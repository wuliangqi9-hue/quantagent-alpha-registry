from __future__ import annotations

from fastapi import APIRouter

from ..byreal import byreal_status
from ..config import AGENT_ID, CHAIN_CONFIGURED, CONTRACT_ADDRESS, SUPPORTED_ASSETS

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
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


@router.get("/assets")
async def assets():
    return {"assets": SUPPORTED_ASSETS}