from __future__ import annotations

import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from strategy_selector.finpos import DirectionDecisionAgent, QuantityRiskDecisionAgent


class TestFinPosAgents(unittest.TestCase):
    def test_direction_agent_outputs_discrete_signal(self) -> None:
        decision = DirectionDecisionAgent().decide(
            regime="bull",
            factors={"momentum": 0.4, "trend": 0.2},
        )
        self.assertEqual(decision.direction, "long")
        self.assertIn("denoised", decision.reasoning)

    def test_quantity_agent_reduces_exposure_after_15_percent_crash(self) -> None:
        plan = QuantityRiskDecisionAgent().decide(
            direction="long",
            confidence=0.86,
            factors={"momentum": 0.5, "trend": 0.3, "volatility": 1.2, "funding": 0.2},
            recent_volatility=0.025,
            risk_profile="aggressive",
            memory_context={"summary": {"consecutiveLosses": 0, "maxDrawdownBps": -100}},
            risk_warnings=[],
            current_exposure=0.50,
            unrealized_pnl_bps=-1500,
        )

        self.assertLessEqual(plan.targetExposure, 0.175)
        self.assertEqual(plan.orderType, "protected-market-or-rfq")
        self.assertIn("unrealizedPnL=-1500.0bps", plan.positionRationale)

    def test_quantity_agent_conservative_neutral_observes_only(self) -> None:
        plan = QuantityRiskDecisionAgent().decide(
            direction="neutral",
            confidence=0.4,
            factors={},
            recent_volatility=0.04,
            risk_profile="conservative",
            memory_context={"summary": {"consecutiveLosses": 3}},
            risk_warnings=["loss streak"],
        )
        self.assertEqual(plan.targetExposure, 0.0)
        self.assertEqual(plan.orderType, "observe")


if __name__ == "__main__":
    unittest.main()
