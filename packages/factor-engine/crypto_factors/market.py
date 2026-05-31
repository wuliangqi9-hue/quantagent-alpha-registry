from __future__ import annotations

import numpy as np
import pandas as pd


def _rsi(close: pd.Series, length: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, min_periods=span, adjust=False).mean()


def _macd_hist(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
    macd_line = _ema(close, fast) - _ema(close, slow)
    signal_line = _ema(macd_line, signal)
    return macd_line - signal_line


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.rolling(length, min_periods=length).mean()


def calculate_market_factors(df: pd.DataFrame, window: int = 720) -> pd.DataFrame:
    """
    Calculate OHLCV-based crypto factor proxies.

    Required columns: open, high, low, close, volume.
    Optional columns: circulating_supply.
    """
    required = {"open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required OHLCV columns: {sorted(missing)}")

    out = df.copy()
    safe_close = out["close"].replace(0.0, np.nan)
    safe_low = out["low"].replace(0.0, np.nan)
    safe_volume = out["volume"].replace(0.0, np.nan)
    amount = (safe_close * safe_volume).replace(0.0, np.nan)
    returns = out["close"].pct_change()

    if "circulating_supply" in out.columns:
        out["f_size"] = np.log1p(safe_close * out["circulating_supply"])
    else:
        out["f_size_proxy"] = np.log1p(amount)

    out["f_momentum_return_24h"] = out["close"].pct_change(24)
    out["f_momentum_return_window"] = out["close"].pct_change(window)
    out["f_momentum_macd_hist"] = _macd_hist(out["close"])
    out["f_momentum_rsi_14"] = _rsi(out["close"], length=14)

    out["f_illiquidity_amihud"] = returns.abs() / amount
    out["f_liquidity_amount_ma"] = amount.rolling(window, min_periods=max(2, window // 2)).mean()

    atr = _atr(out["high"], out["low"], out["close"], length=14)
    out["f_volatility_natr_14"] = atr / safe_close
    out["f_volatility_return_std_window"] = returns.rolling(
        window, min_periods=max(2, window // 2)
    ).std()

    ma20 = out["close"].rolling(20, min_periods=20).mean()
    out["f_trend_close_ma20_gap"] = out["close"] / ma20 - 1.0
    low_24h = safe_low.rolling(24, min_periods=12).min().replace(0.0, np.nan)
    out["f_range_high_low_24h"] = (
        out["high"].rolling(24, min_periods=12).max()
        / low_24h
        - 1.0
    )

    return out.replace([np.inf, -np.inf], np.nan)
