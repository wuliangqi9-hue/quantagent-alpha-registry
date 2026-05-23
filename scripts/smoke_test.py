"""End-to-end smoke test for offline demo mode."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "factor-engine"))
sys.path.insert(0, str(ROOT / "packages" / "strategy-selector"))

import pandas as pd
from factor_engine.service import compute_factor_summary
from strategy_selector.selector import select_strategy


def main() -> None:
    for sym in ["BTC", "ETH", "SOL"]:
        df = pd.read_csv(ROOT / "data" / "sample" / f"{sym.lower()}.csv")
        factors = compute_factor_summary(df)
        selection = select_strategy(sym, factors, df)
        print(sym, selection["strategyId"], selection["marketRegime"], selection["confidence"])
    print("OK")


if __name__ == "__main__":
    main()
