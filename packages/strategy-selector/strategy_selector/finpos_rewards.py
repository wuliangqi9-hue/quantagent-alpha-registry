"""FinPos 多时间尺度复合奖励函数。

基于 FinPos 架构的多时间尺度奖励信号矩阵（论文 §2.1），将即时盈亏、
短期夏普比率、中期累积回报和回撤惩罚融合为 [−1, 1] 区间的单一复合得分，
直接供 A2C 在线训练器作为 reward 信号和 selector 的 adaptive confidence
调节因子使用。

设计目标：
- 短视的 /settle 单次 PnL 被提升为包含中长期统计特征的复合信号
- 避免单次大赚掩盖连续亏损的幸存者偏差
- 复合得分可以直接作为 soft risk cap 注入 FinPos QuantityRiskDecisionAgent
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RewardWindow:
    """滚动窗口统计，用于在线计算短期/中期夏普和回撤。"""

    maxlen_short: int = 20  # 短期窗口（约 4 小时，5min 频率）
    maxlen_mid: int = 60  # 中期窗口（约 1 天）
    short_returns_bps: deque[float] = field(default_factory=lambda: deque(maxlen=20))
    mid_returns_bps: deque[float] = field(default_factory=lambda: deque(maxlen=60))
    cumulative_returns_bps: list[float] = field(default_factory=list)
    peak_cumulative: float = 0.0

    def push(self, single_return_bps: float) -> None:
        """添加一个新观测值并更新滚动统计。"""
        self.short_returns_bps.append(single_return_bps)
        self.mid_returns_bps.append(single_return_bps)
        # 累积回报
        if not self.cumulative_returns_bps:
            self.cumulative_returns_bps.append(single_return_bps)
        else:
            self.cumulative_returns_bps.append(
                self.cumulative_returns_bps[-1] + single_return_bps
            )
        # 保持 cumulative_returns 与 mid 窗口长度一致
        while len(self.cumulative_returns_bps) > self.maxlen_mid:
            self.cumulative_returns_bps.pop(0)
        # 更新峰值
        if self.cumulative_returns_bps:
            self.peak_cumulative = max(self.peak_cumulative, self.cumulative_returns_bps[-1])

    def short_sharpe(self) -> float:
        """短期（窗口内）年化夏普比率近似值。"""
        data = list(self.short_returns_bps)
        n = len(data)
        if n < 3:
            return 0.0
        mean_bps = sum(data) / n
        var = sum((x - mean_bps) ** 2 for x in data) / (n - 1)
        std_bps = math.sqrt(max(var, 1e-8))
        if std_bps == 0:
            return 0.0
        # 短期近似年化（假设 5min bar → 288/d → 105120/yr）
        ann_factor = math.sqrt(105120)  # 年化波动率缩放
        return mean_bps / std_bps * ann_factor if std_bps > 0 else 0.0

    def mid_sharpe(self) -> float:
        """中期年化夏普比率近似值。"""
        data = list(self.mid_returns_bps)
        n = len(data)
        if n < 5:
            return 0.0
        mean_bps = sum(data) / n
        var = sum((x - mean_bps) ** 2 for x in data) / (n - 1)
        std_bps = math.sqrt(max(var, 1e-8))
        ann_factor = math.sqrt(105120)
        return mean_bps / std_bps * ann_factor if std_bps > 0 else 0.0

    def drawdown_bps(self) -> float:
        """当前累积回撤（bps）。"""
        if not self.cumulative_returns_bps:
            return 0.0
        return self.peak_cumulative - self.cumulative_returns_bps[-1]

    def current_cumulative_bps(self) -> float:
        """当前累积回报（bps）。"""
        if not self.cumulative_returns_bps:
            return 0.0
        return self.cumulative_returns_bps[-1]


# ------------------------------------------------------------------
# 复合得分公式
# ------------------------------------------------------------------

def compute_composite_score(
    *,
    immediate_pnl_bps: float,
    latest_pnl_bps: float,
    avg_pnl_bps: float,
    max_drawdown_bps: float,
    consecutive_losses: int,
    short_sharpe: float,
    mid_sharpe: float,
) -> dict[str, Any]:
    """计算 FinPos 多时间尺度复合奖励得分。

    得分范围：[−1, 1]，正值表示策略有效，负值表示当前行为需要纠偏。

    核心公式（论文 §2.1 多尺度奖励矩阵）：
    composite = tanh(
        0.35 × immediate_pnl_norm +
        0.25 × short_sharpe_norm +
        0.20 × mid_sharpe_norm +
        0.15 × memory_health_norm +
        0.05 × drawdown_penalty_norm
    )

    Args:
        immediate_pnl_bps: 单次交易盈亏（bps），如 +15.2
        latest_pnl_bps: 最近一次结算的 PnL（bps），来自 memory summary
        avg_pnl_bps: 历史平均 PnL（bps），来自 memory summary
        max_drawdown_bps: 历史最大回撤（bps），来自 memory summary
        consecutive_losses: 连续亏损次数
        short_sharpe: 短期滚动夏普（年化）
        mid_sharpe: 中期滚动夏普（年化）

    Returns:
        {
            "composite_score": float ∈ [−1, 1],
            "immediate_pnl_norm": float,
            "short_sharpe_norm": float,
            "mid_sharpe_norm": float,
            "memory_health_norm": float,
            "drawdown_penalty_norm": float,
            "safe_for_position_sizing": bool,
        }
    """
    # ---- 各组件归一化到 [−1, 1] ----
    # 即时盈亏归一化（典型范围 ±50 bps → tanh 映射）
    immediate_norm = math.tanh(immediate_pnl_bps / 50.0)

    # 短期夏普归一化（典型范围 ±3 → tanh(x/3)）
    short_sharpe_norm = math.tanh(short_sharpe / 3.0)

    # 中期夏普归一化
    mid_sharpe_norm = math.tanh(mid_sharpe / 3.0)

    # 记忆健康度：综合 Avg PnL 和连续亏损
    avg_pnl_norm = math.tanh(avg_pnl_bps / 80.0)
    loss_penalty = -math.tanh(consecutive_losses / 4.0)
    memory_health = 0.6 * avg_pnl_norm + 0.4 * loss_penalty

    # 回撤惩罚：回撤越大惩罚越重
    drawdown_penalty = -math.tanh(max_drawdown_bps / 500.0)

    # ---- 加权复合 ----
    raw = (
        0.35 * immediate_norm
        + 0.25 * short_sharpe_norm
        + 0.20 * mid_sharpe_norm
        + 0.15 * memory_health
        + 0.05 * drawdown_penalty
    )

    composite = round(max(-1.0, min(1.0, math.tanh(raw * 1.2))), 5)

    # ---- 安全阈值：决定是否可以增加仓位 ----
    safe_for_sizing = composite > -0.3 and consecutive_losses < 3 and max_drawdown_bps < 500

    return {
        "composite_score": composite,
        "immediate_pnl_norm": round(immediate_norm, 4),
        "short_sharpe_norm": round(short_sharpe_norm, 4),
        "mid_sharpe_norm": round(mid_sharpe_norm, 4),
        "memory_health_norm": round(memory_health, 4),
        "drawdown_penalty_norm": round(drawdown_penalty, 4),
        "safe_for_position_sizing": safe_for_sizing,
        "formula_version": "finpos-multi-timescale-1.0.0",
    }


def compute_reward_for_a2c(
    *,
    immediate_pnl_bps: float,
    memory_context: dict[str, Any] | None = None,
    reward_window: RewardWindow | None = None,
) -> dict[str, Any]:
    """一站式接口：从 memory_context 和 reward_window 计算 A2C 奖励。

    Args:
        immediate_pnl_bps: 单次交易盈亏（bps）
        memory_context: agent-memory 的 JSONL summary 输出
        reward_window: 滚动窗口对象（如不传则用零值）

    Returns:
        A2C reward + 诊断明细
    """
    summary = (memory_context or {}).get("summary", {}) if memory_context else {}

    latest_pnl = float(summary.get("latestPnlBps", 0.0))
    avg_pnl = float(summary.get("avgPnlBps", 0.0))
    max_dd = abs(float(summary.get("maxDrawdownBps", 0.0)))
    cons_losses = int(summary.get("consecutiveLosses", 0))

    if reward_window is not None:
        reward_window.push(immediate_pnl_bps)
        short_s = reward_window.short_sharpe()
        mid_s = reward_window.mid_sharpe()
    else:
        short_s = 0.0
        mid_s = 0.0

    result = compute_composite_score(
        immediate_pnl_bps=immediate_pnl_bps,
        latest_pnl_bps=latest_pnl,
        avg_pnl_bps=avg_pnl,
        max_drawdown_bps=max_dd,
        consecutive_losses=cons_losses,
        short_sharpe=short_s,
        mid_sharpe=mid_s,
    )

    result["reward_window_stats"] = {
        "short_sharpe_annualized": round(short_s, 4),
        "mid_sharpe_annualized": round(mid_s, 4),
        "cumulative_return_bps": (
            round(reward_window.current_cumulative_bps(), 1)
            if reward_window
            else 0.0
        ),
        "drawdown_bps": (
            round(reward_window.drawdown_bps(), 1) if reward_window else 0.0
        ),
        "short_samples": len(reward_window.short_returns_bps) if reward_window else 0,
        "mid_samples": len(reward_window.mid_returns_bps) if reward_window else 0,
    }

    return result