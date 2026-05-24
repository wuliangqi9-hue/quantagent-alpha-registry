from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

RiskProfileState = Literal["aggressive", "neutral", "conservative"]
Direction = Literal["long", "short", "neutral"]


@dataclass(slots=True)
class DirectionDecision:
    """FinPos Direction Decision Agent output."""

    direction: Direction
    reasoning: str


@dataclass(slots=True)
class PositionPlan:
    """FinPos Quantity and Risk Decision Agent output."""

    schema: str
    targetExposure: float
    targetExposurePct: float
    maxSlippageBps: int
    stopLossBps: int
    takeProfitBps: int
    orderType: str
    timeInForce: str
    amountPolicy: str
    positionRationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "targetExposure": self.targetExposure,
            "targetExposurePct": self.targetExposurePct,
            "maxSlippageBps": self.maxSlippageBps,
            "stopLossBps": self.stopLossBps,
            "takeProfitBps": self.takeProfitBps,
            "orderType": self.orderType,
            "timeInForce": self.timeInForce,
            "amountPolicy": self.amountPolicy,
            "positionRationale": self.positionRationale,
        }


class DirectionDecisionAgent:
    """FinPos 方向决策智能体。

    该 Agent 只负责把异构因子流降噪成离散动作，不承担仓位大小计算。
    """

    VERSION = "finpos-direction-agent-1.0.0"

    def decide(self, *, regime: str, factors: dict[str, float]) -> DirectionDecision:
        momentum = factors.get("momentum", 0.0)
        trend = factors.get("trend", 0.0)
        if regime == "bull" or momentum > 0.15:
            direction: Direction = "long"
        elif regime == "bear" or momentum < -0.15:
            direction = "short"
        else:
            direction = "neutral"

        reasoning = (
            f"{self.VERSION}: regime={regime}, momentum={momentum:.3f}, "
            f"trend={trend:.3f}; denoised discrete action={direction}."
        )
        return DirectionDecision(direction=direction, reasoning=reasoning)


class QuantityRiskDecisionAgent:
    """FinPos 数量与风险决策智能体。

    该 Agent 显式消费连续仓位限制、历史回撤、未实现盈亏和连续亏损状态，
    输出可执行的目标资产配置权重。
    """

    VERSION = "finpos-quantity-risk-agent-1.0.0"

    def decide(
        self,
        *,
        direction: str,
        confidence: float,
        factors: dict[str, float],
        recent_volatility: float,
        risk_profile: RiskProfileState,
        memory_context: dict[str, Any] | None,
        risk_warnings: list[str],
        current_exposure: float = 0.0,
        unrealized_pnl_bps: float = 0.0,
    ) -> PositionPlan:
        if direction == "neutral":
            return PositionPlan(
                schema="quantagent.position-plan.v1",
                targetExposure=0.0,
                targetExposurePct=0,
                maxSlippageBps=0,
                stopLossBps=0,
                takeProfitBps=0,
                orderType="observe",
                timeInForce="none",
                amountPolicy="no-new-position",
                positionRationale="Neutral direction agent output selected observation only.",
            )

        volatility = abs(float(factors.get("volatility", 0.0) or 0.0))
        funding = abs(float(factors.get("funding", 0.0) or 0.0))
        summary = (memory_context or {}).get("summary", {})
        consecutive_losses = _safe_int(summary.get("consecutiveLosses"), 0)
        max_drawdown_bps = abs(_safe_float(summary.get("maxDrawdownBps"), 0.0))

        profile_cap = {"conservative": 0.18, "neutral": 0.32, "aggressive": 0.52}[risk_profile]
        base = profile_cap * max(0.25, min(1.0, confidence))
        vol_haircut = 0.70 if recent_volatility > 0.03 or volatility > 1.5 else 1.0
        funding_haircut = 0.82 if funding > 1.0 else 1.0
        streak_haircut = 0.65 if consecutive_losses >= 2 else 1.0
        drawdown_haircut = 0.75 if max_drawdown_bps > 250 else 1.0
        unrealized_haircut = 0.72 if unrealized_pnl_bps < -150 else 1.0

        raw_target = base * vol_haircut * funding_haircut * streak_haircut * drawdown_haircut * unrealized_haircut
        target = round(max(0.03, min(profile_cap, raw_target)), 4)

        # 价格大跌或未实现亏损时主动减仓，满足 FinPos 连续仓位状态转移要求。
        if unrealized_pnl_bps <= -1500:
            target = round(min(target, max(0.02, current_exposure * 0.35)), 4)
        elif unrealized_pnl_bps <= -500:
            target = round(min(target, max(0.03, current_exposure * 0.60)), 4)

        max_slippage, stop_loss, take_profit = _risk_bounds(risk_profile)
        if recent_volatility > 0.03:
            max_slippage = max(8, max_slippage - 4)
            stop_loss = max(35, stop_loss - 10)
        if consecutive_losses >= 2:
            max_slippage = max(6, max_slippage - 5)
            stop_loss = max(30, stop_loss - 15)

        order_type = "protected-limit"
        if risk_profile == "aggressive" and confidence >= 0.75 and len(risk_warnings) <= 2:
            order_type = "protected-market-or-rfq"
        if target <= 0.08 or risk_profile == "conservative":
            order_type = "limit-only"

        return PositionPlan(
            schema="quantagent.position-plan.v1",
            targetExposure=target,
            targetExposurePct=round(target * 100, 2),
            maxSlippageBps=max_slippage,
            stopLossBps=stop_loss,
            takeProfitBps=take_profit,
            orderType=order_type,
            timeInForce="ioc-or-5m-limit",
            amountPolicy="confidence-weighted-risk-cap",
            positionRationale=(
                f"{self.VERSION}: target={target:.2%}, current={current_exposure:.2%}, "
                f"confidence={confidence:.2f}, riskProfile={risk_profile}, "
                f"recentVol={recent_volatility:.4f}, funding={funding:.3f}, "
                f"maxDrawdown={max_drawdown_bps:.1f}bps, unrealizedPnL={unrealized_pnl_bps:.1f}bps, "
                f"consecutiveLosses={consecutive_losses}."
            ),
        )


def _risk_bounds(risk_profile: RiskProfileState) -> tuple[int, int, int]:
    if risk_profile == "conservative":
        return 12, 45, 75
    if risk_profile == "aggressive":
        return 28, 95, 155
    return 18, 70, 115


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
