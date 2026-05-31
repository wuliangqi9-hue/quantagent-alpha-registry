from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from .config import EFFECTIVE_MANTLE_RPC_URL, MANTLE_CHAIN_ID

logger = logging.getLogger(__name__)

# ── gas estimator constants ──────────────────────────────────────────
# Mantle network uses MNT tokens for gas with a relatively stable base fee.
# These defaults are conservative for Mantle and can be overridden
# via environment variables.
DEFAULT_GAS_MULTIPLIER = 1.2  # 20% buffer for execution safety


@dataclass
class GasEstimate:
    """Dynamic gas cost estimate for a transaction on Mantle."""

    gas_price_gwei: float
    gas_limit: int
    estimated_cost_mnt: float
    estimated_cost_usd: float
    base_fee_gwei: float
    max_priority_fee_gwei: float

    @property
    def total_gas_wei(self) -> int:
        return int(self.gas_price_gwei * 1e9 * self.gas_limit)

    @property
    def formatted(self) -> str:
        return (
            f"Gas: {self.gas_limit:,} × {self.gas_price_gwei:.2f} Gwei "
            f"(≈ {self.estimated_cost_mnt:.6f} MNT / ${self.estimated_cost_usd:.4f})"
        )


MNT_USD_PRICE_CACHE: float = 0.80  # reasonable fallback; updated via fetch_mnt_price()


async def fetch_mnt_price() -> float:
    """Fetch current MNT/USD price from a public oracle."""
    global MNT_USD_PRICE_CACHE
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Use a CoinGecko-compatible endpoint for MNT token price
            resp = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "mantle", "vs_currencies": "usd"},
            )
            if resp.status_code == 200:
                data = resp.json()
                price = data.get("mantle", {}).get("usd", 0)
                if price > 0:
                    MNT_USD_PRICE_CACHE = float(price)
                    logger.info("MNT/USD price updated: $%.4f", MNT_USD_PRICE_CACHE)
                    return MNT_USD_PRICE_CACHE
    except Exception as exc:
        logger.warning("Failed to fetch MNT price, using cache $%.4f: %s", MNT_USD_PRICE_CACHE, exc)
    return MNT_USD_PRICE_CACHE


async def estimate_gas_cost(
    *,
    gas_limit: int = 300_000,
    mnt_usd_price: Optional[float] = None,
    multiplier: float = DEFAULT_GAS_MULTIPLIER,
) -> GasEstimate:
    """
    Query the Mantle RPC for current gas fee data and return a dynamic estimate.

    Uses eth_maxPriorityFeePerGas + latest block baseFeePerGas (EIP-1559 style).
    Falls back to eth_gasPrice for networks without EIP-1559 support.
    """
    if mnt_usd_price is None:
        mnt_usd_price = await fetch_mnt_price()

    base_fee = 0.02  # Gwei — safe Mantle fallback
    priority_fee = 1.0  # Gwei
    gas_price = 1.0  # Gwei — fallback for legacy mode

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1) Try eth_maxPriorityFeePerGas (EIP-1559)
            priority_resp = await client.post(
                EFFECTIVE_MANTLE_RPC_URL,
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_maxPriorityFeePerGas",
                    "params": [],
                    "id": 1,
                },
            )
            if priority_resp.status_code == 200:
                prio_data = priority_resp.json()
                if prio_data.get("result"):
                    priority_fee = max(priority_fee, int(prio_data["result"], 16) / 1e9)

            # 2) Get latest block for baseFeePerGas
            block_resp = await client.post(
                EFFECTIVE_MANTLE_RPC_URL,
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_getBlockByNumber",
                    "params": ["latest", False],
                    "id": 2,
                },
            )
            if block_resp.status_code == 200:
                block_data = block_resp.json()
                if block_data.get("result") and block_data["result"].get("baseFeePerGas"):
                    base_fee = max(base_fee, int(block_data["result"]["baseFeePerGas"], 16) / 1e9)

            gas_price = base_fee + priority_fee

    except Exception as exc:
        logger.warning("Gas estimation via RPC failed, using defaults: %s", exc)
        # fall through to defaults

    # Apply safety multiplier
    gas_price = max(gas_price, 0.02) * multiplier

    # Cost calculations
    cost_mnt = (gas_price * 1e9 * gas_limit) / 1e18
    cost_usd = cost_mnt * mnt_usd_price

    return GasEstimate(
        gas_price_gwei=round(gas_price, 4),
        gas_limit=gas_limit,
        estimated_cost_mnt=round(cost_mnt, 6),
        estimated_cost_usd=round(cost_usd, 4),
        base_fee_gwei=round(base_fee, 4),
        max_priority_fee_gwei=round(priority_fee, 4),
    )


async def get_gas_display() -> dict:
    """Return a human-readable gas summary for UI display."""
    estimate = await estimate_gas_cost()
    return {
        "network": f"Mantle {'Sepolia' if MANTLE_CHAIN_ID == 5003 else 'Mainnet'} (chain {MANTLE_CHAIN_ID})",
        "gas_price_gwei": estimate.gas_price_gwei,
        "base_fee_gwei": estimate.base_fee_gwei,
        "max_priority_fee_gwei": estimate.max_priority_fee_gwei,
        "gas_limit": estimate.gas_limit,
        "estimated_cost_mnt": estimate.estimated_cost_mnt,
        "estimated_cost_usd": estimate.estimated_cost_usd,
        "formatted": estimate.formatted,
        "multiplier": DEFAULT_GAS_MULTIPLIER,
    }
