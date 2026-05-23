from __future__ import annotations

from typing import Any

from .config import BYREAL_API_BASE, BYREAL_API_KEY, BYREAL_SIMULATION_MODE


def byreal_status() -> dict[str, Any]:
    configured = bool(BYREAL_API_BASE and BYREAL_API_KEY)
    return {
        "configured": configured,
        "mode": "api" if configured and not BYREAL_SIMULATION_MODE else "simulation",
        "apiBase": BYREAL_API_BASE or None,
        "skills": ["quote", "route-simulation", "risk-check", "execution-intent"],
        "message": (
            "Byreal/RealClaw credentials configured; execution adapter can call the ecosystem route layer."
            if configured
            else "Byreal/RealClaw adapter is present but running in simulation mode until credentials are configured."
        ),
    }


def build_execution_intent(analysis: dict[str, Any]) -> dict[str, Any]:
    selection = analysis.get("selection", {})
    direction = selection.get("signalDirection", "neutral")
    symbol = analysis.get("symbol", "BTC")
    confidence = float(selection.get("confidence", 0.0) or 0.0)
    risk_warnings = selection.get("riskWarnings", [])

    if direction == "long":
        action = "prepare-swap-or-long-route"
    elif direction == "short":
        action = "prepare-hedge-or-perps-route"
    else:
        action = "observe-only"

    size_hint = "micro" if confidence < 0.65 or len(risk_warnings) > 1 else "small"
    return {
        "provider": "Byreal/RealClaw",
        "mode": byreal_status()["mode"],
        "asset": symbol,
        "action": action,
        "sizeHint": size_hint,
        "strategyId": selection.get("strategyId"),
        "confidence": confidence,
        "slippagePolicy": "dynamic-estimate-required",
        "mevPolicy": "prefer-private-rpc-or-protected-route",
        "notes": [
            "Core alpha remains QuantAgent factor research.",
            "Execution is routed through the Mantle ecosystem adapter when configured.",
            "Simulation mode is allowed for demos but must be replaced by real credentials before final live execution.",
        ],
    }
