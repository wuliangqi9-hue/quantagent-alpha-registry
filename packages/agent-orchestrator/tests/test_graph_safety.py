from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_orchestrator.graph import AgentOrchestrator  # noqa: E402


class TestAgentGraphSafety(unittest.TestCase):
    def test_exploration_hints_use_raw_factor_aliases(self) -> None:
        orchestrator = AgentOrchestrator()
        orchestrator.a2c.evaluate = lambda **_: type(
            "Decision",
            (),
            {
                "explorationNeeded": True,
                "confidence": 0.2,
                "to_dict": lambda self: {
                    "schema": "test",
                    "explorationNeeded": True,
                    "confidence": 0.2,
                },
            },
        )()
        context = orchestrator.run(
            symbol="BTC",
            factor_summary={
                "factors": [{"id": "volume", "score": 0.4, "missing": False}],
                "rawFactorColumns": ["f_liquidity_amount_ma_zscore_safe"],
            },
            memory_context={"summary": {}},
            agent_reputation=None,
        )

        missing = context["explorationHints"]["missingFactorColumns"]
        self.assertNotIn("liquidity_depth", missing)


if __name__ == "__main__":
    unittest.main()
