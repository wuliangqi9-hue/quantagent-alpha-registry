from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict
import json
from time import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from agent_memory import MemoryRecord

from ..atlas_opro import trigger_opro_adaptation
from ..atlas_adaptive_engine import evaluate_window, mutate_prompt
from ..byreal import byreal_status
from ..chain import (
    get_agent_status,
    record_signal_on_chain,
    register_agent_on_chain,
    submit_reputation_feedback,
)
from ..config import (
    ANALYSIS_SESSION_DIR,
    CHAIN_CONFIGURED,
    CHAIN_WRITE_AUTH_CONFIGURED,
    FINPOS_MULTI_TIMESCALE_ENABLED,
    MANTLE_ALLOW_PUBLIC_WRITES,
    ONCHAIN_WRITE_AUTH_TOKEN,
)
from ..erc8004 import build_reputation_feedback
from ..erc8004_adapter import ERC8004Adapter
from ..finpos import (
    compute_finpos_rewards,
)

# ---- A2C 在线训练器集成 ----
from ..a2c_adapter import run_a2c_training_step
from ..config import A2C_TRAINING_ENABLED as A2C_ENABLED_CFG
from ..reclaim import generate_zktls_proof, get_reclaim_adapter
from ..reputation import settle_last_signal
from ..tee import get_tee_attestor
from ..models import AgentRegisterRequest, RecordSignalRequest, SettleRequest
from ..proof_bundle import build_proof_bundle

router = APIRouter(tags=["signal"])

_last_analysis: dict[str, Any] = {}
_analysis_cache: "OrderedDict[str, tuple[float, dict[str, Any]]]" = OrderedDict()
_ANALYSIS_CACHE_TTL_SECONDS = 30 * 60
_ANALYSIS_CACHE_MAX_ITEMS = 64


def get_last_analysis() -> dict[str, Any]:
    return _last_analysis


def set_last_analysis(data: dict[str, Any], *, analysis_id: str | None = None) -> None:
    global _last_analysis
    _last_analysis = data
    cache_key = analysis_id or data.get("analysisId")
    if cache_key:
        _analysis_cache[str(cache_key)] = (time(), data)
        _analysis_cache.move_to_end(str(cache_key))
        _persist_analysis_session(str(cache_key), data)
        _prune_analysis_cache()


def _prune_analysis_cache() -> None:
    now = time()
    expired = [
        key
        for key, (created_at, _) in _analysis_cache.items()
        if now - created_at > _ANALYSIS_CACHE_TTL_SECONDS
    ]
    for key in expired:
        _analysis_cache.pop(key, None)
    while len(_analysis_cache) > _ANALYSIS_CACHE_MAX_ITEMS:
        _analysis_cache.popitem(last=False)
    _prune_analysis_session_files(now)


def _safe_analysis_id(analysis_id: str) -> str:
    clean = "".join(ch for ch in analysis_id if ch.isalnum() or ch in {"-", "_"})
    if not clean or clean != analysis_id:
        raise HTTPException(status_code=400, detail="Invalid analysisId.")
    return clean


def _analysis_session_path(analysis_id: str):
    return ANALYSIS_SESSION_DIR / f"{_safe_analysis_id(analysis_id)}.json"


def _persist_analysis_session(analysis_id: str, payload: dict[str, Any]) -> None:
    ANALYSIS_SESSION_DIR.mkdir(parents=True, exist_ok=True)
    path = _analysis_session_path(analysis_id)
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(payload, sort_keys=True, default=str), encoding="utf-8")
    tmp_path.replace(path)


def _load_analysis_session(analysis_id: str) -> dict[str, Any] | None:
    path = _analysis_session_path(analysis_id)
    if not path.exists():
        return None
    if time() - path.stat().st_mtime > _ANALYSIS_CACHE_TTL_SECONDS:
        path.unlink(missing_ok=True)
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _prune_analysis_session_files(now: float) -> None:
    if not ANALYSIS_SESSION_DIR.exists():
        return
    for path in ANALYSIS_SESSION_DIR.glob("*.json"):
        try:
            if now - path.stat().st_mtime > _ANALYSIS_CACHE_TTL_SECONDS:
                path.unlink(missing_ok=True)
        except OSError:
            continue


def _resolve_analysis_payload(*, analysis_id: str | None, signal_hash: str | None) -> dict[str, Any]:
    _prune_analysis_cache()
    payload: dict[str, Any] | None = None

    if analysis_id:
        safe_id = _safe_analysis_id(str(analysis_id))
        cached = _analysis_cache.get(safe_id)
        if cached is None:
            disk_payload = _load_analysis_session(safe_id)
            if disk_payload is None:
                raise HTTPException(status_code=404, detail="Analysis session expired or was not found. Run /analyze again.")
            _analysis_cache[safe_id] = (time(), disk_payload)
            cached = _analysis_cache[safe_id]
        _analysis_cache.move_to_end(safe_id)
        payload = cached[1]
    else:
        raise HTTPException(status_code=400, detail="analysisId is required. Run /analyze and pass the returned analysisId.")

    expected_hash = payload.get("signalHash")
    if signal_hash and expected_hash and signal_hash.lower() != str(expected_hash).lower():
        raise HTTPException(
            status_code=409,
            detail="signalHash does not match the referenced analysis session.",
        )
    return payload


def _trade_window_from_memory(previous_records: list[Any], current: dict[str, Any]) -> list[dict[str, Any]]:
    trades: list[dict[str, Any]] = []
    for record in (previous_records or [])[-8:]:
        if isinstance(record, dict):
            settlement = record.get("settlement", record)
        else:
            settlement = asdict(record)
        entry = settlement.get("entryPrice") or settlement.get("entry_price")
        exit_price = settlement.get("exitPrice") or settlement.get("exit_price")
        side = settlement.get("direction") or settlement.get("side")
        if entry is not None and exit_price is not None and side:
            trades.append({"entry": entry, "exit": exit_price, "side": side})

    if current.get("entryPrice") is not None and current.get("exitPrice") is not None:
        trades.append(
            {
                "entry": current.get("entryPrice"),
                "exit": current.get("exitPrice"),
                "side": current.get("direction") or "long",
            }
        )
    return trades


def _dedup_prompt_append(current_prompt: str, addition: str, *, max_chars: int = 1800) -> str:
    normalized = " ".join(str(current_prompt or "").split())
    addition_normalized = " ".join(addition.split())
    if addition_normalized in normalized:
        combined = normalized
    else:
        combined = f"{normalized} {addition_normalized}".strip()
    if len(combined) <= max_chars:
        return combined
    return combined[-max_chars:].lstrip()


def _enrich_chain_metadata(chain_result: dict[str, Any], settlement: dict[str, Any]) -> None:
    chain_result.setdefault("erc8004Feedback", build_reputation_feedback(settlement))
    chain_result.setdefault(
        "standardReputationFeedback",
        ERC8004Adapter().reputation_feedback_payload(settlement),
    )


def _chain_attempt_http_status(chain_result: dict[str, Any]) -> int:
    if chain_result.get("recorded"):
        return 200
    if chain_result.get("proofMode") == "onchain-attempt-failed":
        return 502
    return 200


def _require_onchain_write_authorized(
    request: Request,
    *,
    signal_hash: str | None = None,
    symbol: str | None = None,
    strategy_id: str | None = None,
) -> None:
    """Protect public deployments from spending the configured signer by accident."""
    if not CHAIN_CONFIGURED:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "mantle-config-required",
                "message": "Set MANTLE_ENABLE_ONCHAIN_WRITES=true, SIGNAL_REGISTRY_ADDRESS, and MANTLE_PRIVATE_KEY to record a real Mantle transaction.",
                "proofMode": "config-required",
                "signalHash": signal_hash,
                "symbol": symbol,
                "strategyId": strategy_id,
            },
        )
    if MANTLE_ALLOW_PUBLIC_WRITES:
        return
    if ONCHAIN_WRITE_AUTH_TOKEN:
        supplied = request.headers.get("x-quantagent-write-token", "")
        auth = request.headers.get("authorization", "")
        bearer = auth.removeprefix("Bearer ").strip() if auth.lower().startswith("bearer ") else ""
        if supplied == ONCHAIN_WRITE_AUTH_TOKEN or bearer == ONCHAIN_WRITE_AUTH_TOKEN:
            return
    raise HTTPException(
        status_code=403,
        detail={
            "code": "onchain-write-locked",
            "message": (
                "On-chain writes are configured but locked for public safety. "
                "Set MANTLE_ALLOW_PUBLIC_WRITES=true for a live judging session or send x-quantagent-write-token."
            ),
            "proofMode": "write-locked",
            "writeAuthConfigured": CHAIN_WRITE_AUTH_CONFIGURED,
            "signalHash": signal_hash,
            "symbol": symbol,
            "strategyId": strategy_id,
        },
    )


async def _apply_atlas_adaptive_engine(
    *,
    payload: dict[str, Any],
    settlement: dict[str, Any],
    previous_records: list[Any],
    opro_store: Any,
) -> dict[str, Any] | None:
    if opro_store is None:
        return None

    trades = _trade_window_from_memory(previous_records, settlement)
    score = evaluate_window(trades)
    adaptive_prompt = (payload.get("memory") or {}).get("adaptivePrompt", {})
    current_prompt = adaptive_prompt.get("template") or "Prioritize position-aware decisions and strict risk control."
    market_context = (
        f"symbol={payload.get('symbol')}; "
        f"direction={payload.get('selection', {}).get('signalDirection')}; "
        f"regime={payload.get('selection', {}).get('marketRegime')}; "
        f"pnlBps={settlement.get('pnlBps')}; "
        f"proofMode={payload.get('proofMode')}"
    )

    if score >= 0 and float(settlement.get("pnlBps") or 0.0) >= 0:
        return {
            "schema": "quantagent.atlas-adaptive-engine.v1",
            "score": score,
            "mutated": False,
            "rationale": "Recent trade window is non-negative; prompt mutation was not required.",
        }

    try:
        new_prompt = await mutate_prompt(current_prompt, score, market_context)
        variant = opro_store.append_variant(new_prompt, source="openai-atlas-engine")
        return {
            "schema": "quantagent.atlas-adaptive-engine.v1",
            "score": score,
            "mutated": True,
            "promptId": variant.id,
            "selectedTemplate": variant.template,
            "rationale": "Negative trade-window score triggered OpenAI prompt mutation.",
        }
    except Exception as exc:
        fallback_clause = (
            f"Loss-window score {score:.4f}: reduce exposure, require stronger liquidity confirmation, "
            "and avoid increasing risk until the next settlement recovers."
        )
        fallback = opro_store.append_variant(
            _dedup_prompt_append(current_prompt, fallback_clause),
            source="deterministic-atlas-engine",
        )
        return {
            "schema": "quantagent.atlas-adaptive-engine.v1",
            "score": score,
            "mutated": True,
            "promptId": fallback.id,
            "selectedTemplate": fallback.template,
            "rationale": f"OpenAI mutation unavailable; deterministic risk prompt applied: {exc}",
        }


@router.post("/record-signal")
async def record_signal(body: RecordSignalRequest, request: Request):
    if body.useLastAnalysis:
        payload = _resolve_analysis_payload(analysis_id=body.analysisId, signal_hash=body.signalHash)
        sig = payload["signalHash"]
        symbol = payload["symbol"]
        strategy_id = payload["selection"]["strategyId"]
        model_version = payload["modelVersion"]
        mode = payload["mode"]
    else:
        if not all([body.signalHash, body.symbol, body.strategyId, body.modelVersion, body.mode]):
            raise HTTPException(status_code=400, detail="Missing required record fields.")
        sig = body.signalHash
        symbol = body.symbol.upper()
        strategy_id = body.strategyId
        model_version = body.modelVersion
        mode = body.mode or "offline-demo"

    _require_onchain_write_authorized(
        request,
        signal_hash=sig,
        symbol=symbol,
        strategy_id=strategy_id,
    )

    report = payload.get("decisionReport") if body.useLastAnalysis else None
    try:
        chain_result = await _record_signal_on_chain_async(sig, symbol, strategy_id, model_version, mode, report)
    except Exception as exc:
        chain_result = {
            "recorded": False,
            "mock": False,
            "mode": mode,
            "signalHash": sig,
            "symbol": symbol,
            "strategyId": strategy_id,
            "modelVersion": model_version,
            "txHash": None,
            "explorerUrl": None,
            "error": str(exc),
            "proofMode": "onchain-attempt-failed",
            "message": "Configured on-chain recording failed.",
        }

    response_body = {"signalHash": sig, "chain": chain_result}
    return JSONResponse(content=response_body, status_code=_chain_attempt_http_status(chain_result))


@router.post("/settle")
async def settle(
    body: SettleRequest,
    request: Request,
    memory_store: Any = None,
    opro_store: Any = None,
):
    if body.useLastAnalysis:
        payload = _resolve_analysis_payload(analysis_id=body.analysisId, signal_hash=body.signalHash)
    else:
        raise HTTPException(status_code=400, detail="Settlement requires a referenced analysis session.")

    previous_records = memory_store.load(symbol=payload["symbol"]) if memory_store is not None else []
    settlement = settle_last_signal(payload, body.exitPrice, previous_records=previous_records)
    agent = payload.get("agent") or {}
    reputation_score = None
    if isinstance(agent, dict) and isinstance(agent.get("reputation"), dict):
        reputation_score = agent["reputation"].get("score")

    try:
        record = MemoryRecord.from_analysis(payload, settlement, reputation_score=reputation_score)
        if memory_store is not None:
            memory_store.append(record)
    except Exception as exc:
        settlement["memoryAppendError"] = {
            "code": "memory-append-failed",
            "message": str(exc),
        }

    finpos_rewards = None
    if FINPOS_MULTI_TIMESCALE_ENABLED:
        try:
            current_exposure = (agent.get("wallet") or {}).get("exposurePct", 0.0)
            signal_direction = str(payload["selection"]["signalDirection"]).lower()
            direction_correct = (
                (signal_direction in {"buy", "long"} and settlement["pnlBps"] > 0)
                or (signal_direction in {"sell", "short"} and settlement["pnlBps"] < 0)
            )
            finpos_rewards = compute_finpos_rewards(
                current_pnl_bps=float(settlement.get("pnlBps", 0)),
                current_pnl_usd=float(settlement.get("pnlUsd", 0)),
                direction_correct=direction_correct,
                current_exposure_pct=float(current_exposure),
                historical_records=[
                    {"settlement": r} if isinstance(r, dict) else {"settlement": asdict(r)}
                    for r in (previous_records or [])[-50:]
                ],
            )
            settlement["finposRewards"] = finpos_rewards.to_dict()
            settlement["compositeScore"] = finpos_rewards.composite_score
        except Exception as exc:
            settlement["finposError"] = {
                "code": "finpos-rewards-failed",
                "message": str(exc),
            }

    if A2C_ENABLED_CFG and finpos_rewards is not None:
        try:
            a2c_result = run_a2c_training_step(
                symbol=payload.get("symbol", "BTC"),
                payload=payload,
                agent=agent,
                finpos_rewards=finpos_rewards,
                checkpoint_dir="data",
            )
            if a2c_result is not None:
                settlement["a2cTraining"] = a2c_result
        except Exception as exc:
            settlement["a2cTrainingError"] = {
                "code": "a2c-training-failed",
                "message": str(exc),
            }

    if opro_store is not None:
        try:
            adaptive_prompt = (payload.get("memory") or {}).get("adaptivePrompt", {})
            opro_store.update_from_settlement(
                prompt_id=adaptive_prompt.get("id"),
                prompt_template=adaptive_prompt.get("template"),
                pnl_bps=float(settlement.get("pnlBps") or 0.0),
                history=[
                    {"settlement": asdict(r)} if not isinstance(r, dict) else r
                    for r in (previous_records or [])[-12:]
                ],
            )
            atlas_engine_result = await _apply_atlas_adaptive_engine(
                payload=payload,
                settlement=settlement,
                previous_records=previous_records,
                opro_store=opro_store,
            )
            if atlas_engine_result:
                settlement["atlasAdaptiveEngine"] = atlas_engine_result
                if atlas_engine_result.get("mutated"):
                    settlement["oproAdaptation"] = {
                        "schema": "quantagent.atlas-opro-adaptation.v1",
                        "iteration": len(opro_store.load()),
                        "promptId": atlas_engine_result.get("promptId"),
                        "mutations": ["atlas-adaptive-engine"],
                        "performanceDelta": atlas_engine_result.get("score", 0.0),
                        "selectedTemplate": atlas_engine_result.get("selectedTemplate", ""),
                        "rationale": atlas_engine_result.get("rationale", ""),
                    }
        except Exception as exc:
            settlement["oproError"] = {
                "code": "opro-adaptation-failed",
                "message": str(exc),
            }

    try:
        market_feedback = {
            "regime": (payload.get("regime") or {}).get("regime", "normal"),
            "volatilityMultiplier": float((payload.get("regime") or {}).get("volatilityMultiplier", 1.0)),
            "pnlBps": float(settlement.get("pnlBps", 0)),
        }
        opro_adapt = trigger_opro_adaptation(market_feedback=market_feedback)
        if opro_adapt and "oproAdaptation" not in settlement:
            settlement["oproAdaptation"] = opro_adapt
    except Exception as exc:
        settlement["oproAdaptationError"] = {
            "code": "opro-trigger-failed",
            "message": str(exc),
        }

    tee_attestation = None
    try:
        attestor = get_tee_attestor()
        payload_json = (
            payload["signalHash"]
            + str(settlement.get("pnlBps", ""))
            + payload["selection"]["signalDirection"]
        )
        tee_attestation = attestor.attest_execution(
            payload=payload_json,
            metadata={
                "signalHash": payload["signalHash"],
                "symbol": payload["symbol"],
                "pnlBps": settlement.get("pnlBps", 0),
                "strategyId": payload["selection"]["strategyId"],
            },
        )
        settlement["teeAttestation"] = tee_attestation.to_dict()
    except Exception as exc:
        settlement["teeAttestationError"] = {
            "code": "tee-attestation-failed",
            "message": str(exc),
        }

    zktls_proof = None
    try:
        reclaim = get_reclaim_adapter()
        data_sources = (payload.get("factorEngine") or {}).get("sources", [])
        if data_sources:
            source = data_sources[0] if isinstance(data_sources[0], dict) else {}
            provider_key = source.get("provider", "binance")
            response_body = source.get("response", {})
            request_params = source.get("params", {})
            zktls_proof = generate_zktls_proof(
                provider_key=provider_key,
                response_body=response_body,
                request_params=request_params,
            )
        elif payload.get("dataProof"):
            data_proof = payload["dataProof"]
            zktls_proof = generate_zktls_proof(
                provider_key="binance-klines",
                response_body=data_proof,
                request_params={
                    "symbol": payload["symbol"],
                    "mode": payload.get("mode"),
                    "proofHash": data_proof.get("proofHash"),
                },
                custom_endpoint=str(data_proof.get("endpoint") or "/api/v3/klines"),
            )
        if zktls_proof is not None:
            verification_payload = reclaim.build_verification_payload(
                zktls_proof,
                signal_hash=payload["signalHash"],
            )
            settlement["zktlsProof"] = zktls_proof.to_dict()
            settlement["zktlsVerification"] = verification_payload
    except Exception as exc:
        settlement["zktlsProofError"] = {
            "code": "zktls-proof-failed",
            "message": str(exc),
        }

    chain_result: dict[str, Any]
    try:
        if request is not None:
            _require_onchain_write_authorized(
                request,
                signal_hash=payload["signalHash"],
                symbol=payload["symbol"],
                strategy_id=payload["selection"]["strategyId"],
            )
        chain_result = await _submit_reputation_feedback_async(
            settlement["score"],
            signal_hash=payload["signalHash"],
            tag1="pnl-bps",
            tag2=payload["selection"]["signalDirection"],
            feedback_payload=settlement,
        )
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
        chain_result = {
            "recorded": False,
            "mock": False,
            "proofMode": detail.get("proofMode", "onchain-write-unavailable"),
            "signalHash": payload["signalHash"],
            "error": detail.get("code", "onchain-write-unavailable"),
            "message": detail.get(
                "message",
                "Settlement calculated locally; on-chain reputation write was not authorized.",
            ),
        }
    except Exception as exc:
        chain_result = {
            "recorded": False,
            "mock": False,
            "proofMode": "onchain-attempt-failed" if CHAIN_CONFIGURED else "config-required",
            "signalHash": payload["signalHash"],
            "error": str(exc),
            "message": (
                "Configured reputation write failed; local settlement, proof bundle, and adaptive outputs were preserved."
                if CHAIN_CONFIGURED
                else "Settlement calculated locally; configure Mantle credentials to write reputation on-chain."
            ),
        }

    _enrich_chain_metadata(chain_result, settlement)

    if tee_attestation:
        chain_result["teeAttestationHash"] = tee_attestation.attestation_hash
    if zktls_proof:
        chain_result["zktlsProofId"] = zktls_proof.proof_id

    try:
        proof_bundle = build_proof_bundle(
            decision_report=payload.get("decisionReport", {}),
            data_proof=payload.get("dataProof"),
            execution_intent=payload.get("executionIntent", {}),
            route_decision=(payload.get("executionIntent") or {}).get("routeDecision"),
            tee_attestation=settlement.get("teeAttestation"),
            zktls_proof=settlement.get("zktlsProof"),
            settlement=settlement,
        )
        settlement["proofBundleHash"] = proof_bundle["proofBundleHash"]
        settlement["proofBundle"] = proof_bundle
        chain_result["proofBundleHash"] = proof_bundle["proofBundleHash"]
    except Exception as exc:
        settlement["proofBundleError"] = {
            "code": "proof-bundle-failed",
            "message": str(exc),
        }

    result: dict[str, Any] = {"settlement": settlement, "chain": chain_result}
    if memory_store is not None:
        result["memory"] = memory_store.summary(payload["symbol"])
    return JSONResponse(content=result, status_code=_chain_attempt_http_status(chain_result))


async def _submit_reputation_feedback_async(*args: Any, **kwargs: Any) -> dict[str, Any]:
    # submit_reputation_feedback performs RPC signing and receipt polling. Keep
    # the async route responsive while the RPC waits for confirmation.
    import asyncio

    return await asyncio.to_thread(submit_reputation_feedback, *args, **kwargs)


async def _record_signal_on_chain_async(*args: Any, **kwargs: Any) -> dict[str, Any]:
    import asyncio

    return await asyncio.to_thread(record_signal_on_chain, *args, **kwargs)


@router.get("/agent")
async def agent_status(memory_store: Any = None):
    result = {**get_agent_status()}
    if memory_store is not None:
        result["memory"] = memory_store.summary()
    return result


@router.get("/memory")
async def memory_status(
    symbol: str | None = None,
    memory_store: Any = None,
):
    sym = symbol.upper() if symbol else None
    base = {
        "summary": memory_store.summary(sym) if memory_store is not None else None,
        "recent": [],
    }
    if memory_store is not None:
        base["recent"] = [asdict(record) for record in memory_store.load(symbol=sym, limit=10)]
    return base


@router.post("/agent/register")
async def agent_register(body: AgentRegisterRequest, request: Request):
    _require_onchain_write_authorized(request)
    try:
        return await _register_agent_on_chain_async(body.agentURI)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


async def _register_agent_on_chain_async(agent_uri: str | None) -> dict[str, Any]:
    import asyncio

    return await asyncio.to_thread(register_agent_on_chain, agent_uri)


@router.get("/byreal/status")
async def byreal_adapter_status():
    return byreal_status()
