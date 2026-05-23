"""Create deterministic ETH/SOL demo snapshots from the BTC sample.

The generated files are intended for hackathon demo reliability, not empirical
market claims.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "data" / "sample"


def scale_asset(source: pd.DataFrame, price_scale: float, volume_scale: float) -> pd.DataFrame:
    out = source.copy()
    for col in ["open", "high", "low", "close", "spot_price", "perp_price"]:
        if col in out.columns:
            out[col] = out[col].astype(float) * price_scale
    if "volume" in out.columns:
        out["volume"] = out["volume"].astype(float) * volume_scale
    for col in ["market_cap", "realized_cap", "transfer_volume", "open_interest"]:
        if col in out.columns:
            out[col] = out[col].astype(float) * price_scale * volume_scale
    return out


def main() -> None:
    btc = pd.read_csv(SAMPLE_DIR / "btc.csv")
    scale_asset(btc, price_scale=0.055, volume_scale=8.0).to_csv(SAMPLE_DIR / "eth.csv", index=False)
    scale_asset(btc, price_scale=0.0024, volume_scale=18.0).to_csv(SAMPLE_DIR / "sol.csv", index=False)
    print("Wrote ETH and SOL sample snapshots.")


if __name__ == "__main__":
    main()
