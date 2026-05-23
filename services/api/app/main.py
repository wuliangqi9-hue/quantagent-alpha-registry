from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "packages" / "factor-engine"))
sys.path.insert(0, str(ROOT / "packages" / "strategy-selector"))
sys.path.insert(0, str(ROOT / "packages" / "agent-memory"))
sys.path.insert(0, str(ROOT / "packages" / "agent-orchestrator"))

from agent_memory import AgentMemoryStore, MemoryRecord  # noqa: E402
from agent_orchestrator import build_agent_context  # noqa: E402
from factor_engine.service import compute_factor_summary  # noqa: E402
from strategy_selector.selector import select_strategy  # noqa: E402

from .byreal import build_execution_intent, byreal_status
from .chain import (
    get_agent_status,
    mock_record,
    record_signal_on_chain,
    register_agent_on_chain,
    submit_reputation_feedback,
)
from .config import AGENT_ID, CHAIN_CONFIGURED, CONTRACT_ADDRESS, EXPLORER_BASE, MEMORY_STORE_PATH, SUPPORTED_ASSETS
from .data_loader import load_market_data, load_offline
from .decision import build_decision_report, signal_hash
from .reputation import settle_last_signal

app = FastAPI(
    title="QuantAgent Alpha Registry API",
    version="1.0.0",
    description="MVP API for factor analysis, strategy selection, and Mantle signal proofs.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_last_analysis: dict[str, Any] = {}
_memory_store = AgentMemoryStore(MEMORY_STORE_PATH)


class AnalyzeRequest(BaseModel):
    symbol: str = Field(default="BTC", examples=["BTC"])
    mode: Literal["auto", "live", "offline-demo"] | None = "auto"


class RecordSignalRequest(BaseModel):
    symbol: str | None = None
    useLastAnalysis: bool = True
    signalHash: str | None = None
    strategyId: str | None = None
    modelVersion: str | None = None
    mode: str | None = None


class AgentRegisterRequest(BaseModel):
    agentURI: str | None = None


class SettleRequest(BaseModel):
    useLastAnalysis: bool = True
    exitPrice: float | None = None


@app.get("/health")
@app.get("/api/health", include_in_schema=False)
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "contractConfigured": bool(CONTRACT_ADDRESS),
        "walletConfigured": CHAIN_CONFIGURED,
        "agentId": AGENT_ID or None,
        "agentConfigured": AGENT_ID > 0,
        "proofMode": "real-onchain" if CHAIN_CONFIGURED else "demo-proof",
        "supportedAssets": SUPPORTED_ASSETS,
        "byreal": byreal_status(),
        "apiPrefixes": ["", "/api"],
    }


@app.get("/assets")
@app.get("/api/assets", include_in_schema=False)
def assets() -> dict[str, Any]:
    return {"assets": SUPPORTED_ASSETS}


@app.get("/demo/sample")
@app.get("/api/demo/sample", include_in_schema=False)
def demo_sample(symbol: str = "BTC") -> dict[str, Any]:
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


@app.post("/analyze")
@app.post("/api/analyze", include_in_schema=False)
async def analyze(body: AnalyzeRequest) -> dict[str, Any]:
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
            "summary": _memory_store.summary(symbol),
            "retrieved": _memory_store.retrieve(symbol=symbol, factor_snapshot=factor_snapshot, limit=3),
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
    global _last_analysis
    _last_analysis = result
    return result


WEB_DIST = ROOT / "apps" / "web" / "dist"
if WEB_DIST.exists():
    assets_dir = WEB_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    def serve_dashboard():
        return FileResponse(WEB_DIST / "index.html")


@app.post("/record-signal")
@app.post("/api/record-signal", include_in_schema=False)
async def record_signal(body: RecordSignalRequest) -> dict[str, Any]:
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
                "message": "Configured on-chain recording failed. Check RPC, wallet balance, contract address, and duplicate signal status.",
            }
        else:
            chain_result = {
                "recorded": False,
                "error": str(exc),
                **mock_record(sig, symbol, strategy_id, model_version, mode),
            }

    return {"signalHash": sig, "chain": chain_result}


@app.get("/agent")
@app.get("/api/agent", include_in_schema=False)
def agent_status() -> dict[str, Any]:
    return {**get_agent_status(), "memory": _memory_store.summary()}


@app.get("/memory")
@app.get("/api/memory", include_in_schema=False)
def memory_status(symbol: str | None = None) -> dict[str, Any]:
    sym = symbol.upper() if symbol else None
    return {
        "storePath": str(MEMORY_STORE_PATH),
        "summary": _memory_store.summary(sym),
        "recent": [asdict(record) for record in _memory_store.load(symbol=sym, limit=10)],
    }


@app.post("/agent/register")
@app.post("/api/agent/register", include_in_schema=False)
def agent_register(body: AgentRegisterRequest) -> dict[str, Any]:
    try:
        return register_agent_on_chain(body.agentURI)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/byreal/status")
@app.get("/api/byreal/status", include_in_schema=False)
def byreal_adapter_status() -> dict[str, Any]:
    return byreal_status()


@app.post("/settle")
@app.post("/api/settle", include_in_schema=False)
async def settle(body: SettleRequest) -> dict[str, Any]:
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
        _memory_store.append(record)
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
                "message": "Configured reputation write failed. Check AGENT_ID, wallet permission, and contract address.",
            }
        else:
            chain_result = {
                "recorded": False,
                "mock": True,
                "proofMode": "demo-proof",
                "signalHash": payload["signalHash"],
                "message": "Demo settlement calculated locally. Configure Mantle credentials and AGENT_ID to write reputation feedback.",
            }

    return {"settlement": settlement, "chain": chain_result, "memory": _memory_store.summary(payload["symbol"])}
