from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "packages" / "factor-engine"))
sys.path.insert(0, str(ROOT / "packages" / "strategy-selector"))
sys.path.insert(0, str(ROOT / "packages" / "agent-memory"))
sys.path.insert(0, str(ROOT / "packages" / "agent-orchestrator"))

from agent_memory import AdaptiveOPROStore, AgentMemoryStore  # noqa: E402

from .config import ATLAS_OPRO_STORE_PATH, MEMORY_STORE_PATH
from .routers import analyze as analyze_router
from .routers import health as health_router
from .routers import signal as signal_router

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

_memory_store = AgentMemoryStore(MEMORY_STORE_PATH)
_opro_store = AdaptiveOPROStore(ATLAS_OPRO_STORE_PATH)


def _inject_memory() -> dict[str, Any]:
    """Shared dependency to inject memory store into route handlers that need it."""
    return {"memory_store": _memory_store}


@app.get("/health")
@app.get("/api/health", include_in_schema=False)
async def health():
    return await health_router.health_check()


@app.get("/assets")
@app.get("/api/assets", include_in_schema=False)
async def assets():
    return await health_router.assets()


@app.get("/demo/sample")
@app.get("/api/demo/sample", include_in_schema=False)
async def demo_sample(symbol: str = "BTC"):
    return await analyze_router.demo_sample(symbol)


@app.post("/analyze")
@app.post("/api/analyze", include_in_schema=False)
async def analyze(body: analyze_router.AnalyzeRequest):
    result = await analyze_router.analyze(body, memory_store=_memory_store, opro_store=_opro_store)
    signal_router.set_last_analysis(result)
    return result


@app.post("/record-signal")
@app.post("/api/record-signal", include_in_schema=False)
async def record_signal(body: signal_router.RecordSignalRequest):
    return await signal_router.record_signal(body)


@app.post("/settle")
@app.post("/api/settle", include_in_schema=False)
async def settle(body: signal_router.SettleRequest):
    return await signal_router.settle(body, memory_store=_memory_store, opro_store=_opro_store)


@app.get("/agent")
@app.get("/api/agent", include_in_schema=False)
async def agent_status():
    return await signal_router.agent_status(memory_store=_memory_store)


@app.get("/memory")
@app.get("/api/memory", include_in_schema=False)
async def memory_status(symbol: str | None = None):
    return await signal_router.memory_status(symbol, memory_store=_memory_store)


@app.post("/agent/register")
@app.post("/api/agent/register", include_in_schema=False)
async def agent_register(body: signal_router.AgentRegisterRequest):
    return await signal_router.agent_register(body)


@app.get("/byreal/status")
@app.get("/api/byreal/status", include_in_schema=False)
async def byreal_status():
    return await signal_router.byreal_adapter_status()


WEB_DIST = ROOT / "apps" / "web" / "dist"
if WEB_DIST.exists():
    assets_dir = WEB_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    def serve_dashboard():
        return FileResponse(WEB_DIST / "index.html")
