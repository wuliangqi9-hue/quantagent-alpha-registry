from __future__ import annotations

import hashlib
import json
from typing import Any


def _direction_sign(direction: str) -> int:
    if direction == "long":
        return 1
    if direction == "short":
        return -1
    return 0


def _performance_summary(previous_records: list[Any], current_pnl_bps: float) -> dict[str, Any]:
    """FinPos 多时间尺度奖励：把单笔 PnL 放入滚动/累计/回撤轨迹。"""
    prior_pnls = [float(getattr(record, "pnl_bps", 0.0)) for record in previous_records]
    series = [*prior_pnls, current_pnl_bps]
    rolling_window = series[-5:]
    rolling_pnl = sum(rolling_window)
    cumulative = sum(series)
    wins = sum(1 for item in series if item > 0)

    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for pnl in series:
        equity += pnl
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, equity - peak)

    consecutive_losses = 0
    for pnl in reversed(series):
        if pnl < 0:
            consecutive_losses += 1
        else:
            break

    return {
        "rewardSchema": "quantagent.multi-timescale-reward.v1",
        "tradeCount": len(series),
        "rollingWindow": len(rolling_window),
        "rollingPnlBps": round(rolling_pnl, 2),
        "cumulativePnlBps": round(cumulative, 2),
        "winRate": round(wins / len(series), 4) if series else 0.0,
        "maxDrawdownBps": round(max_drawdown, 2),
        "consecutiveLosses": consecutive_losses,
    }


def settle_last_signal(
    analysis: dict[str, Any],
    exit_price: float | None = None,
    previous_records: list[Any] | None = None,
) -> dict[str, Any]:
    prices = analysis.get("selection", {}).get("benchmarkChart", {}).get("prices", [])
    if len(prices) < 2:
        raise ValueError("Not enough price points to settle the signal.")

    entry = float(prices[-2]["close"])
    exit_ = float(exit_price if exit_price is not None else prices[-1]["close"])
    direction = analysis.get("selection", {}).get("signalDirection", "neutral")
    sign = _direction_sign(direction)
    raw_return = 0.0 if sign == 0 else ((exit_ - entry) / entry) * sign
    pnl_bps = round(raw_return * 10000, 2)
    confidence = float(analysis.get("selection", {}).get("confidence", 0.0) or 0.0)

    score = int(max(-10000, min(10000, round(pnl_bps * confidence))))
    performance = _performance_summary(previous_records or [], pnl_bps)
    payload = {
        "schema": "quantagent.reputation-settlement.v1",
        "signalHash": analysis.get("signalHash"),
        "symbol": analysis.get("symbol"),
        "direction": direction,
        "entryPrice": entry,
        "exitPrice": exit_,
        "pnlBps": pnl_bps,
        "confidence": confidence,
        "score": score,
        **performance,
        "source": "benchmark-window-settlement",
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    payload["settlementHash"] = f"0x{digest}"
    return payload
