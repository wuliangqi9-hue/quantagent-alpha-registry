from __future__ import annotations

import math
from typing import Any


def build_state_vector(
    *,
    factors: dict[str, float],
    memory_context: dict[str, Any] | None,
    agent_reputation: dict[str, Any] | None,
) -> dict[str, float]:
    summary = (memory_context or {}).get("summary", {})
    reputation = _extract_reputation_score(agent_reputation)
    return {
        "momentum": float(factors.get("momentum", 0.0)),
        "trend": float(factors.get("trend", 0.0)),
        "volatility": abs(float(factors.get("volatility", 0.0))),
        "funding": float(factors.get("funding", 0.0)),
        "openInterest": float(factors.get("open_interest", 0.0)),
        "latestPnlBps": _safe_float(summary.get("latestPnlBps"), 0.0),
        "avgPnlBps": _safe_float(summary.get("avgPnlBps"), 0.0),
        "maxDrawdownBps": abs(_safe_float(summary.get("maxDrawdownBps"), 0.0)),
        "consecutiveLosses": _safe_float(summary.get("consecutiveLosses"), 0.0),
        "reputationScore": float(reputation or 5000),
    }


def critic_value(state: dict[str, float]) -> float:
    raw = (
        0.36 * state["momentum"]
        + 0.30 * state["trend"]
        - 0.18 * state["volatility"]
        - 0.12 * abs(state["funding"])
        - 0.0009 * state["maxDrawdownBps"]
        - 0.08 * state["consecutiveLosses"]
        + 0.00002 * (state["reputationScore"] - 5000)
    )
    return round(math.tanh(raw), 5)


def policy_score(state: dict[str, float], action: str) -> float:
    direction_bias = state["momentum"] + state["trend"]
    action_sign = 1.0 if action == "long" else -1.0 if action == "short" else 0.0
    risk_penalty = 0.16 * state["volatility"] + 0.05 * state["consecutiveLosses"]
    reward_memory = 0.0005 * state["avgPnlBps"] + 0.0003 * state["latestPnlBps"]
    score = action_sign * direction_bias + reward_memory - risk_penalty
    return round(math.tanh(score), 5)


def blend_confidence(base_confidence: float, score: float) -> float:
    blended = float(base_confidence) + 0.08 * score
    return round(max(0.30, min(0.95, blended)), 4)


def reward_features(state: dict[str, float]) -> dict[str, float]:
    return {
        "latestPnlBps": state["latestPnlBps"],
        "avgPnlBps": state["avgPnlBps"],
        "maxDrawdownBps": state["maxDrawdownBps"],
        "consecutiveLosses": state["consecutiveLosses"],
        "reputationScore": state["reputationScore"],
    }


def build_policy_output(
    *,
    factors: dict[str, float],
    memory_context: dict[str, Any] | None,
    agent_reputation: dict[str, Any] | None,
    action: str,
    base_confidence: float,
) -> dict[str, Any]:
    state = build_state_vector(
        factors=factors,
        memory_context=memory_context,
        agent_reputation=agent_reputation,
    )
    value = critic_value(state)
    score = policy_score(state, action)
    confidence = blend_confidence(base_confidence, score)
    return {
        "schema": "quantagent.policy-blender.v1",
        "stateVector": state,
        "criticValue": value,
        "policyScore": score,
        "policyConfidence": confidence,
        "rewardFeatures": reward_features(state),
        "rationale": (
            f"Policy blender adjusted confidence from {base_confidence:.2f} to {confidence:.2f} "
            f"using critic value {value:.3f} and policy score {score:.3f}."
        ),
    }


def _extract_reputation_score(agent_reputation: dict[str, Any] | None) -> int | None:
    if not agent_reputation:
        return None
    raw = agent_reputation.get("score")
    if raw is None and isinstance(agent_reputation.get("reputation"), dict):
        raw = agent_reputation["reputation"].get("score")
    try:
        return int(float(raw)) if raw is not None else None
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
