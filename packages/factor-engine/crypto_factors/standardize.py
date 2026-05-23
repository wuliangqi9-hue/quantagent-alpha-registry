from __future__ import annotations

import numpy as np
import pandas as pd


def winsorize_series(series: pd.Series, lower: float = -3.0, upper: float = 3.0) -> pd.Series:
    """Clip a factor series to reduce crypto fat-tail distortion."""
    return series.clip(lower=lower, upper=upper)


def rolling_mad_zscore(
    series: pd.Series,
    window: int,
    min_periods: int,
    eps: float = 1e-8,
) -> pd.Series:
    """
    Robust rolling z-score using median absolute deviation.

    1.4826 scales MAD to be comparable with standard deviation under a normal
    distribution.
    """
    rolling_median = series.rolling(window=window, min_periods=min_periods).median()
    abs_dev = (series - rolling_median).abs()
    rolling_mad = abs_dev.rolling(window=window, min_periods=min_periods).median()
    robust_std = 1.4826 * rolling_mad
    return (series - rolling_median) / (robust_std + eps)


def shift_and_standardize_factors(
    df: pd.DataFrame,
    z_window: int = 720,
    min_periods: int | None = None,
    drop_raw: bool = True,
    factor_prefix: str = "f_",
    method: str = "zscore",
    winsorize: bool = True,
    clip_lower: float = -3.0,
    clip_upper: float = 3.0,
) -> pd.DataFrame:
    """
    Shift all factor columns by one row and create rolling z-score features.

    The shift prevents using a factor value formed at the current bar to trade
    on that same bar.
    """
    out = df.copy()
    factor_cols = [col for col in out.columns if col.startswith(factor_prefix)]
    if min_periods is None:
        min_periods = max(2, z_window // 2)

    for col in factor_cols:
        shifted = out[col].replace([np.inf, -np.inf], np.nan).shift(1)
        if method == "mad":
            standardized = rolling_mad_zscore(shifted, window=z_window, min_periods=min_periods)
            suffix = "mad_zscore_safe"
        elif method == "zscore":
            rolling_mean = shifted.rolling(window=z_window, min_periods=min_periods).mean()
            rolling_std = shifted.rolling(window=z_window, min_periods=min_periods).std()
            standardized = (shifted - rolling_mean) / (rolling_std + 1e-8)
            suffix = "zscore_safe"
        else:
            raise ValueError("method must be 'zscore' or 'mad'")

        if winsorize:
            standardized = winsorize_series(standardized, lower=clip_lower, upper=clip_upper)
        out[f"{col}_{suffix}"] = standardized

    if drop_raw and factor_cols:
        out = out.drop(columns=factor_cols)

    return out


def add_forward_returns(
    df: pd.DataFrame,
    horizons: tuple[int, ...] = (1, 24, 168),
    price_col: str = "close",
    benchmark_return_cols: dict[int, str] | None = None,
    volatility_window: int | None = None,
) -> pd.DataFrame:
    out = df.copy()
    for horizon in horizons:
        target_col = f"target_return_{horizon}"
        out[target_col] = out[price_col].shift(-horizon) / out[price_col] - 1.0
        if benchmark_return_cols and horizon in benchmark_return_cols:
            bench_col = benchmark_return_cols[horizon]
            if bench_col in out.columns:
                out[f"target_excess_return_{horizon}"] = out[target_col] - out[bench_col]
        if volatility_window:
            realized_vol = out[price_col].pct_change().rolling(
                volatility_window,
                min_periods=max(2, volatility_window // 2),
            ).std()
            out[f"target_vol_adj_return_{horizon}"] = out[target_col] / (realized_vol + 1e-8)
    return out


def cross_sectional_standardize(
    panel: pd.DataFrame,
    factor_cols: list[str] | None = None,
    time_col: str = "timestamp",
    method: str = "rank",
    clip_lower: float = -3.0,
    clip_upper: float = 3.0,
) -> pd.DataFrame:
    """
    Add cross-sectional factor features for [timestamp, symbol, factor] panels.

    method='rank' maps same-timestamp ranks to roughly [-1, 1].
    method='zscore' subtracts same-timestamp mean and divides by std.
    """
    out = panel.copy()
    if factor_cols is None:
        factor_cols = [
            col for col in out.columns
            if col.startswith("f_") and (col.endswith("_zscore_safe") or col.endswith("_mad_zscore_safe"))
        ]
    if not factor_cols:
        return out

    grouped = out.groupby(time_col, group_keys=False)
    for col in factor_cols:
        if method == "rank":
            ranks = grouped[col].rank(pct=True)
            out[f"{col}_cs_rank"] = (ranks - 0.5) * 2.0
        elif method == "zscore":
            mean = grouped[col].transform("mean")
            std = grouped[col].transform("std")
            out[f"{col}_cs_zscore"] = ((out[col] - mean) / (std + 1e-8)).clip(
                lower=clip_lower,
                upper=clip_upper,
            )
        else:
            raise ValueError("method must be 'rank' or 'zscore'")
    return out


def clean_factor_matrix(df: pd.DataFrame) -> pd.DataFrame:
    out = df.replace([np.inf, -np.inf], np.nan)
    return out.dropna()


def factor_quality_report(df: pd.DataFrame) -> pd.DataFrame:
    factor_cols = [
        col for col in df.columns
        if col.endswith("_zscore_safe") or col.endswith("_mad_zscore_safe")
    ]
    rows = []
    for col in factor_cols:
        series = df[col]
        rows.append(
            {
                "factor": col,
                "missing_ratio": float(series.isna().mean()),
                "finite_ratio": float(np.isfinite(series.dropna()).mean()) if series.notna().any() else 0.0,
                "mean": float(series.mean()) if series.notna().any() else np.nan,
                "std": float(series.std()) if series.notna().any() else np.nan,
                "min": float(series.min()) if series.notna().any() else np.nan,
                "max": float(series.max()) if series.notna().any() else np.nan,
                "zero_ratio": float((series == 0).mean()),
            }
        )
    return pd.DataFrame(rows)
