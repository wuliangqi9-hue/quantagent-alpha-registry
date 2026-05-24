from __future__ import annotations

from typing import Any

from .byreal import byreal_status
from .x402 import X402Client, X402PaymentSchema


class ByrealRFQAdapter:
    """Byreal / RealClaw execution adapter.

    This adapter removes direct AMM routing from the API surface. The default
    mode simulates RFQ and scheduled macro trading, while the method names and
    payloads map cleanly to the live SDK/CLI integration.
    """

    VERSION = "byreal-rfq-adapter-1.0.0"

    def build_intent(self, analysis: dict[str, Any]) -> dict[str, Any]:
        selection = analysis.get("selection", {})
        position = selection.get("positionPlan", {})
        direction = selection.get("signalDirection", "neutral")
        confidence = float(selection.get("confidence", 0.0) or 0.0)
        max_slippage = int(position.get("maxSlippageBps") or 0)
        target_exposure = float(position.get("targetExposure") or 0.0)
        risk_warnings = selection.get("riskWarnings", [])

        if direction == "neutral" or target_exposure <= 0:
            route_type = "observe-only"
            action = "observe-only"
        elif target_exposure >= 0.20 or max_slippage <= 15:
            route_type = "rfq-zero-price-impact"
            action = "request-byreal-rfq"
        else:
            route_type = "protected-clmm-fallback"
            action = "request-protected-route"

        mev_required = route_type == "rfq-zero-price-impact" or len(risk_warnings) > 1
        x402_client = X402Client()
        x402_payment = x402_client.prepare_payment(
            X402PaymentSchema(
                amountUsd=0.05,
                asset="USDC",
                network="mantle",
                recipient="premium-factor-provider",
                resource=f"{analysis.get('symbol', 'BTC')}-rfq-depth",
            ),
            alpha_value_bps=max(0.0, confidence * 10),
        )

        return {
            "schema": "quantagent.execution-intent.v2",
            "provider": "Byreal/RealClaw",
            "adapterVersion": self.VERSION,
            "mode": byreal_status()["mode"],
            "asset": analysis.get("symbol", "BTC"),
            "action": action,
            "routeType": route_type,
            "venuePreference": ["Byreal RFQ", "RealClaw Scheduled Macro", "protected CLMM fallback"],
            "amountPolicy": position.get("amountPolicy", "confidence-weighted-risk-cap"),
            "targetExposure": target_exposure,
            "targetExposurePct": position.get("targetExposurePct", 0),
            "orderType": position.get("orderType", "observe"),
            "strategyId": selection.get("strategyId"),
            "confidence": confidence,
            "slippageGuard": {
                "maxSlippageBps": max_slippage,
                "zeroPriceImpactPreferred": route_type == "rfq-zero-price-impact",
                "constantProductAmmPenalty": "x*y=k price impact avoided unless protected fallback is required",
            },
            "mevProtectionRequired": mev_required,
            "mevPolicy": "rfq-or-private-mempool-required" if mev_required else "protected-route-preferred",
            "realClawMacro": {
                "enabled": direction != "neutral",
                "capabilities": ["scheduled macro trading", "LP farming intent", "perps risk envelope"],
                "maxLeverage": 1 if direction == "neutral" else min(3, max(1, round(confidence * 4))),
            },
            "x402": x402_payment,
            "notes": [
                "Direct constant-product AMM routing is not exposed by this adapter.",
                "RFQ is preferred for zero price impact and MEV resistance.",
                "Simulation mode degrades safely until Byreal/RealClaw credentials are configured.",
            ],
        }
