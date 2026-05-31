from __future__ import annotations

import unittest
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd

from strategy_selector.selector import (
    _pick_strategy,
    _classify_regime,
    _risk_warnings,
    _factor_map,
    _safe_parse_llm_response,
    _apply_reputation_guardrails,
    _apply_reflection_guardrails,
    _apply_memory_guardrails,
    _memory_loss_streak,
    _memory_context_summary,
    _risk_profile_from_reputation,
    _reputation_impact,
    _benchmark_id,
    _default_alpha_formula,
    _default_formula_rationale,
    _reflection_from_settlement,
    _build_system_prompt,
    _build_position_plan,
    select_strategy,
    LLMStrategyDecision,
    STRATEGIES,
    STRATEGY_BENCHMARKS,
)
from strategy_selector.benchmark import build_benchmark_chart


def _make_ohlcv_df(rows: int = 120) -> pd.DataFrame:
    import numpy as np

    np.random.seed(42)
    base = 60000.0
    closes = [base + float(v) for v in np.cumsum(np.random.randn(rows) * 200)]
    now = datetime.now(timezone.utc)
    timestamps = [
        (now - pd.Timedelta(minutes=i)).isoformat() for i in range(rows, 0, -1)
    ]
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": [c * 0.999 for c in closes],
            "high": [c * 1.002 for c in closes],
            "low": [c * 0.998 for c in closes],
            "close": closes,
            "volume": [100.0 + i * 5 for i in range(rows)],
        }
    )


def _make_factor_summary(items: list[tuple[str, float]]) -> dict:
    """Build a factor_summary dict matching the internal `factors` list format."""
    return {"factors": [{"id": k, "score": v, "missing": False} for k, v in items]}


# -- _factor_map ----------------------------------------------------------

class TestFactorMap(unittest.TestCase):
    def test_extracts_from_factors_list(self) -> None:
        summary = _make_factor_summary(
            [("momentum", 0.35), ("trend", 0.60), ("volatility", 0.80)]
        )
        result = _factor_map(summary)
        self.assertAlmostEqual(result["momentum"], 0.35)
        self.assertAlmostEqual(result["trend"], 0.60)
        self.assertAlmostEqual(result["volatility"], 0.80)

    def test_empty_factors_returns_empty_dict(self) -> None:
        result = _factor_map({})
        self.assertEqual(len(result), 0)

    def test_missing_items_skipped(self) -> None:
        summary = {
            "factors": [
                {"id": "momentum", "score": 0.5, "missing": False},
                {"id": "liquidity", "score": None, "missing": True},
                {"id": "trend", "score": 0.4, "missing": False},
            ]
        }
        result = _factor_map(summary)
        self.assertAlmostEqual(result["momentum"], 0.5)
        self.assertAlmostEqual(result["trend"], 0.4)
        self.assertNotIn("liquidity", result)


# -- _classify_regime -----------------------------------------------------

class TestClassifyRegime(unittest.TestCase):
    def test_bull_regime(self) -> None:
        regime = _classify_regime(
            {"momentum": 0.5, "trend": 0.6, "volatility": 0.3, "funding": 0.1},
            0.015,
        )
        self.assertEqual(regime, "bull")

    def test_bear_regime(self) -> None:
        regime = _classify_regime(
            {"momentum": -0.6, "trend": -0.5, "volatility": 0.4, "funding": -0.1},
            0.02,
        )
        self.assertEqual(regime, "bear")

    def test_range_regime_neutral_momentum(self) -> None:
        regime = _classify_regime(
            {"momentum": 0.0, "trend": 0.1, "volatility": 0.2, "funding": 0.0},
            0.01,
        )
        self.assertEqual(regime, "range")

    def test_low_vol_range_condition(self) -> None:
        """abs(trend) < 0.25 and recent_vol < 0.02 triggers range."""
        regime = _classify_regime(
            {"momentum": 0.2, "trend": 0.1}, 0.015
        )
        self.assertEqual(regime, "range")

    def test_bear_from_negative_momentum_trend(self) -> None:
        regime = _classify_regime(
            {"momentum": -0.2, "trend": -0.3}, 0.025
        )
        self.assertEqual(regime, "bear")

    def test_bull_from_positive_momentum(self) -> None:
        regime = _classify_regime(
            {"momentum": 0.3, "trend": -0.1}, 0.025
        )
        self.assertEqual(regime, "bull")

    def test_default_range_when_no_factors(self) -> None:
        regime = _classify_regime({}, 0.03)
        self.assertEqual(regime, "range")


# -- _pick_strategy -------------------------------------------------------

class TestPickStrategy(unittest.TestCase):
    def test_bull_selects_supertrend(self) -> None:
        sid, conf, drivers = _pick_strategy("bull", {"momentum": 0.4, "trend": 0.3})
        self.assertEqual(sid, "supertrend")
        self.assertGreater(conf, 0.5)

    def test_bear_selects_macd_bollinger(self) -> None:
        sid, conf, drivers = _pick_strategy("bear", {"momentum": -0.4, "trend": -0.4})
        self.assertEqual(sid, "macd_bollinger")
        self.assertGreater(conf, 0.4)

    def test_range_selects_bollinger(self) -> None:
        sid, conf, drivers = _pick_strategy("range", {"momentum": 0.05})
        self.assertEqual(sid, "bollinger")

    def test_unknown_regime_falls_back_to_macd_bollinger(self) -> None:
        sid, conf, drivers = _pick_strategy("random_regime", {})
        self.assertEqual(sid, "macd_bollinger")

    def test_high_volatility_reduces_confidence(self) -> None:
        sid, conf, drivers = _pick_strategy("bear", {"volatility": 2.0, "momentum": 0.0})
        self.assertLessEqual(conf, 0.65)


# -- _risk_warnings -------------------------------------------------------

class TestRiskWarnings(unittest.TestCase):
    def test_high_recent_vol_warning(self) -> None:
        warnings = _risk_warnings({"volatility": 0.5, "funding": 0.1}, "bull", 0.05)
        self.assertTrue(any("realized volatility is elevated" in w for w in warnings))

    def test_extreme_funding_warning(self) -> None:
        warnings = _risk_warnings({"funding": 1.5, "volatility": 0.3}, "bull", 0.01)
        self.assertTrue(any("Funding rate is extreme" in w for w in warnings))

    def test_fallback_no_elevated_risk_flags(self) -> None:
        warnings = _risk_warnings({"volatility": 0.2, "funding": 0.01}, "range", 0.005)
        self.assertGreaterEqual(len(warnings), 1)
        self.assertTrue(any("No elevated risk flags" in w for w in warnings))

    def test_range_with_momentum_spike_warning(self) -> None:
        warnings = _risk_warnings({"momentum": 0.9}, "range", 0.01)
        self.assertTrue(any("false breakouts" in w for w in warnings))


# -- _safe_parse_llm_response ---------------------------------------------

class TestSafeParseLLMResponse(unittest.TestCase):
    def setUp(self) -> None:
        self.defaults = LLMStrategyDecision(
            strategyId="bollinger",
            signalDirection="neutral",
            confidence=0.5,
            topDrivers=["test"],
            riskWarnings=[],
            explanation="default",
            alphaFormula="test",
            formulaRationale="test",
            riskProfileState="neutral",
            reputationImpact="test",
            reflection="test",
        )

    def test_none_returns_defaults(self) -> None:
        result = _safe_parse_llm_response(None, self.defaults)
        self.assertEqual(result.strategyId, self.defaults.strategyId)

    def test_valid_dict_overrides_fields(self) -> None:
        payload = {"strategyId": "supertrend", "confidence": 0.85}
        result = _safe_parse_llm_response(payload, self.defaults)
        self.assertEqual(result.strategyId, "supertrend")
        self.assertEqual(result.confidence, 0.85)

    def test_json_string_parsed_correctly(self) -> None:
        payload = '{"strategyId": "macd_bollinger", "confidence": 0.72}'
        result = _safe_parse_llm_response(payload, self.defaults)
        self.assertEqual(result.strategyId, "macd_bollinger")
        self.assertEqual(result.confidence, 0.72)

    def test_malformed_json_returns_defaults(self) -> None:
        payload = "not valid json {"
        result = _safe_parse_llm_response(payload, self.defaults)
        self.assertEqual(result.strategyId, self.defaults.strategyId)

    def test_invalid_type_returns_defaults(self) -> None:
        payload = [1, 2, 3]
        result = _safe_parse_llm_response(payload, self.defaults)
        self.assertEqual(result.strategyId, self.defaults.strategyId)

    def test_risk_profile_validation(self) -> None:
        payload = {"riskProfileState": "invalid"}
        result = _safe_parse_llm_response(payload, self.defaults)
        self.assertEqual(result.riskProfileState, "neutral")

    def test_invalid_confidence_string_returns_defaults(self) -> None:
        payload = {"confidence": "high_confidence"}
        result = _safe_parse_llm_response(payload, self.defaults)
        self.assertEqual(result.confidence, self.defaults.confidence)


# -- reputation / reflection / memory guardrails --------------------------

class TestReputationGuardrails(unittest.TestCase):
    def test_conservative_forces_neutral_and_bollinger(self) -> None:
        sid, conf, direction, drv, warn = _apply_reputation_guardrails(
            "supertrend", 0.8, "long", ["momentum"], [], "conservative"
        )
        self.assertEqual(sid, "bollinger")
        self.assertEqual(direction, "neutral")
        self.assertLessEqual(conf, 0.60)

    def test_aggressive_boosts_confidence(self) -> None:
        sid, conf, direction, drv, warn = _apply_reputation_guardrails(
            "supertrend", 0.70, "long", ["momentum"], [], "aggressive"
        )
        self.assertAlmostEqual(conf, 0.73)

    def test_neutral_unchanged(self) -> None:
        sid, conf, direction, drv, warn = _apply_reputation_guardrails(
            "macd_bollinger", 0.65, "short", ["trend"], ["test"], "neutral"
        )
        self.assertEqual(sid, "macd_bollinger")
        self.assertEqual(conf, 0.65)
        self.assertEqual(direction, "short")


class TestReflectionGuardrails(unittest.TestCase):
    def test_material_loss_reduces_confidence(self) -> None:
        conf, drv, warn = _apply_reflection_guardrails(0.70, ["momentum"], [], -100.0)
        self.assertLess(conf, 0.70)
        self.assertTrue(len(warn) > 0)

    def test_mild_loss_small_haircut(self) -> None:
        conf, drv, warn = _apply_reflection_guardrails(0.70, ["momentum"], [], -10.0)
        self.assertLess(conf, 0.70)

    def test_positive_pnl_boosts_confidence(self) -> None:
        conf, drv, warn = _apply_reflection_guardrails(0.70, ["momentum"], [], 80.0)
        self.assertGreaterEqual(conf, 0.72)
        self.assertTrue(any("Positive" in d for d in drv))

    def test_none_unchanged(self) -> None:
        conf, drv, warn = _apply_reflection_guardrails(0.70, ["momentum"], [], None)
        self.assertEqual(conf, 0.70)


class TestMemoryGuardrails(unittest.TestCase):
    def test_recent_loss_haircut(self) -> None:
        ctx = {"summary": {"latestPnlBps": -60, "avgPnlBps": -20, "count": 3}}
        conf, drv, warn = _apply_memory_guardrails(0.70, ["m"], [], ctx)
        self.assertLess(conf, 0.70)

    def test_positive_memory_bonus(self) -> None:
        ctx = {"summary": {"latestPnlBps": 30, "avgPnlBps": 30, "count": 3}}
        conf, drv, warn = _apply_memory_guardrails(0.70, ["m"], [], ctx)
        self.assertGreaterEqual(conf, 0.72)

    def test_none_context_unchanged(self) -> None:
        conf, drv, warn = _apply_memory_guardrails(0.70, ["m"], [], None)
        self.assertEqual(conf, 0.70)

    def test_insufficient_sample_no_bonus(self) -> None:
        ctx = {"summary": {"latestPnlBps": 30, "avgPnlBps": 30, "count": 1}}
        conf, drv, warn = _apply_memory_guardrails(0.70, ["m"], [], ctx)
        self.assertEqual(conf, 0.70)


# -- helper functions -----------------------------------------------------

class TestMemoryLossStreak(unittest.TestCase):
    def test_returns_zero_for_none(self) -> None:
        self.assertEqual(_memory_loss_streak(None), 0)

    def test_returns_int_from_context(self) -> None:
        self.assertEqual(
            _memory_loss_streak({"summary": {"consecutiveLosses": 5}}), 5
        )

    def test_defaults_zero_for_missing_key(self) -> None:
        self.assertEqual(_memory_loss_streak({"summary": {}}), 0)


class TestMemoryContextSummary(unittest.TestCase):
    def test_none_returns_no_memory(self) -> None:
        result = _memory_context_summary(None)
        self.assertIn("No retrieved", result)

    def test_empty_context(self) -> None:
        result = _memory_context_summary({})
        self.assertIn("No retrieved", result)

    def test_with_data(self) -> None:
        ctx = {
            "summary": {"count": 10, "avgPnlBps": 15.0, "latestPnlBps": 20},
            "retrieved": [{"id": 1}, {"id": 2}],
        }
        result = _memory_context_summary(ctx)
        self.assertIn("10 records", result)
        self.assertIn("retrieved memories 2", result)


class TestRiskProfileFromReputation(unittest.TestCase):
    def test_low_reputation_conservative(self) -> None:
        # score < 3000 (on 0-10000 scale)
        rp = _risk_profile_from_reputation({"score": 10})
        self.assertEqual(rp, "conservative")

    def test_moderate_reputation_neutral(self) -> None:
        rp = _risk_profile_from_reputation({"score": 5000})
        self.assertEqual(rp, "neutral")

    def test_high_reputation_aggressive(self) -> None:
        # score > 7000
        rp = _risk_profile_from_reputation({"score": 7500})
        self.assertEqual(rp, "aggressive")

    def test_none_defaults_neutral(self) -> None:
        rp = _risk_profile_from_reputation(None)
        self.assertEqual(rp, "neutral")


class TestReputationImpact(unittest.TestCase):
    def test_conservative_impact_mentions_reputation(self) -> None:
        impact = _reputation_impact({"score": 10}, "conservative")
        self.assertIn("reputation", impact.lower())

    def test_aggressive_impact_mentions_variance(self) -> None:
        impact = _reputation_impact({"score": 7500}, "aggressive")
        self.assertIn("higher variance", impact.lower())


class TestBenchmarkId(unittest.TestCase):
    def test_supertrend(self) -> None:
        self.assertEqual(_benchmark_id("supertrend"), "supertrend")

    def test_macd_bollinger(self) -> None:
        self.assertEqual(_benchmark_id("macd_bollinger"), "macd_bollinger")

    def test_unknown_defaults_to_bollinger(self) -> None:
        self.assertEqual(_benchmark_id("unknown_strategy"), "bollinger")


class TestDefaultAlphaFormula(unittest.TestCase):
    def test_returns_non_empty_string(self) -> None:
        f = _default_alpha_formula({"momentum": 0.3}, "neutral")
        self.assertIsInstance(f, str)
        self.assertTrue(len(f) > 0)

    def test_aggressive_uses_higher_momentum_weight(self) -> None:
        f = _default_alpha_formula({"momentum": 0.5, "trend": 0.6}, "aggressive")
        self.assertIn("0.55", f)


class TestDefaultFormulaRationale(unittest.TestCase):
    def test_returns_non_empty_string(self) -> None:
        r = _default_formula_rationale("bull", {"momentum": 0.3}, "neutral")
        self.assertIsInstance(r, str)
        self.assertTrue(len(r) > 0)

    def test_mentions_regime(self) -> None:
        r = _default_formula_rationale("bear", {"trend": -0.4}, "neutral")
        self.assertIn("bear", r.lower())


class TestReflectionFromSettlement(unittest.TestCase):
    def test_none_settlement_returns_default(self) -> None:
        r = _reflection_from_settlement(None, None)
        self.assertIn("No previous settlement", r)

    def test_positive_pnl(self) -> None:
        r = _reflection_from_settlement(80.0, None)
        self.assertIn("gained", r.lower())

    def test_negative_pnl(self) -> None:
        r = _reflection_from_settlement(-60.0, None)
        self.assertIn("lost", r.lower())

    def test_with_trajectory_memory(self) -> None:
        ctx = {
            "retrieved": [
                {"pnlBps": -30},
                {"pnlBps": -40},
            ]
        }
        r = _reflection_from_settlement(-10.0, ctx)
        self.assertIn("consecutive-loss streak", r)


class TestBuildSystemPrompt(unittest.TestCase):
    def test_basic_prompt(self) -> None:
        summary = _make_factor_summary([("momentum", 0.3), ("trend", 0.4)])
        prompt = _build_system_prompt(
            factor_summary=summary,
            risk_profile="neutral",
            agent_reputation=None,
            last_settlement_pnl=None,
            memory_context=None,
            multi_agent_context=None,
        )
        self.assertIn("QuantAgent", prompt)
        self.assertIn("momentum", prompt)

    def test_multi_agent_context_injected(self) -> None:
        summary = _make_factor_summary([("momentum", 0.5)])
        prompt = _build_system_prompt(
            factor_summary=summary,
            risk_profile="aggressive",
            agent_reputation={"score": 8000},
            last_settlement_pnl=50.0,
            memory_context={"summary": {"count": 3}},
            multi_agent_context={"riskCriticWarnings": ["test warning"]},
        )
        self.assertIn("aggressive", prompt)
        self.assertIn("multi-agent", prompt.lower())


class TestBuildPositionPlan(unittest.TestCase):
    def test_returns_plan_dict(self) -> None:
        plan = _build_position_plan(
            direction="long",
            confidence=0.75,
            factors={"momentum": 0.4, "volatility": 0.3},
            recent_vol=0.015,
            risk_profile="neutral",
            memory_context=None,
            risk_warnings=[],
        )
        self.assertIn("targetExposure", plan)
        self.assertIn("orderType", plan)
        self.assertGreater(plan["targetExposure"], 0.0)

    def test_neutral_direction_zero_exposure(self) -> None:
        plan = _build_position_plan(
            direction="neutral",
            confidence=0.4,
            factors={},
            recent_vol=0.02,
            risk_profile="conservative",
            memory_context={"summary": {"consecutiveLosses": 3}},
            risk_warnings=["loss streak"],
        )
        self.assertEqual(plan["targetExposure"], 0.0)
        self.assertEqual(plan["orderType"], "observe")


# -- select_strategy end-to-end -------------------------------------------

class TestSelectStrategyEndToEnd(unittest.TestCase):
    def setUp(self) -> None:
        self.df = _make_ohlcv_df(120)

    def test_bull_factor_summary(self) -> None:
        summary = _make_factor_summary(
            [
                ("momentum", 0.45),
                ("trend", 0.55),
                ("volatility", 0.25),
                ("liquidity", 0.50),
                ("sentiment", 0.30),
                ("onchain_flow", 0.20),
                ("funding", 0.02),
                ("correlation", 0.85),
            ]
        )
        result = select_strategy("BTC", summary, self.df)
        self.assertEqual(result["symbol"], "BTC")
        self.assertIn(result["strategyId"], STRATEGIES)
        self.assertIsInstance(result["confidence"], float)
        self.assertGreater(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 1.0)
        self.assertIn("positionPlan", result)
        self.assertIn("benchmarkSummary", result)
        self.assertIn("benchmarkChart", result)
        self.assertIn("alphaFormula", result)
        self.assertIn("formulaRationale", result)
        self.assertIn("llmSystemPrompt", result)

    def test_bear_factor_summary(self) -> None:
        summary = _make_factor_summary(
            [
                ("momentum", -0.55),
                ("trend", -0.50),
                ("volatility", 0.40),
                ("funding", -0.03),
            ]
        )
        result = select_strategy("ETH", summary, self.df)
        self.assertEqual(result["marketRegime"], "bear")

    def test_with_conservative_reputation(self) -> None:
        summary = _make_factor_summary([("momentum", 0.45), ("trend", 0.55)])
        result = select_strategy(
            "BTC", summary, self.df, agent_reputation={"score": 5}
        )
        self.assertEqual(result["riskProfileState"], "conservative")
        self.assertEqual(result["strategyId"], "bollinger")
        self.assertEqual(result["signalDirection"], "neutral")

    def test_with_aggressive_reputation(self) -> None:
        summary = _make_factor_summary([("momentum", 0.45), ("trend", 0.55)])
        result = select_strategy(
            "BTC", summary, self.df, agent_reputation={"score": 7500}
        )
        self.assertEqual(result["riskProfileState"], "aggressive")

    def test_with_negative_settlement(self) -> None:
        summary = _make_factor_summary([("momentum", 0.45), ("trend", 0.55)])
        result = select_strategy(
            "BTC", summary, self.df, last_settlement_pnl=-200.0
        )
        self.assertLess(result["confidence"], 0.75)

    def test_with_memory_context(self) -> None:
        summary = _make_factor_summary([("momentum", 0.45), ("trend", 0.55)])
        result = select_strategy(
            "BTC",
            summary,
            self.df,
            memory_context={
                "summary": {
                    "count": 5,
                    "avgPnlBps": 30,
                    "latestPnlBps": 40,
                    "consecutiveLosses": 0,
                    "currentExposure": 0.30,
                    "unrealizedPnlBps": -200,
                },
                "retrieved": [{"id": 1}],
            },
        )
        self.assertIn("positionPlan", result)

    def test_with_llm_response_override(self) -> None:
        summary = {
            "factors": [{"id": "momentum", "score": 0.45, "missing": False}],
            "llmStrategyDecision": {
                "strategyId": "supertrend",
                "signalDirection": "long",
                "confidence": 0.82,
                "topDrivers": ["momentum", "trend"],
                "riskWarnings": [],
                "explanation": "LLM override explanation",
                "alphaFormula": "0.4*momentum + 0.3*trend",
                "formulaRationale": "LLM reasoned formula",
                "riskProfileState": "neutral",
                "reputationImpact": "neutral reputation",
                "reflection": "LLM reflection",
            },
        }
        result = select_strategy("BTC", summary, self.df)
        self.assertEqual(result["alphaFormula"], "0.4*momentum + 0.3*trend")

    def test_llm_strategy_override_rebuilds_benchmark_chart(self) -> None:
        summary = {
            "factors": [{"id": "momentum", "score": -0.55, "missing": False}],
            "llmStrategyDecision": {
                "strategyId": "supertrend",
                "confidence": 0.80,
            },
        }
        result = select_strategy("BTC", summary, self.df)
        self.assertEqual(result["strategyId"], "supertrend")
        self.assertEqual(
            result["benchmarkSummary"]["winRate"],
            STRATEGY_BENCHMARKS["supertrend"]["win_rate"],
        )
        self.assertEqual(
            result["benchmarkChart"]["evidence"]["win_rate"],
            STRATEGY_BENCHMARKS["supertrend"]["win_rate"],
        )

    def test_with_multi_agent_risk_critic(self) -> None:
        summary = _make_factor_summary([("momentum", 0.45), ("trend", 0.55)])
        result = select_strategy(
            "BTC",
            summary,
            self.df,
            multi_agent_context={
                "riskCriticWarnings": ["volatility is high, cap confidence"]
            },
        )
        # confidence should be reduced by risk critic
        self.assertLess(result["confidence"], 0.85)

    def test_with_consecutive_loss_critic(self) -> None:
        summary = _make_factor_summary([("momentum", 0.45), ("trend", 0.55)])
        result = select_strategy(
            "BTC",
            summary,
            self.df,
            multi_agent_context={
                "riskCriticWarnings": [
                    "consecutive-loss streak detected, reflection critic"
                ]
            },
        )
        self.assertLessEqual(result["confidence"], 0.80)
        self.assertIn(
            result["strategyId"], ["reversal_trend", "range_mean_reversion"]
        )

    def test_empty_factor_summary_handled(self) -> None:
        result = select_strategy("BTC", {}, self.df)
        self.assertIn("strategyId", result)
        self.assertIsInstance(result["confidence"], float)

    def test_small_ohlcv_handled(self) -> None:
        small_df = _make_ohlcv_df(30)
        summary = _make_factor_summary([("momentum", 0.3)])
        result = select_strategy("BTC", summary, small_df)
        self.assertIn("benchmarkChart", result)

    def test_empty_benchmark_chart_handled(self) -> None:
        chart = build_benchmark_chart(pd.DataFrame({"close": []}), "supertrend")
        self.assertEqual(chart["prices"], [])
        self.assertEqual(chart["markers"], [])

    def test_strategies_dict_has_required_keys(self) -> None:
        for sid in STRATEGIES:
            self.assertIn("name", STRATEGIES[sid])
            self.assertIn("description", STRATEGIES[sid])

    def test_strategy_benchmarks_have_required_keys(self) -> None:
        for sid in STRATEGY_BENCHMARKS:
            self.assertIn("win_rate", STRATEGY_BENCHMARKS[sid])
            self.assertIn("max_drawdown_pct", STRATEGY_BENCHMARKS[sid])


if __name__ == "__main__":
    unittest.main()
