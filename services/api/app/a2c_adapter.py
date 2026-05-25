from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "packages" / "strategy-selector"))

from strategy_selector.a2c_trainer import get_a2c_trainer  # noqa: E402
from strategy_selector.policy_blender import build_state_vector  # noqa: E402
from strategy_selector.finpos_rewards import compute_reward_for_a2c  # noqa: E402
from strategy_selector.finpos_rewards import RewardWindow as FinPosRewardWindow  # noqa: E402

__all__ = [
    "FinPosRewardWindow",
    "build_state_vector",
    "compute_reward_for_a2c",
    "get_a2c_trainer",
    "run_a2c_training_step",
]


# ---------------------------------------------------------------------------
# 便捷封装：从 FinPos 奖励 → A2C 训练一步完成
# ---------------------------------------------------------------------------
def run_a2c_training_step(
    *,
    symbol: str,
    payload: dict[str, Any],
    agent: dict[str, Any],
    finpos_rewards: Any,  # FinPosCompositeReward
    checkpoint_dir: str = "data",
) -> dict[str, Any] | None:
    """从 settlement payload 提取状态并执行一次 A2C 训练步骤。

    返回训练指标 dict，失败返回 None（不阻塞上游流程）。
    """
    try:
        factor_snapshot_raw = (payload.get("factorSummary") or {}).get("factors", [])
        factor_snapshot_map: dict[str, float] = {}
        for item in factor_snapshot_raw:
            if isinstance(item, dict) and item.get("id") and item.get("score") is not None:
                try:
                    factor_snapshot_map[str(item["id"])] = float(item["score"])
                except (TypeError, ValueError):
                    pass

        state_vector = build_state_vector(
            symbol=symbol,
            factors=factor_snapshot_map,
            regime=(payload.get("regime") or {}).get("regime", "normal"),
            volatility=float((payload.get("regime") or {}).get("volatilityMultiplier", 1.0)),
            current_exposure_pct=float((agent.get("wallet") or {}).get("exposurePct", 0.0)),
            spread_bps=float((agent.get("wallet") or {}).get("spreadBps", 1.5)),
        )

        reward_window = FinPosRewardWindow(
            immediate_pnl_bps=float(getattr(finpos_rewards, "immediate_pnl_bps", 0.0)),
            cumulative_pnl_bps=float(getattr(finpos_rewards, "cumulative_pnl_bps", 0.0)),
            direction_correct=bool(getattr(finpos_rewards, "direction_correct", False)),
            exposure_util=float(getattr(finpos_rewards, "exposure_util", 0.5)),
            volatility_regime=float(getattr(finpos_rewards, "volatility_regime", 1.0)),
        )
        a2c_reward = compute_reward_for_a2c(
            window=reward_window,
            composite_score=float(getattr(finpos_rewards, "composite_score", 0.0)),
        )

        trainer = get_a2c_trainer(checkpoint_dir=checkpoint_dir)
        action_idx = payload.get("selection", {}).get("actionIdx", 0)
        if isinstance(action_idx, str):
            action_map: dict[str, int] = {"buy": 0, "sell": 1, "hold": 2, "long": 0, "short": 1}
            action_idx = action_map.get(action_idx.lower(), 2)
        action_idx = int(action_idx)

        return trainer.step(
            state_vector=state_vector,
            action_idx=action_idx,
            reward=a2c_reward,
        )
    except Exception:
        return None