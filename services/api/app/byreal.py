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
    from .execution import ByrealRFQAdapter

    return ByrealRFQAdapter().build_intent(analysis)
