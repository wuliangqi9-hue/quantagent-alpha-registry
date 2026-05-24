from __future__ import annotations

from typing import Literal

import httpx
import pandas as pd

from .config import SAMPLE_DIR

Mode = Literal["live", "offline-demo"]

BINANCE_SYMBOLS = {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT"}


def load_offline(symbol: str) -> tuple[pd.DataFrame, Mode]:
    sym = symbol.upper()
    path = SAMPLE_DIR / f"{sym.lower()}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Sample data not found for {sym}: {path}")
    df = pd.read_csv(path)
    return df, "offline-demo"


async def fetch_binance_klines(symbol: str, limit: int = 500) -> pd.DataFrame:
    pair = BINANCE_SYMBOLS.get(symbol.upper())
    if not pair:
        raise ValueError(f"Unsupported symbol for live mode: {symbol}")
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": pair, "interval": "1h", "limit": limit}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        rows = resp.json()

    records = []
    for row in rows:
        records.append(
            {
                "timestamp": pd.to_datetime(row[0], unit="ms", utc=True),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
            }
        )
    df = pd.DataFrame(records)
    # Enrich with derivative/on-chain placeholders for factor module compatibility
    df["circulating_supply"] = 1.0
    df["funding_rate"] = 0.0001
    df["open_interest"] = df["close"] * df["volume"] * 100
    df["spot_price"] = df["close"]
    df["perp_price"] = df["close"] * 1.0002
    df["long_short_ratio"] = 1.0
    df["taker_buy_volume"] = df["volume"] * 0.55
    df["taker_sell_volume"] = df["volume"] * 0.45
    df["market_cap"] = df["close"] * 1e6
    df["realized_cap"] = df["close"] * 0.8e6
    df["sopr"] = 1.0
    df["transfer_volume"] = df["volume"] * df["close"]
    df["tx_count"] = 100000
    df["active_addresses"] = 500000
    df["fees"] = 1000
    df["github_commits"] = 10
    return df


async def load_market_data(symbol: str, mode: str | None = None) -> tuple[pd.DataFrame, Mode]:
    if mode == "offline-demo":
        return load_offline(symbol)
    if mode == "live":
        try:
            return await fetch_binance_klines(symbol), "live"
        except Exception:
            return load_offline(symbol)

    try:
        return await fetch_binance_klines(symbol), "live"
    except Exception:
        return load_offline(symbol)
