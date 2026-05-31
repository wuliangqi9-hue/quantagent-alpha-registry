from __future__ import annotations

from typing import Any

import pandas as pd

# Evidence from prior QuantAgent / Hummingbot-style experiments (workflow evidence, not profit proof).
STRATEGY_BENCHMARKS: dict[str, dict[str, float]] = {
    "supertrend": {
        "bull_sharpe": 1.12,
        "bear_sharpe": 0.41,
        "range_sharpe": 0.58,
        "win_rate": 0.54,
        "max_drawdown_pct": 18.2,
    },
    "bollinger": {
        "bull_sharpe": 0.62,
        "bear_sharpe": 0.48,
        "range_sharpe": 1.05,
        "win_rate": 0.57,
        "max_drawdown_pct": 12.4,
    },
    "macd_bollinger": {
        "bull_sharpe": 0.88,
        "bear_sharpe": 0.92,
        "range_sharpe": 0.71,
        "win_rate": 0.52,
        "max_drawdown_pct": 15.1,
    },
}


def _supertrend_signals(close: pd.Series, period: int = 10, multiplier: float = 3.0) -> pd.Series:
    hl2 = close
    atr = close.diff().abs().rolling(period, min_periods=period).mean()
    upper = hl2 + multiplier * atr
    lower = hl2 - multiplier * atr
    direction = pd.Series(0, index=close.index, dtype=float)
    for i in range(1, len(close)):
        if close.iloc[i] > upper.iloc[i - 1]:
            direction.iloc[i] = 1
        elif close.iloc[i] < lower.iloc[i - 1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i - 1]
    return direction


def _bollinger_signals(close: pd.Series, window: int = 20, num_std: float = 2.0) -> pd.Series:
    ma = close.rolling(window, min_periods=window).mean()
    std = close.rolling(window, min_periods=window).std()
    upper = ma + num_std * std
    lower = ma - num_std * std
    signals = pd.Series(0, index=close.index, dtype=float)
    signals[close < lower] = 1
    signals[close > upper] = -1
    return signals


def _macd_bollinger_signals(close: pd.Series) -> pd.Series:
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    bb = _bollinger_signals(close)
    out = pd.Series(0, index=close.index, dtype=float)
    out[(macd > signal) & (bb >= 0)] = 1
    out[(macd < signal) & (bb <= 0)] = -1
    return out


def build_benchmark_chart(
    ohlcv_df: pd.DataFrame,
    strategy_id: str,
    *,
    max_points: int = 120,
) -> dict[str, Any]:
    bench = STRATEGY_BENCHMARKS.get(strategy_id, STRATEGY_BENCHMARKS["bollinger"])
    empty_chart = {
        "prices": [],
        "markers": [],
        "evidence": bench,
        "caveats": [
            "Backtest sample is limited to the loaded window.",
            "Slippage and fees are not fully modeled in this demo chart.",
            "Past regime performance does not guarantee future results.",
        ],
    }
    if ohlcv_df.empty or "close" not in ohlcv_df.columns or len(ohlcv_df) < 5:
        return empty_chart

    df = ohlcv_df.copy()
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.sort_values("timestamp")
    close = pd.to_numeric(df["close"], errors="coerce").dropna()
    if close.empty or len(close) < 5:
        return empty_chart
    df = df.loc[close.index]
    if len(close) > max_points:
        close = close.iloc[-max_points:]
        df = df.iloc[-max_points:]

    generators = {
        "supertrend": _supertrend_signals,
        "bollinger": _bollinger_signals,
        "macd_bollinger": _macd_bollinger_signals,
    }
    gen = generators.get(strategy_id, _bollinger_signals)
    signals = gen(close).fillna(0).iloc[: len(close)]

    timestamps = (
        df["timestamp"].astype(str).tolist()
        if "timestamp" in df.columns
        else [str(i) for i in range(len(close))]
    )
    prices = [round(float(v), 4) for v in close.tolist()]
    markers = []
    prev = 0.0
    for i, sig in enumerate(signals):
        if i >= len(prices) or i >= len(timestamps):
            break
        if sig != 0 and sig != prev:
            markers.append(
                {
                    "timestamp": timestamps[i],
                    "price": prices[i],
                    "side": "buy" if sig > 0 else "sell",
                }
            )
        prev = sig

    return {
        "prices": [{"timestamp": timestamps[i], "close": prices[i]} for i in range(len(prices))],
        "markers": markers[-20:],
        "evidence": bench,
        "caveats": [
            "Backtest sample is limited to the loaded window.",
            "Slippage and fees are not fully modeled in this demo chart.",
            "Past regime performance does not guarantee future results.",
        ],
    }
