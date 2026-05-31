from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "packages" / "strategy-selector"))

from strategy_selector.a2c_trainer import get_a2c_trainer  # noqa: E402
from strategy_selector.policy_blender import build_state_vector  # noqa: E402
from strategy_selector.finpos_rewards import compute_reward_for_a2c  # noqa: E402
from strategy_selector.finpos_rewards import RewardWindow as FinPosRewardWindow  # noqa: E402

logger = logging.getLogger(__name__)

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

    返回训练指标 dict，失败返回带 error 字段的诊断对象（不阻塞上游流程）。
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

        memory_context = payload.get("memory")
        if not isinstance(memory_context, dict):
            memory_context = None

        state_vector_dict = build_state_vector(
            factors=factor_snapshot_map,
            memory_context=memory_context,
            agent_reputation=agent.get("reputation") if isinstance(agent, dict) else None,
        )
        state_vector = list(state_vector_dict.values())

        reward_window = FinPosRewardWindow()
        for pnl in _historical_pnl_series(memory_context):
            reward_window.push(pnl)

        immediate_pnl_bps = _safe_float(
            getattr(finpos_rewards, "immediate_pnl_bps", None),
            _safe_float(payload.get("pnlBps"), 0.0),
        )
        a2c_reward = compute_reward_for_a2c(
            immediate_pnl_bps=immediate_pnl_bps,
            memory_context=memory_context,
            reward_window=reward_window,
        )
        reward = _safe_float(
            getattr(finpos_rewards, "composite_score", None),
            _safe_float(a2c_reward.get("composite_score"), 0.0),
        )

        trainer = get_a2c_trainer(checkpoint_dir=checkpoint_dir)
        action_idx = _selection_action_idx(payload.get("selection", {}))

        result = trainer.step(
            current_state=state_vector,
            current_action_idx=action_idx,
            reward=reward,
        )
        result["stateVector"] = state_vector_dict
        result["reward"] = reward
        result["finposReward"] = a2c_reward
        result["symbol"] = symbol.upper()
        return result
    except Exception as exc:
        logger.exception("A2C online training step failed")
        return {
            "schema": "quantagent.a2c-training-error.v1",
            "trained": False,
            "errorType": type(exc).__name__,
            "error": str(exc),
            "symbol": symbol.upper(),
        }


def _selection_action_idx(selection: dict[str, Any]) -> int:
    raw = selection.get("actionIdx")
    if raw is None:
        raw = selection.get("signalDirection") or selection.get("direction") or selection.get("action")
    if isinstance(raw, str):
        action_map: dict[str, int] = {
            "buy": 0,
            "long": 0,
            "sell": 1,
            "short": 1,
            "hold": 2,
            "flat": 2,
            "neutral": 2,
            "observe": 2,
        }
        return action_map.get(raw.lower(), 2)
    try:
        idx = int(raw)
    except (TypeError, ValueError):
        return 2
    return max(0, min(2, idx))


def _historical_pnl_series(memory_context: dict[str, Any] | None) -> list[float]:
    if not memory_context:
        return []
    series: list[float] = []
    for item in memory_context.get("retrieved", []):
        if not isinstance(item, dict):
            continue
        if item.get("pnlBps") is not None:
            series.append(_safe_float(item.get("pnlBps"), 0.0))
    return series[-60:]


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
