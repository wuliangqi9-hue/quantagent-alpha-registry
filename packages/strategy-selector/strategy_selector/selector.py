from __future__ import annotations

from typing import Any

from .benchmark import STRATEGY_BENCHMARKS, build_benchmark_chart

MODEL_VERSION = "strategy-selector-1.0.0"

STRATEGIES = {
    "supertrend": {
        "name": "SuperTrend",
        "description": "Trend-following strategy suited to directional markets.",
    },
    "bollinger": {
        "name": "Bollinger",
        "description": "Mean-reversion strategy suited to range-bound markets.",
    },
    "macd_bollinger": {
        "name": "MACD + Bollinger",
        "description": "Hybrid momentum and band strategy for mixed or bearish regimes.",
    },
}


def _factor_map(factor_summary: dict[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for item in factor_summary.get("factors", []):
        if item.get("score") is not None and not item.get("missing"):
            out[item["id"]] = float(item["score"])
    return out


def _classify_regime(factors: dict[str, float], recent_vol: float) -> str:
    momentum = factors.get("momentum", 0.0)
    trend = factors.get("trend", 0.0)
    if momentum > 0.35 and trend > 0.2:
        return "bull"
    if momentum < -0.35 and trend < -0.2:
        return "bear"
    if abs(trend) < 0.25 and recent_vol < 0.02:
        return "range"
    if momentum < 0 and trend < 0:
        return "bear"
    if momentum > 0:
        return "bull"
    return "range"


def _pick_strategy(regime: str, factors: dict[str, float]) -> tuple[str, float, list[str]]:
    volatility = abs(factors.get("volatility", 0.0))
    funding = factors.get("funding", 0.0)
    drivers: list[str] = []

    if regime == "bull":
        strategy_id = "supertrend"
        confidence = 0.72 + min(0.15, max(factors.get("trend", 0.0), 0.0) * 0.1)
        drivers = ["Strong positive momentum", "Trend gap supports continuation"]
    elif regime == "range":
        strategy_id = "bollinger"
        confidence = 0.7 + min(0.12, 0.08 if volatility < 1.0 else 0.0)
        drivers = ["Compressed trend gap", "Range-friendly volatility profile"]
    else:
        strategy_id = "macd_bollinger"
        confidence = 0.68 + min(0.1, abs(factors.get("momentum", 0.0)) * 0.05)
        drivers = ["Bearish or mixed momentum", "Hybrid signal reduces single-indicator risk"]

    if abs(funding) > 1.2:
        confidence -= 0.08
        drivers.append("Extreme funding rate increases squeeze risk")

    if volatility > 1.5:
        confidence -= 0.1
        drivers.append("Elevated volatility reduces sizing confidence")

    confidence = round(max(0.45, min(0.92, confidence)), 2)
    return strategy_id, confidence, drivers[:4]


def _signal_direction(regime: str, factors: dict[str, float]) -> str:
    momentum = factors.get("momentum", 0.0)
    if regime == "bull" or momentum > 0.15:
        return "long"
    if regime == "bear" or momentum < -0.15:
        return "short"
    return "neutral"


def _risk_warnings(
    factors: dict[str, float],
    regime: str,
    recent_vol: float,
) -> list[str]:
    warnings: list[str] = []
    if recent_vol > 0.03:
        warnings.append("24h realized volatility is elevated; reduce position size.")
    if abs(factors.get("funding", 0.0)) > 1.0:
        warnings.append("Funding rate is extreme; crowded positioning may trigger squeezes.")
    if factors.get("open_interest") is not None and factors.get("open_interest", 0) > 1.0:
        warnings.append("Open interest momentum is high; liquidation risk may rise.")
    if regime == "range" and abs(factors.get("momentum", 0.0)) > 0.8:
        warnings.append("Momentum spike inside a range regime; false breakouts are likely.")
    if not warnings:
        warnings.append("No elevated risk flags; still subject to regime shift and slippage.")
    return warnings


def select_strategy(
    symbol: str,
    factor_summary: dict[str, Any],
    ohlcv_df,
) -> dict[str, Any]:
    factors = _factor_map(factor_summary)
    recent_vol = float(factor_summary.get("recentVolatility24h") or 0.0)
    regime = _classify_regime(factors, recent_vol)
    strategy_id, confidence, drivers = _pick_strategy(regime, factors)
    direction = _signal_direction(regime, factors)
    warnings = _risk_warnings(factors, regime, recent_vol)

    bench = STRATEGY_BENCHMARKS[strategy_id]
    regime_key = f"{regime}_sharpe" if f"{regime}_sharpe" in bench else "range_sharpe"
    sharpe = bench.get(regime_key, bench.get("range_sharpe", 0.0))

    benchmark_summary = {
        "regimeSharpe": sharpe,
        "winRate": bench["win_rate"],
        "maxDrawdownPct": bench["max_drawdown_pct"],
        "note": "Historical benchmark from prior QuantAgent/Hummingbot workflow experiments.",
    }
    chart = build_benchmark_chart(ohlcv_df, strategy_id)

    meta = STRATEGIES[strategy_id]
    return {
        "symbol": symbol.upper(),
        "modelVersion": MODEL_VERSION,
        "marketRegime": regime,
        "strategyId": strategy_id,
        "strategyName": meta["name"],
        "strategyDescription": meta["description"],
        "signalDirection": direction,
        "confidence": confidence,
        "topDrivers": drivers,
        "riskWarnings": warnings,
        "benchmarkSummary": benchmark_summary,
        "benchmarkChart": chart,
        "explanation": (
            f"Regime classified as {regime}. {meta['name']} was selected because "
            f"prior benchmark evidence shows stronger workflow fit in this state "
            f"(regime Sharpe {sharpe:.2f}). Confidence {confidence:.0%}."
        ),
    }
