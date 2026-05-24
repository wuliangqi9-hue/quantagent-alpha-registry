from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException

from agent_memory import MemoryRecord

from ..byreal import byreal_status
from ..chain import (
    get_agent_status,
    mock_record,
    record_signal_on_chain,
    register_agent_on_chain,
    submit_reputation_feedback,
)
from ..config import CHAIN_CONFIGURED, MEMORY_STORE_PATH
from ..reputation import settle_last_signal
from ..models import AgentRegisterRequest, RecordSignalRequest, SettleRequest

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
):
    if body.useLastAnalysis:
        if not _last_analysis:
            raise HTTPException(status_code=400, detail="Run /analyze first.")
        payload = _last_analysis
    else:
        raise HTTPException(status_code=400, detail="Only useLastAnalysis settlement is supported in this MVP.")

    try:
        settlement = settle_last_signal(payload, body.exitPrice)
        reputation_score = None
        agent = payload.get("agent") or {}
        if isinstance(agent, dict) and isinstance(agent.get("reputation"), dict):
            reputation_score = agent["reputation"].get("score")
        record = MemoryRecord.from_analysis(payload, settlement, reputation_score=reputation_score)
        if memory_store is not None:
            memory_store.append(record)
        chain_result = submit_reputation_feedback(
            settlement["score"],
            signal_hash=payload["signalHash"],
            tag1="pnl-bps",
            tag2=payload["selection"]["signalDirection"],
            feedback_payload=settlement,
        )
    except Exception as exc:
        settlement = settle_last_signal(payload, body.exitPrice)
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