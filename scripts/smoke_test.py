"""End-to-end smoke test for offline demo mode."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages" / "factor-engine"))
sys.path.insert(0, str(ROOT / "packages" / "strategy-selector"))
sys.path.insert(0, str(ROOT / "packages" / "agent-memory"))
sys.path.insert(0, str(ROOT / "packages" / "agent-orchestrator"))

import pandas as pd
from agent_orchestrator import build_agent_context
from factor_engine.service import compute_factor_summary
from strategy_selector.selector import select_strategy

from services.api.app.decision import build_decision_report, signal_hash
from services.api.app.reputation import settle_last_signal


def main() -> None:
    for sym in ["BTC", "ETH", "SOL"]:
        df = pd.read_csv(ROOT / "data" / "sample" / f"{sym.lower()}.csv")
        factors = compute_factor_summary(df)
        memory_context = {"summary": {"count": 1, "avgPnlBps": -12.5, "latestPnlBps": -12.5}, "retrieved": []}
        multi_agent_context = build_agent_context(
            symbol=sym,
            factor_summary=factors,
            memory_context=memory_context,
            agent_reputation={"score": 6500},
        )
        selection = select_strategy(
            sym,
            factors,
            df,
            agent_reputation={"score": 6500},
            last_settlement_pnl=-12.5,
            memory_context=memory_context,
            multi_agent_context=multi_agent_context,
        )
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
