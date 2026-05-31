from __future__ import annotations

import logging
from typing import Any, Literal

import httpx
import pandas as pd

from .config import SAMPLE_DIR
from .x402 import X402Client

logger = logging.getLogger(__name__)

Mode = Literal["live", "offline-demo", "offline-fallback"]

BINANCE_SYMBOLS = {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT"}


def load_offline(symbol: str) -> tuple[pd.DataFrame, Mode]:
    sym = symbol.upper()
    path = SAMPLE_DIR / f"{sym.lower()}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Sample data not found for {sym}: {path}")
    df = pd.read_csv(path)
    return df, "offline-demo"


async def _fetch_with_x402_retry(
    url: str,
    params: dict[str, Any],
    *,
    alpha_value_bps: float = 5.0,
    max_retries: int = 1,
) -> list[Any]:
    """Fetch external data with optional x402 HTTP 402 intercept & retry pipeline."""
    x402 = X402Client()
    last_status: int | None = None

    async with httpx.AsyncClient(timeout=15.0) as client:
        for attempt in range(max_retries + 1):
            resp = await client.get(url, params=params)
            last_status = resp.status_code

            if resp.status_code != 402:
                resp.raise_for_status()
                return resp.json()

            # --- x402 intercept ---
            body: dict[str, Any] | None = None
            if resp.text:
                content_type = resp.headers.get("content-type", "")
                if "json" in content_type:
                    try:
                        body = resp.json()
                    except Exception:
                        logger.debug(
                            "x402 body claimed JSON but failed to parse for %s",
                            url,
                        )
                # Non-JSON body → headers-only parsing below

            schema = x402.parse_schema(dict(resp.headers), body=body)
            if schema is None:
                logger.warning(
                    "x402 response from %s missing payment schema (status=%d)",
                    url,
                    last_status,
                )
                break

            if not x402.should_pay(schema, alpha_value_bps):
                logger.warning(
                    "x402 payment declined for %s (amount=$%.4f, alpha=%.1fbps)",
                    schema.resource,
                    schema.amountUsd,
                    alpha_value_bps,
                )
                break

            payment = x402.prepare_payment(schema, alpha_value_bps=alpha_value_bps)
            logger.info(
                "x402 payment approved for %s: $%.4f %s → %s",
                schema.resource,
                schema.amountUsd,
                schema.asset,
                schema.recipient,
            )

            if not payment["approved"] or not payment["payload"]:
                logger.warning("x402 payment preparation incomplete, breaking retry loop")
                break

            # Submit signed payment payload to Blocky402 Facilitator for on-chain settlement
            facilitator_result = await x402.submit_to_facilitator(payment)
            logger.info(
                "x402 Facilitator result: submitted=%s mode=%s receipt=%s",
                facilitator_result.get("submitted"),
                facilitator_result.get("mode"),
                facilitator_result.get("receipt"),
            )
            if not facilitator_result.get("submitted"):
                logger.error("x402 Facilitator submission failed: %s", facilitator_result.get("message"))
                break

            # Use facilitator-provided on-chain receipt as payment proof for retry
            params = {
                **params,
                "x402-payment-proof": payment["payload"],
                "x402-receipt": facilitator_result.get("receipt", ""),
            }
            logger.info("Retrying with x402 on-chain payment proof (facilitator=%s)", facilitator_result.get("mode"))
            # Fall through to next attempt (or exhaust) with payment proof

    raise httpx.HTTPStatusError(
        f"External API {url} returned {last_status} after x402 intercept (attempts={attempt + 1})",
        request=resp.request,
        response=resp,
    )


async def fetch_binance_klines(symbol: str, limit: int = 500) -> pd.DataFrame:
    pair = BINANCE_SYMBOLS.get(symbol.upper())
    if not pair:
        raise ValueError(f"Unsupported symbol for live mode: {symbol}")
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": pair, "interval": "1h", "limit": limit}
    rows = await _fetch_with_x402_retry(url, params, alpha_value_bps=5.0)

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
    # Live Binance klines provide only OHLCV. Do not fabricate derivative or
    # on-chain values; downstream factors will mark absent metrics as missing.
    df["spot_price"] = df["close"]
    try:
        from crypto_factors.mantle_native import fetch_mantle_metrics

        mantle_metrics = await fetch_mantle_metrics()
        for key, value in mantle_metrics.items():
            if key.startswith("_") or value is None:
                continue
            df[key] = value
        df.attrs["mantleMetrics"] = mantle_metrics
    except Exception as exc:
        df.attrs["mantleMetrics"] = {
            "_status": "unavailable",
            "_errors": [{"provider": "mantle-native", "message": str(exc)}],
        }
    return df


async def load_market_data(symbol: str, mode: str | None = None) -> tuple[pd.DataFrame, Mode]:
    if mode == "offline-demo":
        return load_offline(symbol)
    if mode == "live":
        return await fetch_binance_klines(symbol), "live"

    try:
        return await fetch_binance_klines(symbol), "live"
    except Exception:
        df, _ = load_offline(symbol)
        return df, "offline-fallback"
