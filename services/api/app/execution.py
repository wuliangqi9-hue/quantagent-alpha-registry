from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any

from .byreal import byreal_status
from .x402 import X402Client, X402PaymentSchema


@dataclass(slots=True)
class ExecutionQuote:
    schema: str
    provider: str
    routeType: str
    venue: str
    expectedSlippageBps: float
    priceImpactBps: float
    mevProtectionRequired: bool
    quoteExpiryUnix: int
    executionMode: str
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RouteDecision:
    schema: str
    selectedRoute: str
    venue: str
    executionMode: str
    expectedSlippageBps: float
    mevProtectionRequired: bool
    routeRationale: str
    quoteExpiryUnix: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ByrealRFQAdapter:
    """Byreal / RealClaw execution adapter with explicit quote and route phases."""

    VERSION = "byreal-rfq-adapter-2.0.0"

    def build_intent(self, analysis: dict[str, Any]) -> dict[str, Any]:
        selection = analysis.get("selection", {})
        position = selection.get("positionPlan", {})
        direction = selection.get("signalDirection", "neutral")
        confidence = float(selection.get("confidence", 0.0) or 0.0)
        target_exposure = float(position.get("targetExposure") or 0.0)
        max_slippage = int(position.get("maxSlippageBps") or 0)

        intent = {
            "schema": "quantagent.execution-intent.v3",
            "provider": "Byreal/RealClaw",
            "adapterVersion": self.VERSION,
            "mode": byreal_status()["mode"],
            "asset": analysis.get("symbol", "BTC"),
            "action": _action_from_direction(direction, target_exposure),
            "amountPolicy": position.get("amountPolicy", "confidence-weighted-risk-cap"),
            "targetExposure": target_exposure,
            "targetExposurePct": position.get("targetExposurePct", 0),
            "orderType": position.get("orderType", "observe"),
            "strategyId": selection.get("strategyId"),
            "confidence": confidence,
            "slippageGuard": {
                "maxSlippageBps": max_slippage,
                "zeroPriceImpactPreferred": target_exposure >= 0.20 or max_slippage <= 15,
                "constantProductAmmPenalty": "direct x*y=k routing is avoided unless protected fallback is required",
            },
            "realClawMacro": {
                "enabled": direction != "neutral",
                "capabilities": ["scheduled macro trading", "LP farming intent", "perps risk envelope"],
                "maxLeverage": 1 if direction == "neutral" else min(3, max(1, round(confidence * 4))),
            },
            "notes": [
                "Execution is represented as quote -> route -> receipt.",
                "RFQ is preferred when slippage or MEV risk would damage alpha.",
            ],
        }
        quote = self.quote(intent, selection)
        route = self.select_route(intent, quote)
        intent.update(
            {
                "routeType": route.selectedRoute,
                "venuePreference": [route.venue, "protected CLMM fallback", "observe-only"],
                "expectedSlippageBps": route.expectedSlippageBps,
                "quoteExpiry": route.quoteExpiryUnix,
                "executionMode": route.executionMode,
                "routeRationale": route.routeRationale,
                "mevProtectionRequired": route.mevProtectionRequired,
                "mevPolicy": "rfq-or-private-mempool-required" if route.mevProtectionRequired else "protected-route-preferred",
                "quote": quote.to_dict(),
                "routeDecision": route.to_dict(),
                "x402": _x402_payment(intent),
            }
        )
        return intent

    def quote(self, intent: dict[str, Any], selection: dict[str, Any]) -> ExecutionQuote:
        target_exposure = float(intent.get("targetExposure") or 0.0)
        max_slippage = float((intent.get("slippageGuard") or {}).get("maxSlippageBps") or 0.0)
        risk_warnings = selection.get("riskWarnings", [])
        mode = byreal_status()["mode"]

        if intent.get("action") == "observe-only" or target_exposure <= 0:
            route_type = "observe-only"
            venue = "no-trade"
            slippage = 0.0
            price_impact = 0.0
            mev_required = False
            rationale = "No executable exposure requested; observe-only route selected."
        else:
            price_impact = round(max(1.0, target_exposure * 110), 2)
            mev_required = price_impact > 18 or len(risk_warnings) > 1
            if target_exposure >= 0.20 or max_slippage <= 15 or mev_required:
                route_type = "byreal-rfq"
                venue = "Byreal RFQ"
                slippage = min(max_slippage or 12.0, 4.0)
                rationale = "RFQ selected to avoid constant-product AMM price impact and public mempool leakage."
            else:
                route_type = "protected-clmm"
                venue = "RealClaw protected CLMM"
                slippage = min(max_slippage or 18.0, 14.0)
                rationale = "Protected CLMM route is sufficient for a smaller, bounded-slippage order."

        return ExecutionQuote(
            schema="quantagent.execution-quote.v1",
            provider="Byreal/RealClaw",
            routeType=route_type,
            venue=venue,
            expectedSlippageBps=round(float(slippage), 2),
            priceImpactBps=round(float(price_impact), 2),
            mevProtectionRequired=mev_required,
            quoteExpiryUnix=int(time.time()) + 90,
            executionMode=mode,
            rationale=rationale,
        )

    def select_route(self, intent: dict[str, Any], quote: ExecutionQuote) -> RouteDecision:
        return RouteDecision(
            schema="quantagent.route-decision.v1",
            selectedRoute=quote.routeType,
            venue=quote.venue,
            executionMode=quote.executionMode,
            expectedSlippageBps=quote.expectedSlippageBps,
            mevProtectionRequired=quote.mevProtectionRequired,
            routeRationale=quote.rationale,
            quoteExpiryUnix=quote.quoteExpiryUnix,
        )

    def receipt(self, route: RouteDecision) -> dict[str, Any]:
        return {
            "schema": "quantagent.execution-receipt.v1",
            "executionMode": route.executionMode,
            "routeType": route.selectedRoute,
            "venue": route.venue,
            "submitted": False,
            "txHash": None,
            "message": "Execution receipt is simulated until Byreal/RealClaw credentials are configured.",
        }


def _action_from_direction(direction: str, target_exposure: float) -> str:
    if direction == "neutral" or target_exposure <= 0:
        return "observe-only"
    if direction == "long":
        return "request-buy-route"
    if direction == "short":
        return "request-sell-route"
    return "request-protected-route"


def _x402_payment(intent: dict[str, Any]) -> dict[str, Any]:
    confidence = float(intent.get("confidence") or 0.0)
    x402_client = X402Client()
    schema = X402PaymentSchema(
        amountUsd=0.05,
        asset="USDC",
        network="mantle",
        recipient="premium-factor-provider",
        resource=f"{intent.get('asset', 'BTC')}-rfq-depth",
    )
    return x402_client.prepare_payment(schema, alpha_value_bps=max(0.0, confidence * 10))
