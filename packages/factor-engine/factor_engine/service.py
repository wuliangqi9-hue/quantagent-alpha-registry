from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from crypto_factors.pipeline import build_crypto_factor_matrix, normalize_timestamp_index

MODEL_VERSION = "factor-engine-1.0.0"

# Demo-friendly windows (hourly bars; ~500+ rows after dropna)
DEMO_WINDOWS = {
    "market_window": 168,
    "derivative_window": 168,
    "onchain_window": 90,
    "z_window": 168,
}

MVP_FACTOR_LABELS = {
    "momentum": "f_momentum_return_24h_zscore_safe",
    "volatility": "f_volatility_return_std_window_zscore_safe",
    "trend": "f_trend_close_ma20_gap_zscore_safe",
    "volume": "f_liquidity_amount_ma_zscore_safe",
    "funding": "f_funding_rate_zscore_safe",
    "open_interest": "f_oi_momentum_24h_zscore_safe",
}


def _latest_safe_value(matrix: pd.DataFrame, column: str) -> float | None:
    if column not in matrix.columns:
        return None
    series = matrix[column].dropna()
    if series.empty:
        return None
    value = float(series.iloc[-1])
    if not np.isfinite(value):
        return None
    return round(value, 4)


def compute_factor_summary(
    ohlcv_df: pd.DataFrame,
    *,
    use_demo_windows: bool = True,
) -> dict[str, Any]:
    """Build factor matrix and return chart-ready MVP summary."""
    windows = DEMO_WINDOWS if use_demo_windows else {}
    matrix = build_crypto_factor_matrix(
        ohlcv_df,
        market_window=windows.get("market_window", 720),
        derivative_window=windows.get("derivative_window", 720),
        onchain_window=windows.get("onchain_window", 365),
        z_window=windows.get("z_window", 720),
        dropna=True,
    )
    if matrix.empty:
        raise ValueError("Factor matrix is empty after processing")

    latest_row = matrix.iloc[-1]
    factors: list[dict[str, Any]] = []
    explanations = {
        "momentum": "Positive momentum supports trend-following; extremes may signal reversal risk.",
        "volatility": "Higher volatility reduces confidence and increases slippage risk.",
        "trend": "Strong trend gap favors SuperTrend-style strategies; weak gap favors mean reversion.",
        "volume": "Volume-backed moves are treated as more credible than thin moves.",
        "funding": "Extreme funding can indicate crowded positioning and squeeze risk.",
        "open_interest": "Rising OI during sharp moves can increase liquidation fragility.",
    }

    for key, col in MVP_FACTOR_LABELS.items():
        score = _latest_safe_value(matrix, col)
        factors.append(
            {
                "id": key,
                "label": key.replace("_", " ").title(),
                "column": col,
                "score": score,
                "missing": score is None,
                "explanation": explanations[key],
            }
        )

    close = normalize_timestamp_index(ohlcv_df)["close"]
    returns = close.pct_change().dropna()
    vol = float(returns.tail(24).std()) if len(returns) >= 24 else float(returns.std() or 0.0)

    return {
        "modelVersion": MODEL_VERSION,
        "factors": factors,
        "latestTimestamp": str(matrix.index[-1]),
        "rowCount": int(len(matrix)),
        "recentVolatility24h": round(vol, 6),
        "rawFactorColumns": [
            c for c in matrix.columns if c.endswith("_zscore_safe") or c.endswith("_mad_zscore_safe")
        ],
    }
