from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import BLOCKY402_FACILITATOR_URL, X402_MAX_AUTO_PAY_USD, X402_WALLET_ADDRESS


@dataclass(slots=True)
class X402PaymentSchema:
    amountUsd: float
    asset: str
    network: str
    recipient: str
    resource: str


class X402Client:
    """x402 Payment Required middleware.

    It parses HTTP 402 payment metadata and creates a facilitator payload.
    The current implementation is deterministic and offline-safe; a live
    Blocky402 call can replace `prepare_payment` without touching callers.
    """

    VERSION = "x402-client-1.0.0"

    def status(self) -> dict[str, Any]:
        return {
            "configured": bool(BLOCKY402_FACILITATOR_URL and X402_WALLET_ADDRESS),
            "facilitator": BLOCKY402_FACILITATOR_URL or None,
            "wallet": X402_WALLET_ADDRESS or None,
            "maxAutoPayUsd": X402_MAX_AUTO_PAY_USD,
        }

    def parse_schema(self, response_headers: dict[str, str], body: dict[str, Any] | None = None) -> X402PaymentSchema | None:
        body = body or {}
        raw_amount = body.get("amountUsd") or response_headers.get("x-402-amount-usd")
        recipient = body.get("recipient") or response_headers.get("x-402-recipient")
        if raw_amount is None or not recipient:
            return None
        return X402PaymentSchema(
            amountUsd=float(raw_amount),
            asset=str(body.get("asset") or response_headers.get("x-402-asset") or "USDC"),
            network=str(body.get("network") or response_headers.get("x-402-network") or "mantle"),
            recipient=str(recipient),
            resource=str(body.get("resource") or response_headers.get("x-402-resource") or "premium-factor-data"),
        )

    def should_pay(self, schema: X402PaymentSchema, alpha_value_bps: float) -> bool:
        if schema.amountUsd > X402_MAX_AUTO_PAY_USD:
            return False
        return alpha_value_bps >= 2.0

    def prepare_payment(self, schema: X402PaymentSchema, *, alpha_value_bps: float) -> dict[str, Any]:
        approved = self.should_pay(schema, alpha_value_bps)
        return {
            "schema": "quantagent.x402-payment-intent.v1",
            "clientVersion": self.VERSION,
            "approved": approved,
            "mode": "facilitator" if self.status()["configured"] else "simulation",
            "facilitator": BLOCKY402_FACILITATOR_URL or None,
            "payer": X402_WALLET_ADDRESS or "demo-agent-wallet",
            "payment": {
                "amountUsd": schema.amountUsd,
                "asset": schema.asset,
                "network": schema.network,
                "recipient": schema.recipient,
                "resource": schema.resource,
            },
            "alphaValueBps": alpha_value_bps,
            "payload": (
                f"partial-signature:{schema.network}:{schema.asset}:{schema.amountUsd}:{schema.recipient}"
                if approved
                else None
            ),
        }
