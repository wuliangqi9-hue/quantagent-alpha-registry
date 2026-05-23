from __future__ import annotations

import sys
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

from factor_engine.service import compute_factor_summary  # noqa: E402
from strategy_selector.selector import select_strategy  # noqa: E402

from .chain import mock_record, record_signal_on_chain
from .config import CHAIN_CONFIGURED, CONTRACT_ADDRESS, EXPLORER_BASE, SUPPORTED_ASSETS
from .data_loader import load_market_data, load_offline
from .decision import build_decision_report, signal_hash

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


@app.get("/health")
@app.get("/api/health", include_in_schema=False)
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "contractConfigured": bool(CONTRACT_ADDRESS),
        "walletConfigured": CHAIN_CONFIGURED,
        "proofMode": "real-onchain" if CHAIN_CONFIGURED else "demo-proof",
        "supportedAssets": SUPPORTED_ASSETS,
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
        selection = select_strategy(symbol, factor_summary, ohlcv)
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
        chain_result = record_signal_on_chain(sig, symbol, strategy_id, model_version, mode)
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
