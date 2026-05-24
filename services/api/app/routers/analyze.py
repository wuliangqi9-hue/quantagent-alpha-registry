from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "packages" / "factor-engine"))
sys.path.insert(0, str(ROOT / "packages" / "strategy-selector"))
sys.path.insert(0, str(ROOT / "packages" / "agent-memory"))
sys.path.insert(0, str(ROOT / "packages" / "agent-orchestrator"))

from agent_orchestrator import build_agent_context  # noqa: E402
from factor_engine.service import compute_factor_summary  # noqa: E402
from strategy_selector.selector import select_strategy  # noqa: E402

from ..byreal import build_execution_intent, byreal_status
from ..chain import get_agent_status
from ..config import (
    CHAIN_CONFIGURED,
    CONTRACT_ADDRESS,
    EXPLORER_BASE,
    SUPPORTED_ASSETS,
)
from ..data_loader import load_market_data, load_offline
from ..decision import build_decision_report, signal_hash
from ..models import AnalyzeRequest

router = APIRouter(tags=["analysis"])

@router.get("/demo/sample")
async def demo_sample(symbol: str = "BTC"):
    try:
        df, mode = load_offline(symbol)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "symbol": symbol.upper(),
        "mode": mode,
        "rows": len(df),
        "columns": list(df.columns),
        "preview": df.tail(3).to_dict(orient="records"),
    }


@router.post("/analyze")
async def analyze(body: AnalyzeRequest, memory_store: Any) -> dict[str, Any]:
    symbol = body.symbol.upper()
    if symbol not in SUPPORTED_ASSETS:
        raise HTTPException(status_code=400, detail=f"Unsupported symbol: {symbol}")

    req_mode = None if body.mode == "auto" else body.mode
    try:
        ohlcv, data_mode = await load_market_data(symbol, req_mode)
        factor_summary = compute_factor_summary(ohlcv)
        agent = get_agent_status()
        factor_snapshot = {
            item["id"]: float(item["score"])
            for item in factor_summary.get("factors", [])
            if item.get("score") is not None and not item.get("missing")
        }
        memory_context = {
            "summary": memory_store.summary(symbol),
            "retrieved": memory_store.retrieve(symbol=symbol, factor_snapshot=factor_snapshot, limit=3),
        }
        last_pnl = memory_context["summary"].get("latestPnlBps")
        multi_agent_context = build_agent_context(
            symbol=symbol,
            factor_summary=factor_summary,
            memory_context=memory_context,
            agent_reputation=agent,
        )
        selection = select_strategy(
            symbol,
            factor_summary,
            ohlcv,
            agent_reputation=agent,
            last_settlement_pnl=last_pnl,
            memory_context=memory_context,
            multi_agent_context=multi_agent_context,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    report = build_decision_report(symbol, data_mode, factor_summary, selection)
    sig_hash = signal_hash(report)

    result = {
        "symbol": symbol,
        "mode": data_mode,
        "signalHash": sig_hash,
        "modelVersion": report["modelVersion"],
        "reportSchema": report["schema"],
        "factorSummary": factor_summary,
        "selection": selection,
        "decisionReport": report,
        "explorerBase": EXPLORER_BASE,
        "contractAddress": CONTRACT_ADDRESS or None,
        "proofMode": "real-onchain" if CHAIN_CONFIGURED else "demo-proof",
        "agent": agent,
        "memory": memory_context,
        "multiAgent": multi_agent_context,
        "byreal": byreal_status(),
        "executionIntent": build_execution_intent({"symbol": symbol, "selection": selection}),
    }
    return result
