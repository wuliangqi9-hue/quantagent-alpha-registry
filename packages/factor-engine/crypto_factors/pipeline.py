from __future__ import annotations

import pandas as pd

from .derivatives import calculate_derivative_factors
from .mantle_native import calculate_mantle_native_factors
from .market import calculate_market_factors
from .onchain import calculate_onchain_factors
from .standardize import add_forward_returns, clean_factor_matrix, shift_and_standardize_factors


def normalize_timestamp_index(df: pd.DataFrame, timestamp_col: str = "timestamp") -> pd.DataFrame:
    """Sort data and normalize timestamps to UTC to avoid timezone ghosting."""
    out = df.copy()
    if timestamp_col in out.columns:
        out[timestamp_col] = pd.to_datetime(out[timestamp_col], utc=True)
        out = out.sort_values(timestamp_col).set_index(timestamp_col)
    else:
        out.index = pd.to_datetime(out.index, utc=True)
        out = out.sort_index()
    if out.index.has_duplicates:
        raise ValueError("Duplicate timestamps detected after UTC normalization")
    return out


def forward_fill_optional_metrics(
    df: pd.DataFrame,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """
    Forward-fill low-frequency external metrics after merge.

    Do not use interpolation or backward fill for on-chain/daily metrics because
    that would leak future values into earlier intraday bars.
    """
    out = df.copy()
    if columns is None:
        columns = [
            col for col in [
                "market_cap",
                "realized_cap",
                "sopr",
                "transfer_volume",
                "tx_count",
                "active_addresses",
                "fees",
                "github_commits",
                "funding_rate",
                "open_interest",
                "long_short_ratio",
                "taker_buy_volume",
                "taker_sell_volume",
            ]
            if col in out.columns
        ]
    if columns:
        out[columns] = out[columns].ffill()
    return out


def build_crypto_factor_matrix(
    df: pd.DataFrame,
    market_window: int = 720,
    derivative_window: int = 720,
    onchain_window: int = 365,
    z_window: int = 720,
    target_horizons: tuple[int, ...] = (1, 24, 168),
    drop_raw_factors: bool = True,
    dropna: bool = True,
    standardize_method: str = "zscore",
    winsorize: bool = True,
    clip_lower: float = -3.0,
    clip_upper: float = 3.0,
    ffill_external_metrics: bool = True,
    target_volatility_window: int | None = None,
) -> pd.DataFrame:
    """
    Build a safe crypto factor matrix from OHLCV plus optional extra metrics.

    Use smaller window values for hourly data and larger daily windows for
    low-frequency on-chain data.
    """
    out = normalize_timestamp_index(df)
    if ffill_external_metrics:
        out = forward_fill_optional_metrics(out)

    out = calculate_market_factors(out, window=market_window)
    out = calculate_derivative_factors(out, window=derivative_window)
    out = calculate_onchain_factors(out, window=onchain_window)
    out = calculate_mantle_native_factors(out, window=max(1, onchain_window // 15))
    out = shift_and_standardize_factors(
        out,
        z_window=z_window,
        drop_raw=drop_raw_factors,
        method=standardize_method,
        winsorize=winsorize,
        clip_lower=clip_lower,
        clip_upper=clip_upper,
    )
    out = add_forward_returns(
        out,
        horizons=target_horizons,
        volatility_window=target_volatility_window,
    )

    if dropna:
        out = clean_factor_matrix(out)

    return out
