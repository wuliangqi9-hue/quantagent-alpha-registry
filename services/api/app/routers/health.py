from __future__ import annotations

from fastapi import APIRouter

from ..byreal import byreal_status
from ..config import (
    AGENT_ID,
    CHAIN_CONFIGURED,
    CONTRACT_ADDRESS,
    ERC8004_IDENTITY_REGISTRY_ADDRESS,
    ERC8004_REPUTATION_REGISTRY_ADDRESS,
    QUANT_AGENT_EXECUTOR_ADDRESS,
    SIGNAL_REGISTRY_ADDRESS,
    SUPPORTED_ASSETS,
)

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
        "erc8004": {
            "identityRegistry": ERC8004_IDENTITY_REGISTRY_ADDRESS,
            "reputationRegistry": ERC8004_REPUTATION_REGISTRY_ADDRESS,
        },
        "signalRegistry": SIGNAL_REGISTRY_ADDRESS,
        "quantAgentExecutor": QUANT_AGENT_EXECUTOR_ADDRESS,
    }


@router.get("/assets")
async def assets():
    return {"assets": SUPPORTED_ASSETS}