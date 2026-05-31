from __future__ import annotations

from fastapi import APIRouter

from ..atlas_opro import get_opro_store
from ..byreal import byreal_status
from ..config import (
    AGENT_ID,
    ATLAS_OPRO_ENABLED,
    CHAIN_CONFIGURED,
    CHAIN_WRITE_AUTH_CONFIGURED,
    CONTRACT_ADDRESS,
    ERC8004_IDENTITY_REGISTRY_ADDRESS,
    ERC8004_REPUTATION_REGISTRY_ADDRESS,
    FINPOS_MULTI_TIMESCALE_ENABLED,
    PHALA_TEE_ENABLED,
    QUANT_AGENT_EXECUTOR_ADDRESS,
    RECLAIM_ZKTLS_ENABLED,
    SIGNAL_REGISTRY_ADDRESS,
    SUPPORTED_ASSETS,
    X402_ENABLED,
)
from ..reclaim import get_reclaim_adapter
from ..tee import get_tee_attestor

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    # 新增模块状态检查
    tee_status = "disabled"
    try:
        attestor = get_tee_attestor()
        tee_status = attestor.status()
    except Exception:
        tee_status = "error"

    reclaim_status = "disabled"
    try:
        reclaim = get_reclaim_adapter()
        reclaim_status = reclaim.status()
    except Exception:
        reclaim_status = "error"

    opro_status = "disabled"
    try:
        store = get_opro_store()
        summary = store.summary()
        opro_status = {
            "enabled": ATLAS_OPRO_ENABLED,
            "promptVariants": summary.get("total_variants", 0),
            "topPerformerId": summary.get("top_performer_id"),
        }
    except Exception:
        opro_status = "error"

    return {
        "status": "ok",
        "contractConfigured": bool(CONTRACT_ADDRESS),
        "walletConfigured": CHAIN_CONFIGURED,
        "onchainWriteUnlocked": bool(CHAIN_CONFIGURED and CHAIN_WRITE_AUTH_CONFIGURED),
        "agentId": AGENT_ID or None,
        "agentConfigured": AGENT_ID > 0,
        "proofMode": (
            "onchain-write-ready"
            if CHAIN_CONFIGURED and CHAIN_WRITE_AUTH_CONFIGURED
            else "onchain-write-locked"
            if CHAIN_CONFIGURED
            else "demo-proof"
        ),
        "supportedAssets": SUPPORTED_ASSETS,
        "apiPrefixes": ["", "/api"],
        # ---- 新增模块状态 ----
        "modules": {
            "finpos": {
                "enabled": FINPOS_MULTI_TIMESCALE_ENABLED,
                "description": "FinPos multi-timescale reward & position-aware decision engine",
            },
            "atlasOpro": opro_status,
            "tee": {
                "provider": "phala-network",
                "status": tee_status,
                "enabled": PHALA_TEE_ENABLED,
            },
            "reclaimZkTLS": {
                "status": reclaim_status,
                "enabled": RECLAIM_ZKTLS_ENABLED,
            },
            "x402": {
                "enabled": X402_ENABLED,
                "description": "HTTP 402 machine-payment protocol via Blocky402 facilitator",
            },
            "byreal": byreal_status(),
        },
        # ---- 遗留字段（向后兼容） ----
        "byreal": byreal_status(),
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
