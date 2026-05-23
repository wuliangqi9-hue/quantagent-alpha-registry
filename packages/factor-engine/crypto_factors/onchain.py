from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_onchain_factors(df: pd.DataFrame, window: int = 720) -> pd.DataFrame:
    """
    Calculate on-chain factors from already prepared vendor/API metrics.

    This module deliberately does not reconstruct UTXO-level realized cap locally.
    Expected optional columns include:
    market_cap, realized_cap, sopr, transfer_volume, tx_count,
    active_addresses, fees, github_commits.
    """
    out = df.copy()

    if {"market_cap", "realized_cap"}.issubset(out.columns):
        safe_realized = out["realized_cap"].replace(0.0, np.nan)
        out["f_mvrv_ratio"] = out["market_cap"] / safe_realized
        market_cap_std = out["market_cap"].rolling(
            window=window, min_periods=max(2, window // 2)
        ).std()
        out["f_mvrv_zscore_original"] = (
            (out["market_cap"] - out["realized_cap"]) / (market_cap_std + 1e-8)
        )

    if {"open_interest", "realized_cap"}.issubset(out.columns):
        safe_realized = out["realized_cap"].replace(0.0, np.nan)
        out["f_realized_leverage"] = out["open_interest"] / safe_realized

    if "sopr" in out.columns:
        out["f_sopr_ma_7"] = out["sopr"].rolling(7, min_periods=4).mean()
        out["f_sopr_distance_to_1"] = out["sopr"] - 1.0

    if {"transfer_volume", "market_cap"}.issubset(out.columns):
        safe_market_cap = out["market_cap"].replace(0.0, np.nan)
        out["f_token_velocity_window"] = (
            out["transfer_volume"].rolling(window, min_periods=max(2, window // 2)).sum()
            / safe_market_cap
        )

    if "active_addresses" in out.columns:
        out["f_active_address_growth_7"] = out["active_addresses"].pct_change(7)
        out["f_active_address_growth_30"] = out["active_addresses"].pct_change(30)

    if "tx_count" in out.columns:
        out["f_tx_count_growth_7"] = out["tx_count"].pct_change(7)
        out["f_tx_count_growth_30"] = out["tx_count"].pct_change(30)

    if "fees" in out.columns:
        out["f_fee_pressure_7"] = out["fees"].rolling(7, min_periods=4).mean()

    if "github_commits" in out.columns:
        out["f_github_commit_growth_30"] = out["github_commits"].pct_change(30)

    return out
