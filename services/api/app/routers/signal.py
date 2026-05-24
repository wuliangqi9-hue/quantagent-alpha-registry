from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException

from agent_memory import MemoryRecord

from ..atlas_opro import get_opro_store, trigger_opro_adaptation
from ..byreal import byreal_status
from ..chain import (
    get_agent_status,
    mock_record,
    record_signal_on_chain,
    register_agent_on_chain,
    submit_reputation_feedback,
)
from ..config import CHAIN_CONFIGURED, FINPOS_MULTI_TIMESCALE_ENABLED, MEMORY_STORE_PATH
from ..erc8004 import build_reputation_feedback
from ..erc8004_adapter import ERC8004Adapter
from ..finpos import (
    compute_finpos_rewards,
)
from ..reclaim import generate_zktls_proof, get_reclaim_adapter
from ..reputation import settle_last_signal
from ..tee import get_tee_attestor
from ..models import AgentRegisterRequest, RecordSignalRequest, SettleRequest
from ..proof_bundle import build_proof_bundle

router = APIRouter(tags=["signal"])

_last_analysis: dict[str, Any] = {}


def get_last_analysis() -> dict[str, Any]:
    return _last_analysis


def set_last_analysis(data: dict[str, Any]) -> None:
    global _last_analysis
    _last_analysis = data


@router.post("/record-signal")
async def record_signal(body: RecordSignalRequest):
    if body.useLastAnalysis:
        if not _last_analysis:
            raise HTTPException(status_code=400, detail="Run /analyze first.")
        payload = _last_analysis
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

    try:
        report = payload.get("decisionReport") if body.useLastAnalysis else None
        chain_result = record_signal_on_chain(sig, symbol, strategy_id, model_version, mode, report)
        if not chain_result.get("recorded") and not CHAIN_CONFIGURED:
            chain_result = mock_record(sig, symbol, strategy_id, model_version, mode)
    except Exception as exc:
        if CHAIN_CONFIGURED:
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
                "message": "Configured on-chain recording failed.",
            }
        else:
            chain_result = {
                "recorded": False,
                "error": str(exc),
                **mock_record(sig, symbol, strategy_id, model_version, mode),
            }

    return {"signalHash": sig, "chain": chain_result}


@router.post("/settle")
async def settle(
    body: SettleRequest,
    memory_store: Any = None,
    opro_store: Any = None,
):
    if body.useLastAnalysis:
        if not _last_analysis:
            raise HTTPException(status_code=400, detail="Run /analyze first.")
        payload = _last_analysis
    else:
        raise HTTPException(status_code=400, detail="Only useLastAnalysis settlement is supported in this MVP.")

    try:
        previous_records = memory_store.load(symbol=payload["symbol"]) if memory_store is not None else []
        settlement = settle_last_signal(payload, body.exitPrice, previous_records=previous_records)
        reputation_score = None
        agent = payload.get("agent") or {}
        if isinstance(agent, dict) and isinstance(agent.get("reputation"), dict):
            reputation_score = agent["reputation"].get("score")
        record = MemoryRecord.from_analysis(payload, settlement, reputation_score=reputation_score)
        if memory_store is not None:
            memory_store.append(record)

        # ---- FinPos 多时间尺度奖励 ----
        finpos_rewards = None
        if FINPOS_MULTI_TIMESCALE_ENABLED:
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

        # ---- ATLAS Adaptive-OPRO 动态提示词演化 ----
        opro_result = None
        adaptive_prompt = (payload.get("memory") or {}).get("adaptivePrompt", {})
        if opro_store is not None:
            opro_store.update_from_settlement(
                prompt_id=adaptive_prompt.get("id"),
                prompt_template=adaptive_prompt.get("template"),
                pnl_bps=float(settlement.get("pnlBps") or 0.0),
            )
        # 触发一次适应周期（基于市场反馈）
        market_feedback = {
            "regime": (payload.get("regime") or {}).get("regime", "normal"),
            "volatilityMultiplier": float((payload.get("regime") or {}).get("volatilityMultiplier", 1.0)),
            "pnlBps": float(settlement.get("pnlBps", 0)),
        }
        opro_adapt = trigger_opro_adaptation(market_feedback=market_feedback)
        if opro_adapt:
            opro_result = opro_adapt
            settlement["oproAdaptation"] = opro_adapt

        # ---- TEE 证明生成 ----
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
        except Exception:
            pass  # TEE 证明失败不阻塞结算流程

        # ---- Reclaim zkTLS 数据溯源证明 ----
        zktls_proof = None
        try:
            reclaim = get_reclaim_adapter()
            data_sources = (payload.get("factorEngine") or {}).get("sources", [])
            if data_sources:
                # 为第一个数据源生成 zkTLS 证明
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
        except Exception:
            pass  # zkTLS 证明失败不阻塞结算流程

        chain_result = submit_reputation_feedback(
            settlement["score"],
            signal_hash=payload["signalHash"],
            tag1="pnl-bps",
            tag2=payload["selection"]["signalDirection"],
            feedback_payload=settlement,
        )
        chain_result.setdefault("erc8004Feedback", build_reputation_feedback(settlement))
        chain_result.setdefault(
            "standardReputationFeedback",
            ERC8004Adapter().reputation_feedback_payload(settlement),
        )

        # 将 TEE 证明和 zkTLS 证明附加到链上结果
        if tee_attestation:
            chain_result["teeAttestationHash"] = tee_attestation.attestation_hash
        if zktls_proof:
            chain_result["zktlsProofId"] = zktls_proof.proof_id

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
        previous_records = memory_store.load(symbol=payload["symbol"]) if memory_store is not None else []
        settlement = settle_last_signal(payload, body.exitPrice, previous_records=previous_records)
        if CHAIN_CONFIGURED:
            chain_result = {
                "recorded": False,
                "mock": False,
                "proofMode": "real-onchain",
                "error": str(exc),
                "message": "Configured reputation write failed.",
            }
        else:
            chain_result = {
                "recorded": False,
                "mock": True,
                "proofMode": "demo-proof",
                "signalHash": payload["signalHash"],
                "message": "Demo settlement calculated locally.",
            }

    result: dict[str, Any] = {"settlement": settlement, "chain": chain_result}
    if memory_store is not None:
        result["memory"] = memory_store.summary(payload["symbol"])
    return result


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
    base["storePath"] = str(MEMORY_STORE_PATH) if memory_store is not None else "not-initialized"
    if memory_store is not None:
        base["recent"] = [asdict(record) for record in memory_store.load(symbol=sym, limit=10)]
    return base


@router.post("/agent/register")
async def agent_register(body: AgentRegisterRequest):
    try:
        return register_agent_on_chain(body.agentURI)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/byreal/status")
async def byreal_adapter_status():
    return byreal_status()
