from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# FinPos — Position-Aware Multi-timescale Reward Agent
# ---------------------------------------------------------------------------
# 参考报告第 2.1 节：FinPos 双智能体决策结构
#   - Direction Decision Agent：利用 LLM 推导宏观方向性逻辑
#   - Quantity & Risk Decision Agent：结合连续仓位、滑点容忍度与风险预算，
#     计算精确交易体积
# 多时间尺度奖励信号：
#   - 即时盈亏（Immediate PnL）：单次决策的实际 PnL（bp）
#   - 累积回报（Cumulative Returns）：滑动窗口内的累计 PnL
#   - 夏普比率（Sharpe Ratio）：风险调整后收益
#   - 仓位暴露惩罚（Exposure Penalty）：过度集中持仓的凸性惩罚
# ---------------------------------------------------------------------------


@dataclass
class PositionSnapshot:
    """当前仓位快照。"""

    symbol: str
    side: str = "flat"  # long / short / flat
    entry_price: float = 0.0
    current_price: float = 0.0
    size_base: float = 0.0  # 基础货币数量
    size_quote: float = 0.0  # 计价货币价值
    unrealized_pnl_bps: float = 0.0
    margin_used_pct: float = 0.0  # 已用保证金百分比
    exposure_pct: float = 0.0  # 占组合百分比
    last_updated_unix: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "entryPrice": self.entry_price,
            "currentPrice": self.current_price,
            "sizeBase": self.size_base,
            "sizeQuote": self.size_quote,
            "unrealizedPnlBps": self.unrealized_pnl_bps,
            "marginUsedPct": self.margin_used_pct,
            "exposurePct": self.exposure_pct,
            "lastUpdatedUnix": self.last_updated_unix,
        }


@dataclass
class FinPosDecision:
    """FinPos 双智能体联合决策输出。"""

    # 方向决策智能体输出
    directional_bias: str = "neutral"  # bullish / bearish / neutral
    directional_confidence: float = 0.0  # 0.0 - 1.0
    directional_rationale: str = ""
    macro_regime: str = "undefined"  # trending / ranging / volatile / crisis

    # 数量与风险决策智能体输出
    action: str = "HOLD"  # BUY / SELL / HOLD
    order_type: str = "LIMIT"  # MARKET / LIMIT / OBSERVE
    size_quote: float = 0.0  # 建议交易量（计价货币）
    size_pct_of_position: float = 0.0  # 相对当前仓位的变化百分比
    limit_price_offset_bps: float = 0.0  # 限价单偏移（bp）
    stop_loss_bps: float = 200.0  # 止损距离（bp）
    max_slippage_bps: float = 50.0  # 最大滑点容忍（bp）
    risk_adjustment_factor: float = 1.0  # 风险调节系数

    # 执行路由
    execution_route: str = "byreal-rfq"  # byreal-rfq / clmm-private / clmm-public
    route_rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "directionalBias": self.directional_bias,
            "directionalConfidence": self.directional_confidence,
            "directionalRationale": self.directional_rationale,
            "macroRegime": self.macro_regime,
            "action": self.action,
            "orderType": self.order_type,
            "sizeQuote": self.size_quote,
            "sizePctOfPosition": self.size_pct_of_position,
            "limitPriceOffsetBps": self.limit_price_offset_bps,
            "stopLossBps": self.stop_loss_bps,
            "maxSlippageBps": self.max_slippage_bps,
            "riskAdjustmentFactor": self.risk_adjustment_factor,
            "executionRoute": self.execution_route,
            "routeRationale": self.route_rationale,
        }


@dataclass
class MultiTimescaleReward:
    """多时间尺度奖励信号。"""

    # 即时信号（单次结算）
    immediate_pnl_bps: float = 0.0
    immediate_pnl_usd: float = 0.0
    direction_correct: bool = False

    # 短期窗口（最近 N 次结算，默认 5 次）
    short_window_pnl_bps: float = 0.0
    short_window_sharpe: float = 0.0
    short_window_win_rate: float = 0.0

    # 中期窗口（最近 N 次，默认 20 次）
    medium_window_pnl_bps: float = 0.0
    medium_window_sharpe: float = 0.0
    medium_window_win_rate: float = 0.0

    # 暴露惩罚
    exposure_penalty_bps: float = 0.0  # 仓位过度集中的惩罚

    # 综合得分（加权融合）
    composite_score: float = 0.0

    # 元数据
    calculation_unix: int = 0
    window_sizes: dict[str, int] = field(default_factory=lambda: {"short": 5, "medium": 20})

    def to_dict(self) -> dict[str, Any]:
        return {
            "immediatePnlBps": self.immediate_pnl_bps,
            "immediatePnlUsd": self.immediate_pnl_usd,
            "directionCorrect": self.direction_correct,
            "shortWindow": {
                "pnlBps": self.short_window_pnl_bps,
                "sharpe": self.short_window_sharpe,
                "winRate": self.short_window_win_rate,
                "windowSize": self.window_sizes["short"],
            },
            "mediumWindow": {
                "pnlBps": self.medium_window_pnl_bps,
                "sharpe": self.medium_window_sharpe,
                "winRate": self.medium_window_win_rate,
                "windowSize": self.window_sizes["medium"],
            },
            "exposurePenaltyBps": self.exposure_penalty_bps,
            "compositeScore": self.composite_score,
        }


class FinPosRewardEngine:
    """FinPos 多时间尺度奖励引擎。

    在每次 /api/settle 结算时：
    1. 加载历史结算记录（从 MemoryStore 获取）
    2. 计算即时、短期、中期三个时间尺度的奖励
    3. 施加仓位暴露凸性惩罚
    4. 生成综合得分，注入回 strategy-selector 的自我反思管道
    """

    def __init__(self) -> None:
        pass

    def compute_rewards(
        self,
        *,
        current_pnl_bps: float,
        current_pnl_usd: float,
        direction_correct: bool,
        current_exposure_pct: float,
        max_allowed_exposure_pct: float = 30.0,
        historical_records: list[dict[str, Any]] | None = None,
        short_window: int = 5,
        medium_window: int = 20,
    ) -> MultiTimescaleReward:
        """计算多时间尺度奖励信号。

        Args:
            current_pnl_bps: 当前结算的 PnL（bp）
            current_pnl_usd: 当前结算的 PnL（USD）
            direction_correct: 方向判断是否正确
            current_exposure_pct: 当前仓位暴露百分比
            max_allowed_exposure_pct: 最大允许暴露百分比
            historical_records: 历史结算记录列表
            short_window: 短期窗口大小
            medium_window: 中期窗口大小
        """
        records = historical_records or []
        timestamp = int(time.time())

        reward = MultiTimescaleReward(
            immediate_pnl_bps=current_pnl_bps,
            immediate_pnl_usd=current_pnl_usd,
            direction_correct=direction_correct,
            calculation_unix=timestamp,
            window_sizes={"short": short_window, "medium": medium_window},
        )

        # --- 提取历史 PnL 序列 ---
        pnl_series: list[float] = []
        for rec in records:
            settlement = rec.get("settlement", rec)
            pnl = float(settlement.get("pnlBps", settlement.get("pnl_bps", 0)))
            pnl_series.append(pnl)

        # 将当前 PnL 追加到序列末尾
        all_pnl = pnl_series + [current_pnl_bps]

        # --- 短期窗口统计 ---
        short_pnls = all_pnl[-short_window:] if len(all_pnl) >= short_window else all_pnl
        if short_pnls:
            reward.short_window_pnl_bps = sum(short_pnls)
            reward.short_window_win_rate = sum(1 for p in short_pnls if p > 0) / len(short_pnls)
            reward.short_window_sharpe = self._approximate_sharpe(short_pnls)

        # --- 中期窗口统计 ---
        medium_pnls = all_pnl[-medium_window:] if len(all_pnl) >= medium_window else all_pnl
        if medium_pnls:
            reward.medium_window_pnl_bps = sum(medium_pnls)
            reward.medium_window_win_rate = sum(1 for p in medium_pnls if p > 0) / len(medium_pnls)
            reward.medium_window_sharpe = self._approximate_sharpe(medium_pnls)

        # --- 暴露惩罚 ---
        reward.exposure_penalty_bps = self._compute_exposure_penalty(
            current_exposure_pct, max_allowed_exposure_pct
        )

        # --- 综合得分（加权） ---
        # 权重设计：即时 PnL 40% + 短期 25% + 中期 20% + 方向准确 10% + 暴露惩罚 5%
        immediate_score = _sigmoid(current_pnl_bps / 100.0)  # 归一化到 (-1, 1) 附近
        short_score = _sigmoid(reward.short_window_sharpe * 0.5) if reward.short_window_pnl_bps != 0 else 0.0
        medium_score = _sigmoid(reward.medium_window_sharpe * 0.3) if reward.medium_window_pnl_bps != 0 else 0.0
        direction_score = 1.0 if direction_correct else -0.5
        penalty_score = -_sigmoid(reward.exposure_penalty_bps / 50.0)

        reward.composite_score = (
            0.40 * immediate_score
            + 0.25 * short_score
            + 0.20 * medium_score
            + 0.10 * direction_score
            + 0.05 * penalty_score
        )

        return reward

    @staticmethod
    def _compute_exposure_penalty(exposure_pct: float, max_allowed: float) -> float:
        """凸性暴露惩罚。

        当仓位暴露超过最大允许值时，惩罚呈二次方增长。
        """
        if exposure_pct <= max_allowed:
            return 0.0
        excess = (exposure_pct - max_allowed) / max_allowed  # 0.0+
        return excess * excess * 100.0  # 凸性惩罚，单位 bp

    @staticmethod
    def _approximate_sharpe(pnl_series: list[float], risk_free_annual: float = 0.02) -> float:
        """快速近似夏普比率。

        使用简化公式：均值 / 标准差 * sqrt(252)（假设日频数据）。
        对于日内数据，使用 sqrt(365*24) 或由调用方按实际频率换算。
        """
        if len(pnl_series) < 2:
            return 0.0
        mean_pnl = sum(pnl_series) / len(pnl_series)
        variance = sum((p - mean_pnl) ** 2 for p in pnl_series) / (len(pnl_series) - 1)
        std_pnl = variance**0.5
        if std_pnl == 0:
            return 0.0
        # 假设每个结算周期为 4 小时，annualization factor ≈ sqrt(6*365) ≈ 46.8
        annual_factor = 46.8
        annualized_return = mean_pnl * annual_factor / 10000.0  # bp 转小数
        annualized_std = std_pnl * annual_factor / 10000.0
        if annualized_std == 0:
            return 0.0
        return (annualized_return - risk_free_annual) / annualized_std

    def generate_position_aware_advice(
        self,
        *,
        direction_bias: str,
        direction_confidence: float,
        current_position: PositionSnapshot | None,
        risk_budget_remaining_pct: float,
        atr_bps: float = 200.0,
        estimated_pool_depth_quote: float = 0.0,
    ) -> FinPosDecision:
        """基于当前位置与风险预算，生成仓位感知的执行建议。

        这是 FinPos 双智能体结构中 Quantity & Risk Decision Agent 的核心逻辑。
        """
        pos = current_position
        decision = FinPosDecision()
        decision.directional_bias = direction_bias
        decision.directional_confidence = direction_confidence

        # --- 宏观体制推断 ---
        decision.macro_regime = self._infer_regime(atr_bps, risk_budget_remaining_pct)

        # --- 风险调节系数 ---
        # 在高波动或低风险预算时自动降低仓位
        if decision.macro_regime == "crisis":
            decision.risk_adjustment_factor = 0.25
            decision.directional_rationale = "Crisis regime detected: maximum risk reduction."
        elif decision.macro_regime == "volatile":
            decision.risk_adjustment_factor = 0.50
            decision.directional_rationale = "Elevated volatility: conservative sizing."
        elif risk_budget_remaining_pct < 20:
            decision.risk_adjustment_factor = 0.40
            decision.directional_rationale = "Low remaining risk budget: reduced exposure."
        else:
            decision.risk_adjustment_factor = min(direction_confidence, 0.85)
            decision.directional_rationale = f"Confidence-weighted sizing at {direction_confidence:.0%}."

        # --- 动作判定 ---
        if pos and pos.side != "flat":
            # 已有仓位：基于方向偏差与当前持仓决定操作
            if direction_bias == "bullish" and pos.side == "short":
                decision.action = "BUY"  # 平空
                decision.size_pct_of_position = 100.0
            elif direction_bias == "bearish" and pos.side == "long":
                decision.action = "SELL"  # 平多
                decision.size_pct_of_position = 100.0
            elif direction_bias == "bullish" and pos.side == "long":
                decision.action = "BUY"  # 加仓
                decision.size_pct_of_position = 20.0 * decision.risk_adjustment_factor
            elif direction_bias == "bearish" and pos.side == "short":
                decision.action = "SELL"  # 加仓
                decision.size_pct_of_position = 20.0 * decision.risk_adjustment_factor
            else:
                decision.action = "HOLD"
                decision.size_pct_of_position = 0.0
        else:
            # 无仓位：纯方向性开仓
            if direction_bias == "bullish":
                decision.action = "BUY"
                decision.size_pct_of_position = 100.0 * decision.risk_adjustment_factor  # 相对于风险预算
            elif direction_bias == "bearish":
                decision.action = "SELL"
                decision.size_pct_of_position = 100.0 * decision.risk_adjustment_factor
            else:
                decision.action = "HOLD"

        # --- 订单类型与执行路由 ---
        # 大额订单 → Byreal RFQ（零滑点、MEV 保护）
        if pos and estimated_pool_depth_quote > 0:
            size_ratio = (pos.size_quote * abs(decision.size_pct_of_position) / 100.0) / estimated_pool_depth_quote
            if size_ratio > 0.005:  # > 0.5% 池深度
                decision.order_type = "MARKET"  # RFQ 模式内部处理
                decision.execution_route = "byreal-rfq"
                decision.route_rationale = (
                    f"Order size ({size_ratio:.2%} of pool depth) exceeds RFQ threshold. "
                    "Routing via Byreal off-chain RFQ for zero price impact and MEV protection."
                )
            else:
                decision.order_type = "LIMIT"
                decision.execution_route = "clmm-private"
                decision.route_rationale = "Small order: private CLMM with tight limit."
        else:
            decision.order_type = "LIMIT"
            decision.execution_route = "clmm-private"

        # --- 数量计算 ---
        if pos:
            decision.size_quote = pos.size_quote * abs(decision.size_pct_of_position) / 100.0
        decision.limit_price_offset_bps = 10.0  # 默认 10bp 偏移
        decision.stop_loss_bps = max(atr_bps * 2.0, 100.0)  # 2 ATR 止损
        decision.max_slippage_bps = (
            25.0 if decision.execution_route == "byreal-rfq" else 50.0
        )

        return decision

    @staticmethod
    def _infer_regime(atr_bps: float, risk_budget_remaining_pct: float) -> str:
        """基于 ATR 和风险预算推断市场体制。"""
        if atr_bps > 500:
            return "crisis"
        if atr_bps > 200:
            return "volatile"
        if risk_budget_remaining_pct < 20:
            return "volatile"  # 即使波动不大，低风险预算也视为高压
        return "trending"


# ------------------------------------------------------------------
# 辅助函数
# ------------------------------------------------------------------

def _sigmoid(x: float) -> float:
    """Sigmoid 归一化到 (-1, 1)。"""
    import math

    try:
        return 2.0 / (1.0 + math.exp(-x)) - 1.0
    except OverflowError:
        return 1.0 if x > 0 else -1.0


# ------------------------------------------------------------------
# 模块级单例
# ------------------------------------------------------------------

_finpos_engine: FinPosRewardEngine | None = None


def get_finpos_engine() -> FinPosRewardEngine:
    global _finpos_engine
    if _finpos_engine is None:
        _finpos_engine = FinPosRewardEngine()
    return _finpos_engine


def compute_finpos_rewards(
    *,
    current_pnl_bps: float,
    current_pnl_usd: float,
    direction_correct: bool,
    current_exposure_pct: float,
    max_allowed_exposure_pct: float = 30.0,
    historical_records: list[dict[str, Any]] | None = None,
) -> MultiTimescaleReward:
    return get_finpos_engine().compute_rewards(
        current_pnl_bps=current_pnl_bps,
        current_pnl_usd=current_pnl_usd,
        direction_correct=direction_correct,
        current_exposure_pct=current_exposure_pct,
        max_allowed_exposure_pct=max_allowed_exposure_pct,
        historical_records=historical_records,
    )