from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Mantle-native factor constants ───────────────────────────────────
# These factors are specific to the Mantle L2 ecosystem and demonstrate
# deep integration with the Mantle network for the Turing Test hackathon.

MANTLE_DEFAULT_RPC = "https://rpc.sepolia.mantle.xyz"
DEFILLAMA_PROTOCOLS_API = "https://api.llama.fi/protocols"
DEFILLAMA_MANTLE_CHAIN_API = "https://api.llama.fi/v2/historicalChainTvl/Mantle"
MNT_TOKEN_ADDRESS = "0xDeadDeAddeAddEAddeadDEaDDEAdDeaDDeAD0000"


def calculate_mantle_native_factors(
    df: pd.DataFrame,
    window: int = 24,
) -> pd.DataFrame:
    """
    Calculate Mantle-native ecosystem factors from on-chain data.

    Expected optional columns include:
    - dex_liquidity_mnt_usd: Total MNT-USD liquidity on Mantle DEXes
    - dex_volume_24h: 24-hour DEX trading volume in USD
    - mnt_staking_yield_pct: Annualized MNT staking yield percentage
    - l2_sequencer_revenue_mnt: L2 sequencer revenue in MNT
    - l2_tx_count: L2 transaction count
    - mantle_tvl_usd: Total Value Locked in Mantle ecosystem
    - mnt_price_usd: MNT token price in USD
    """
    out = df.copy()

    # ── DEX Liquidity Depth Factor ─────────────────────────────────
    # Measures the ratio of DEX liquidity to total TVL => ecosystem health
    if {"dex_liquidity_mnt_usd", "mantle_tvl_usd"}.issubset(out.columns):
        safe_tvl = out["mantle_tvl_usd"].replace(0.0, np.nan)
        out["f_mantle_dex_liquidity_ratio"] = out["dex_liquidity_mnt_usd"] / safe_tvl
        # Rolling Z-score of liquidity depth
        _rolling_zscore(out, "dex_liquidity_mnt_usd", window, "f_mantle_dex_depth_zscore")

    # ── DEX Volume / TVL (Velocity) Factor ──────────────────────────
    if {"dex_volume_24h", "mantle_tvl_usd"}.issubset(out.columns):
        safe_tvl = out["mantle_tvl_usd"].replace(0.0, np.nan)
        out["f_mantle_dex_velocity"] = out["dex_volume_24h"] / safe_tvl
        # Volume momentum: 7-period change
        out["f_mantle_dex_vol_momentum_7"] = out["dex_volume_24h"].pct_change(7)

    # ── TVL Growth Rate Factor ──────────────────────────────────────
    if "mantle_tvl_usd" in out.columns:
        out["f_mantle_tvl_growth_7"] = out["mantle_tvl_usd"].pct_change(7)
        out["f_mantle_tvl_growth_30"] = out["mantle_tvl_usd"].pct_change(30)

    # ── MNT Staking Yield Factor ────────────────────────────────────
    if "mnt_staking_yield_pct" in out.columns:
        out["f_mantle_staking_yield"] = out["mnt_staking_yield_pct"]
        out["f_mantle_staking_yield_change_7"] = out["mnt_staking_yield_pct"].diff(7)

    # ── L2 Sequencer Revenue Factor ─────────────────────────────────
    if "l2_sequencer_revenue_mnt" in out.columns:
        out["f_mantle_sequencer_revenue"] = out["l2_sequencer_revenue_mnt"]
        out["f_mantle_sequencer_revenue_ma_7"] = (
            out["l2_sequencer_revenue_mnt"].rolling(7, min_periods=4).mean()
        )
        out["f_mantle_sequencer_revenue_growth_7"] = (
            out["l2_sequencer_revenue_mnt"].pct_change(7)
        )

    # ── L2 Network Activity Factor ──────────────────────────────────
    if "l2_tx_count" in out.columns:
        out["f_mantle_tx_count_growth_7"] = out["l2_tx_count"].pct_change(7)
        out["f_mantle_tx_count_growth_30"] = out["l2_tx_count"].pct_change(30)
        # Transactions per TVL dollar (ecosystem efficiency)
        if "mantle_tvl_usd" in out.columns:
            safe_tvl = out["mantle_tvl_usd"].replace(0.0, np.nan)
            out["f_mantle_tx_per_tvl"] = out["l2_tx_count"] / safe_tvl

    return out


def _rolling_zscore(
    df: pd.DataFrame,
    col: str,
    window: int,
    output_col: str,
) -> None:
    """Compute rolling Z-score and store in-place."""
    if col not in df.columns:
        return
    roll = df[col].rolling(window, min_periods=max(4, window // 4))
    mean = roll.mean()
    std = roll.std()
    df[output_col] = (df[col] - mean) / (std + 1e-8)


# ── Async data fetcher for live Mantle metrics ──────────────────────

async def fetch_mantle_metrics(
    rpc_url: str | None = None,
    *,
    timeout: float = 15.0,
) -> dict[str, Any]:
    """Fetch live Mantle metrics using public RPC and DeFiLlama HTTP APIs."""
    rpc = rpc_url or MANTLE_DEFAULT_RPC
    metrics: dict[str, Any] = {
        "mantle_tvl_usd": None,
        "dex_liquidity_mnt_usd": None,
        "dex_volume_24h": None,
        "mnt_staking_yield_pct": None,
        "l2_sequencer_revenue_mnt": None,
        "l2_tx_count": None,
        "mnt_price_usd": None,
        "l2_gas_price_wei": None,
        "l2_latest_block": None,
        "_fetch_timestamp_utc": pd.Timestamp.utcnow().isoformat(),
        "_status": "live",
        "_sources": [],
        "_errors": [],
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            gas_resp, block_resp = await asyncio.gather(
                client.post(
                    rpc,
                    json={"jsonrpc": "2.0", "id": 1, "method": "eth_gasPrice", "params": []},
                ),
                client.post(
                    rpc,
                    json={"jsonrpc": "2.0", "id": 2, "method": "eth_blockNumber", "params": []},
                ),
            )
            gas_resp.raise_for_status()
            block_resp.raise_for_status()
            gas_body = gas_resp.json()
            block_body = block_resp.json()
            if gas_body.get("result"):
                metrics["l2_gas_price_wei"] = int(gas_body["result"], 16)
            if block_body.get("result"):
                metrics["l2_latest_block"] = int(block_body["result"], 16)
            metrics["_sources"].append({"provider": "mantle-rpc", "url": rpc})
        except Exception as exc:
            metrics["_errors"].append({"provider": "mantle-rpc", "message": str(exc)})

        try:
            chain_resp = await client.get(DEFILLAMA_MANTLE_CHAIN_API)
            chain_resp.raise_for_status()
            chain_rows = chain_resp.json()
            if isinstance(chain_rows, list) and chain_rows:
                latest = chain_rows[-1]
                metrics["mantle_tvl_usd"] = float(latest.get("tvl") or 0.0)
                if len(chain_rows) >= 2:
                    previous = float(chain_rows[-2].get("tvl") or 0.0)
                    metrics["mantle_tvl_change_1d_pct"] = (
                        (metrics["mantle_tvl_usd"] - previous) / previous if previous else None
                    )
            metrics["_sources"].append({"provider": "defillama", "url": DEFILLAMA_MANTLE_CHAIN_API})
        except Exception as exc:
            metrics["_errors"].append({"provider": "defillama-chain", "message": str(exc)})

        try:
            protocols_resp = await client.get(DEFILLAMA_PROTOCOLS_API)
            protocols_resp.raise_for_status()
            protocols = protocols_resp.json()
            dex_names = {"merchant moe", "agni finance"}
            mantle_dex_tvl = 0.0
            mantle_dex_volume = 0.0
            matched: list[str] = []
            for item in protocols if isinstance(protocols, list) else []:
                name = str(item.get("name", "")).lower()
                chains = [str(chain).lower() for chain in item.get("chains", [])]
                if name in dex_names and "mantle" in chains:
                    matched.append(str(item.get("name")))
                    mantle_dex_tvl += float(item.get("tvl") or 0.0)
                    mantle_dex_volume += float(item.get("volume24h") or item.get("change_1d") or 0.0)
            metrics["dex_liquidity_mnt_usd"] = mantle_dex_tvl or None
            metrics["dex_volume_24h"] = mantle_dex_volume or None
            metrics["_sources"].append(
                {
                    "provider": "defillama-protocols",
                    "url": DEFILLAMA_PROTOCOLS_API,
                    "protocols": matched,
                }
            )
        except Exception as exc:
            metrics["_errors"].append({"provider": "defillama-protocols", "message": str(exc)})

    if metrics["_errors"] and not metrics["_sources"]:
        metrics["_status"] = "unavailable"
    elif metrics["_errors"]:
        metrics["_status"] = "partial-live"
    return metrics
