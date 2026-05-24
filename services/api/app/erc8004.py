from __future__ import annotations

from typing import Any


IDENTITY_REGISTRY_MAINNET = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
REPUTATION_REGISTRY_MAINNET = "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63"


def encode_fixed_point(value: float, decimals: int = 2) -> dict[str, Any]:
    """Encode real values into ERC-8004 reputation fixed-point format."""
    decimals = max(0, min(18, int(decimals)))
    scaled = int(round(float(value) * (10**decimals)))
    min_int128 = -(2**127)
    max_int128 = 2**127 - 1
    if scaled < min_int128 or scaled > max_int128:
        raise ValueError("fixed-point value exceeds int128 range")
    return {"value": scaled, "valueDecimals": decimals}


def build_agent_card(*, api_base: str, wallet: str | None = None) -> dict[str, Any]:
    """Build the standardized Agent Card tokenURI payload for Identity Registry."""
    return {
        "schema": "erc8004.agent-card.v1",
        "name": "QuantAgent Alpha Registry",
        "description": "Position-aware Mantle DeFi trading agent with FinPos, QTMRL, ATLAS, RFQ execution, and zkTLS-ready validation.",
        "endpoints": {
            "a2a": f"{api_base.rstrip('/')}/api/analyze",
            "mcp": f"{api_base.rstrip('/')}/api/agent",
            "reputation": f"{api_base.rstrip('/')}/api/settle",
        },
        "trustModels": ["social-reputation", "erc8004-reputation", "reclaim-zktls", "tee-attestation-ready"],
        "wallet": wallet or "configure-agent-wallet",
        "capabilities": ["factor-analysis", "position-aware-routing", "byreal-rfq-intent", "x402-micropayment"],
    }


def build_reputation_feedback(settlement: dict[str, Any]) -> dict[str, Any]:
    """Convert settlement PnL into ERC-8004 Reputation Registry payload semantics."""
    pnl_pct = float(settlement.get("pnlBps") or 0.0) / 100
    fixed = encode_fixed_point(pnl_pct, decimals=2)
    return {
        "schema": "erc8004.reputation-feedback.v1",
        "registry": REPUTATION_REGISTRY_MAINNET,
        "score": fixed,
        "tag1": "DeFi",
        "tag2": "Trading",
        "feedbackUri": f"ipfs://quantagent-settlement/{settlement.get('settlementHash', 'pending')}",
        "sourceSettlement": settlement.get("settlementHash"),
    }
