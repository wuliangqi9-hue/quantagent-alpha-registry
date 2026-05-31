from __future__ import annotations

import math
import logging
from typing import Any

from .a2c_trainer import get_a2c_trainer


logger = logging.getLogger(__name__)


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
    mode: str = "auto",
) -> dict[str, Any]:
    """构建策略融合输出（A2C 在线 + 静态线性双通道）。

    mode:
        - "auto": 当 A2C 训练成熟时自动使用 RL 通道，否则回退静态逻辑
        - "static": 强制使用静态线性融合（用于回测）
        - "a2c": 强制使用 A2C 推理（即使未训练成熟也尝试）
    """
    state = build_state_vector(
        factors=factors,
        memory_context=memory_context,
        agent_reputation=agent_reputation,
    )

    # ---- A2C 在线通道 ----
    a2c_result: dict[str, Any] | None = None
    a2c_error: dict[str, str] | None = None
    if mode in ("auto", "a2c"):
        try:
            a2c_trainer = get_a2c_trainer()
            # 转换为 trainer 期望的列表格式
            state_list = [
                state["momentum"],
                state["trend"],
                state["volatility"],
                state["funding"],
                state["openInterest"],
                state["latestPnlBps"],
                state["avgPnlBps"],
                state["maxDrawdownBps"],
                state["consecutiveLosses"],
                state["reputationScore"],
            ]
            a2c_result = a2c_trainer.act(state_list, deterministic=True)
        except Exception as exc:
            logger.warning("A2C policy inference failed; using static policy fallback", exc_info=True)
            a2c_error = {"type": type(exc).__name__, "message": str(exc)}
            a2c_result = None

    use_a2c = a2c_result is not None and a2c_result.get("active", False)

    if mode == "a2c":
        use_a2c = a2c_result is not None  # 强制使用（即使未训练成熟）
    if mode == "static":
        use_a2c = False

    if use_a2c and a2c_result is not None:
        # A2C 通道：actor 输出替代静态 policy_score，critic 输出替代静态 critic_value
        a2c_critic = a2c_result["critic_value"]
        a2c_probs = a2c_result["probs"]
        a2c_action_idx = a2c_result["action_idx"]
        action_map = {0: "long", 1: "short", 2: "neutral"}
        a2c_action_name = action_map.get(a2c_action_idx, "neutral")

        # 策略得分：选中动作的概率相对于均匀分布的偏移量
        uniform = 1.0 / len(a2c_probs)
        selected_prob = a2c_probs[a2c_action_idx]
        a2c_policy_score = round(math.tanh((selected_prob - uniform) * 3.0), 5)

        # 置信度融合：base_confidence × (1 + critic 调节)
        a2c_confidence = round(
            max(0.30, min(0.95, base_confidence + 0.12 * a2c_critic)), 4
        )

        return {
            "schema": "quantagent.policy-blender.v2-a2c",
            "stateVector": state,
            "criticValue": round(a2c_critic, 5),
            "policyScore": a2c_policy_score,
            "policyConfidence": a2c_confidence,
            "rewardFeatures": reward_features(state),
            "a2c": {
                "active": True,
                "episode_count": a2c_result.get("episode_count", get_a2c_trainer().episode_count),
                "action_idx": a2c_action_idx,
                "action_name": a2c_action_name,
                "probs": [round(p, 4) for p in a2c_probs],
                "entropy": round(a2c_result["entropy"], 5),
                "note": "A2C actor-critic network is active; RL-derived policy substitutes static linear fusion.",
            },
            "rationale": (
                f"A2C policy blender ({a2c_action_name}, prob={selected_prob:.3f}) "
                f"adjusted confidence from {base_confidence:.2f} to {a2c_confidence:.2f} "
                f"using critic value {a2c_critic:.3f} and policy score {a2c_policy_score:.3f}. "
                f"Episodes trained: {get_a2c_trainer().episode_count}."
            ),
        }

    # ---- 静态线性通道（fallback） ----
    value = critic_value(state)
    score = policy_score(state, action)
    confidence = blend_confidence(base_confidence, score)

    a2c_fallback_note = {}
    if a2c_result is not None and not a2c_result.get("active", False):
        a2c_fallback_note = {
            "a2c": {
                "active": False,
                "episode_count": get_a2c_trainer().episode_count,
                "note": (
                    f"A2C trainer has {get_a2c_trainer().episode_count} episodes; "
                    f"minimum {get_a2c_trainer().cfg.min_episodes_before_active} required. "
                    "Using static linear fallback."
                ),
            }
        }
    elif a2c_error is not None:
        a2c_fallback_note = {
            "a2c": {
                "active": False,
                "error": a2c_error,
                "note": "A2C inference failed; static linear fallback was used.",
            }
        }

    output = {
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
    output.update(a2c_fallback_note)
    return output


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
