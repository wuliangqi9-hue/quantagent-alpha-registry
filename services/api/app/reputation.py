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


def settle_last_signal(analysis: dict[str, Any], exit_price: float | None = None) -> dict[str, Any]:
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
        "source": "benchmark-window-settlement",
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    payload["settlementHash"] = f"0x{digest}"
    return payload
