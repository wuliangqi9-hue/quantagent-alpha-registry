from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_derivative_factors(df: pd.DataFrame, window: int = 720) -> pd.DataFrame:
    """
    Calculate derivative-market factors when the required columns exist.

    Optional columns:
    funding_rate, open_interest, spot_price, perp_price,
    iv_put_atm, iv_call_atm, long_short_ratio,
    taker_buy_volume, taker_sell_volume.
    """
    out = df.copy()

    if "funding_rate" in out.columns:
        out["f_funding_rate"] = out["funding_rate"]
        rolling_mean = out["funding_rate"].rolling(window, min_periods=max(2, window // 2)).mean()
        rolling_std = out["funding_rate"].rolling(window, min_periods=max(2, window // 2)).std()
        out["f_funding_rate_local_z"] = (
            (out["funding_rate"] - rolling_mean) / (rolling_std + 1e-8)
        )

    if "open_interest" in out.columns:
        out["f_oi_momentum_24h"] = out["open_interest"].pct_change(24)
        out["f_oi_momentum_window"] = out["open_interest"].pct_change(window)

    if {"spot_price", "perp_price"}.issubset(out.columns):
        safe_spot = out["spot_price"].replace(0.0, np.nan)
        out["f_basis"] = (out["perp_price"] - out["spot_price"]) / safe_spot

    if {"iv_put_atm", "iv_call_atm"}.issubset(out.columns):
        out["f_iv_skew"] = out["iv_put_atm"] - out["iv_call_atm"]

    if "long_short_ratio" in out.columns:
        out["f_long_short_ratio"] = out["long_short_ratio"]

    if {"taker_buy_volume", "taker_sell_volume"}.issubset(out.columns):
        safe_sell = out["taker_sell_volume"].replace(0.0, np.nan)
        out["f_taker_buy_sell_ratio"] = out["taker_buy_volume"] / safe_sell

    return out
