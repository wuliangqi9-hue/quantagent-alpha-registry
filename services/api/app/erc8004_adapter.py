from __future__ import annotations

from typing import Any

from .agent_card import agent_registry_identifier, build_agent_card
from .config import (
    AGENT_ID,
    AGENT_URI,
    ERC8004_IDENTITY_REGISTRY_ADDRESS,
    ERC8004_REPUTATION_REGISTRY_ADDRESS,
    ERC8004_VALIDATION_REGISTRY_ADDRESS,
    MANTLE_CHAIN_ID,
    SIGNAL_REGISTRY_ADDRESS,
)
from .erc8004 import build_reputation_feedback


class ERC8004Adapter:
    """Boundary for ERC-8004 identity, validation, and reputation registries.

    The adapter deliberately returns structured fallback states when official
    registry credentials are absent. Callers can rely on the same shape in demo
    and live modes.
    """

    VERSION = "erc8004-adapter-1.0.0"

    def __init__(self, *, api_base: str = "") -> None:
        self.api_base = api_base or "http://localhost:8000"

    def identity_status(self) -> dict[str, Any]:
        return {
            "schema": "erc8004.identity-status.v1",
            "adapterVersion": self.VERSION,
            "standard": "ERC-8004",
            "mode": "standard-ready" if AGENT_ID > 0 else "fallback-demo",
            "namespace": "eip155",
            "chainId": MANTLE_CHAIN_ID,
            "agentRegistry": agent_registry_identifier(),
            "identityRegistry": ERC8004_IDENTITY_REGISTRY_ADDRESS,
            "agentId": AGENT_ID or None,
            "agentURI": AGENT_URI,
            "signalRegistryFallback": SIGNAL_REGISTRY_ADDRESS or None,
            "agentCard": build_agent_card(self.api_base),
        }

    def validation_status(self, signal_hash: str | None = None) -> dict[str, Any]:
        return {
            "schema": "erc8004.validation-status.v1",
            "mode": "standard-ready" if ERC8004_VALIDATION_REGISTRY_ADDRESS else "fallback-demo",
            "validationRegistry": ERC8004_VALIDATION_REGISTRY_ADDRESS,
            "signalHash": signal_hash,
            "status": "pending" if signal_hash else "not-requested",
            "supportedProofs": ["decision-report-hash", "proof-bundle-hash", "tee-attestation", "reclaim-zktls"],
        }

    def reputation_summary(self, agent_status: dict[str, Any] | None = None) -> dict[str, Any]:
        reputation = (agent_status or {}).get("reputation") if agent_status else None
        return {
            "schema": "erc8004.reputation-summary.v1",
            "mode": "standard-ready" if AGENT_ID > 0 else "fallback-demo",
            "reputationRegistry": ERC8004_REPUTATION_REGISTRY_ADDRESS,
            "agentId": AGENT_ID or None,
            "count": reputation.get("count", 0) if isinstance(reputation, dict) else 0,
            "score": reputation.get("score") if isinstance(reputation, dict) else None,
        }

    def reputation_feedback_payload(self, settlement: dict[str, Any]) -> dict[str, Any]:
        feedback = build_reputation_feedback(settlement)
        feedback.update(
            {
                "agentId": AGENT_ID or None,
                "registry": ERC8004_REPUTATION_REGISTRY_ADDRESS,
                "mode": "standard-ready" if AGENT_ID > 0 else "fallback-demo",
            }
        )
        return feedback


def build_erc8004_status(
    *,
    api_base: str,
    agent_status: dict[str, Any] | None = None,
    signal_hash: str | None = None,
) -> dict[str, Any]:
    adapter = ERC8004Adapter(api_base=api_base)
    return {
        "identity": adapter.identity_status(),
        "validation": adapter.validation_status(signal_hash),
        "reputation": adapter.reputation_summary(agent_status),
    }
