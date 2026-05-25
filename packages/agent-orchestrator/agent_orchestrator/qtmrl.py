from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class A2CDecision:
    """QTMRL Advantage Actor-Critic lightweight output."""

    schema: str
    stateVector: dict[str, float]
    actorExposure: float
    stateValue: float
    actionValue: float
    advantage: float
    confidence: float
    explorationNeeded: bool
    rewardEstimate: float
    gamma: float
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "stateVector": self.stateVector,
            "actorExposure": self.actorExposure,
            "stateValue": self.stateValue,
            "actionValue": self.actionValue,
            "advantage": self.advantage,
            "confidence": self.confidence,
            "explorationNeeded": self.explorationNeeded,
            "rewardEstimate": self.rewardEstimate,
            "gamma": self.gamma,
            "rationale": self.rationale,
        }


class A2CPolicyEngine:
    """QTMRL A2C 强化学习骨架。

    这是可运行的轻量实现：状态空间来自 factor-engine，多时间尺度奖励
    来自 memory summary。后续可以把权重替换为训练出的 Actor/Critic 网络。
    """

    VERSION = "qtmrl-a2c-policy-1.0.0"

    def __init__(self, gamma: float = 0.72) -> None:
        self.gamma = gamma

    def evaluate(
        self,
        *,
        factor_summary: dict[str, Any],
        memory_context: dict[str, Any],
    ) -> A2CDecision:
        state = _state_vector(factor_summary)
        summary = (memory_context or {}).get("summary", {})
        immediate = _safe_float(summary.get("latestPnlBps"), 0.0) / 10000
        cumulative = _safe_float(summary.get("cumulativePnlBps"), _safe_float(summary.get("avgPnlBps"), 0.0)) / 10000
        reward = immediate + self.gamma * cumulative

        momentum = state.get("momentum", 0.0)
        trend = state.get("trend", 0.0)
        volatility = abs(state.get("volatility", 0.0))
        funding = abs(state.get("funding", 0.0))
        drawdown = abs(_safe_float(summary.get("maxDrawdownBps"), 0.0)) / 10000

        state_value = math.tanh(0.45 * momentum + 0.35 * trend - 0.25 * volatility - 0.18 * funding - drawdown)
        actor_raw = 0.28 + 0.18 * math.tanh(momentum + trend) - 0.10 * min(1.0, volatility) - 0.08 * min(1.0, drawdown)
        actor_exposure = round(max(0.0, min(0.58, actor_raw)), 4)
        action_value = math.tanh(state_value + actor_exposure + reward)
        advantage = action_value - state_value

        # ---- 置信度与探索标记（AlphaQuanter 主动信息获取）----
        # 置信度 = 1 - |advantage| / max_advantage_range
        # advantage 越小（不确定性越高）→ 置信度越低 → 需要主动探索
        confidence_raw = 1.0 - min(1.0, abs(advantage) / 0.35)
        confidence = round(confidence_raw, 4)
        # 当置信度低于 30% 且波动率适中时，触发主动数据探索
        exploration_needed = confidence < 0.30 and volatility < 1.8

        return A2CDecision(
            schema="quantagent.qtmrl-a2c.v2",
            stateVector=state,
            actorExposure=actor_exposure,
            stateValue=round(state_value, 5),
            actionValue=round(action_value, 5),
            advantage=round(advantage, 5),
            confidence=confidence,
            explorationNeeded=exploration_needed,
            rewardEstimate=round(reward, 5),
            gamma=self.gamma,
            rationale=(
                f"{self.VERSION}: A(s,a)=Q(s,a)-V(s)={advantage:.5f}; "
                f"confidence={confidence:.2%}; explore={exploration_needed}; "
                f"R=immediate+gamma*cumulative={reward:.5f}; "
                f"actor exposure proposal={actor_exposure:.2%}."
            ),
        )


def _state_vector(factor_summary: dict[str, Any]) -> dict[str, float]:
    factors = {
        item["id"]: float(item["score"])
        for item in factor_summary.get("factors", [])
        if item.get("id") and item.get("score") is not None and not item.get("missing")
    }
    return {
        "momentum": factors.get("momentum", 0.0),
        "trend": factors.get("trend", 0.0),
        "volatility": abs(factors.get("volatility", 0.0)),
        "funding": factors.get("funding", 0.0),
        "openInterest": factors.get("open_interest", 0.0),
        "recentVolatility24h": _safe_float(factor_summary.get("recentVolatility24h"), 0.0),
    }


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
