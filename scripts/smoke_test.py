"""End-to-end smoke test for offline demo mode."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages" / "factor-engine"))
sys.path.insert(0, str(ROOT / "packages" / "strategy-selector"))

import pandas as pd
from factor_engine.service import compute_factor_summary
from strategy_selector.selector import select_strategy

from services.api.app.decision import build_decision_report, signal_hash
from services.api.app.reputation import settle_last_signal


def main() -> None:
    for sym in ["BTC", "ETH", "SOL"]:
        df = pd.read_csv(ROOT / "data" / "sample" / f"{sym.lower()}.csv")
        factors = compute_factor_summary(df)
        selection = select_strategy(sym, factors, df)
        report = build_decision_report(sym, "offline-demo", factors, selection)
        payload = {
            "symbol": sym,
            "mode": "offline-demo",
            "signalHash": signal_hash(report),
            "selection": selection,
        }
        settlement = settle_last_signal(payload)
        print(sym, selection["strategyId"], selection["marketRegime"], selection["confidence"], settlement["score"])
    print("OK")


if __name__ == "__main__":
    main()
