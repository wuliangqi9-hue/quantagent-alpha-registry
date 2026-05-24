from __future__ import annotations

from typing import Any

from .config import (
    AGENT_ID,
    AGENT_URI,
    BLOCKY402_FACILITATOR_URL,
    BYREAL_API_BASE,
    ERC8004_IDENTITY_REGISTRY_ADDRESS,
    ERC8004_REPUTATION_REGISTRY_ADDRESS,
    ERC8004_VALIDATION_REGISTRY_ADDRESS,
    MANTLE_CHAIN_ID,
    QUANT_AGENT_EXECUTOR_ADDRESS,
    SIGNAL_REGISTRY_ADDRESS,
    X402_WALLET_ADDRESS,
)
from .proof_bundle import stable_hash


CARD_SCHEMA = "erc8004.agent-registration-file.v1"


def agent_registry_identifier(registry_address: str | None = None) -> str:
    registry = registry_address or ERC8004_IDENTITY_REGISTRY_ADDRESS
    return f"eip155:{MANTLE_CHAIN_ID}:{registry}"


def build_agent_card(api_base: str) -> dict[str, Any]:
    """Build a deterministic ERC-8004-compatible Agent Registration File."""
    base = api_base.rstrip("/")
    card = {
        "schema": CARD_SCHEMA,
        "name": "QuantAgent Alpha Registry",
        "description": (
            "An autonomous Mantle trading agent that turns factor research into "
            "verifiable decisions, execution intents, and reputation feedback."
        ),
        "version": "1.0.0",
        "agentId": AGENT_ID or None,
        "agentURI": AGENT_URI,
        "agentRegistry": agent_registry_identifier(),
        "registrations": {
            "namespace": "eip155",
            "chainId": MANTLE_CHAIN_ID,
            "identityRegistry": ERC8004_IDENTITY_REGISTRY_ADDRESS,
            "reputationRegistry": ERC8004_REPUTATION_REGISTRY_ADDRESS,
            "validationRegistry": ERC8004_VALIDATION_REGISTRY_ADDRESS,
            "signalRegistryFallback": SIGNAL_REGISTRY_ADDRESS or None,
            "quantAgentExecutor": QUANT_AGENT_EXECUTOR_ADDRESS or None,
        },
        "services": [
            {
                "id": "analyze",
                "type": "https",
                "endpoint": f"{base}/api/analyze",
                "description": "Generate factor summary, strategy selection, execution route, and proof bundle.",
            },
            {
                "id": "record-signal",
                "type": "https",
                "endpoint": f"{base}/api/record-signal",
                "description": "Anchor the latest decision report hash and validation proof metadata.",
            },
            {
                "id": "settle",
                "type": "https",
                "endpoint": f"{base}/api/settle",
                "description": "Settle signal PnL and emit ERC-8004-compatible reputation feedback.",
            },
        ],
        "apiEndpoints": {
            "a2a": f"{base}/api/analyze",
            "agentStatus": f"{base}/api/agent",
            "agentCard": f"{base}/api/agent/card",
            "memory": f"{base}/api/memory",
        },
        "supportedTrust": [
            "erc8004-identity",
            "erc8004-reputation",
            "erc8004-validation",
            "reclaim-zktls",
            "phala-tee-attestation",
            "deterministic-demo-proof",
        ],
        "x402Support": {
            "enabled": bool(BLOCKY402_FACILITATOR_URL and X402_WALLET_ADDRESS),
            "facilitator": BLOCKY402_FACILITATOR_URL or None,
            "wallet": X402_WALLET_ADDRESS or None,
            "policy": "pay only when expected alpha exceeds data cost plus safety margin",
        },
        "execution": {
            "provider": "Byreal/RealClaw",
            "mode": "live-ready" if BYREAL_API_BASE else "simulation",
            "routes": ["byreal-rfq", "protected-clmm", "observe-only"],
        },
        "wallet": X402_WALLET_ADDRESS or "configure-agent-wallet",
        "capabilities": [
            "factor-analysis",
            "position-aware-risk-sizing",
            "qtmrl-a2c-policy-scoring",
            "atlas-adaptive-opro",
            "proof-bundle-generation",
            "erc8004-reputation-feedback",
        ],
    }
    card["cardHash"] = agent_card_hash(card)
    return card


def agent_card_hash(card: dict[str, Any]) -> str:
    payload = {key: value for key, value in card.items() if key != "cardHash"}
    return stable_hash(payload)
