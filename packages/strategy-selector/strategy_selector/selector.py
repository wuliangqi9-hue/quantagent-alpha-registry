from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from .benchmark import STRATEGY_BENCHMARKS, build_benchmark_chart
from .finpos import DirectionDecisionAgent, QuantityRiskDecisionAgent
from .policy_blender import build_policy_output

MODEL_VERSION = "strategy-selector-1.1.0-academic-agent"

RiskProfileState = Literal["aggressive", "neutral", "conservative"]

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
    "reversal_trend": {
        "name": "Reversal Trend",
        "description": "Risk-critic fallback that waits for trend reversal confirmation after loss streaks.",
    },
    "range_mean_reversion": {
        "name": "Range Mean Reversion",
        "description": "Conservative risk-critic fallback for range-bound recovery after adverse settlements.",
    },
    "breakout_swing": {
        "name": "Breakout Swing",
        "description": "Aggressive continuation strategy used only when memory and reputation permit higher variance.",
    },
}

BENCHMARK_FALLBACKS = {
    "reversal_trend": "macd_bollinger",
    "range_mean_reversion": "bollinger",
    "breakout_swing": "supertrend",
}


class LLMStrategyDecision(BaseModel):
    """LLM 强制输出结构。

    这里把 AlphaGPT / FinMem / QuantAgent 三类学术概念落成可校验字段。
    即使上游 LLM 漏字段，也会通过默认值保证实盘流程不崩溃。
    """

    strategyId: str = ""
    signalDirection: str = "neutral"
    confidence: float = 0.5
    topDrivers: list[str] = Field(default_factory=list)
    riskWarnings: list[str] = Field(default_factory=list)
    explanation: str = ""
    alphaFormula: str = ""
    formulaRationale: str = ""
    riskProfileState: RiskProfileState = "neutral"
    reputationImpact: str = "No on-chain reputation data provided; use neutral risk budget."
    reflection: str = "No previous settlement data"

    @field_validator("confidence")
    @classmethod
    def clamp_confidence(cls, value: float) -> float:
        return round(max(0.0, min(1.0, float(value))), 4)

    @field_validator("signalDirection")
    @classmethod
    def normalize_direction(cls, value: str) -> str:
        normalized = str(value).lower()
        return normalized if normalized in {"long", "short", "neutral"} else "neutral"

    @field_validator("riskProfileState")
    @classmethod
    def normalize_risk_profile(cls, value: str) -> RiskProfileState:
        normalized = str(value).lower()
        if normalized in {"aggressive", "neutral", "conservative"}:
            return normalized  # type: ignore[return-value]
        return "neutral"


def _factor_map(factor_summary: dict[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for item in factor_summary.get("factors", []):
        if item.get("score") is not None and not item.get("missing"):
            out[item["id"]] = float(item["score"])
    return out


def _benchmark_id(strategy_id: str) -> str:
    """Map derived risk-critic strategies to benchmark-compatible base strategies."""
    if strategy_id in STRATEGY_BENCHMARKS:
        return strategy_id
    return BENCHMARK_FALLBACKS.get(strategy_id, "bollinger")


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
    return DirectionDecisionAgent().decide(regime=regime, factors=factors).direction


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


def _extract_reputation_score(agent_reputation: dict[str, Any] | None) -> int | None:
    """FinMem 链上情节记忆入口：读取 ERC-8004 reputation score。"""
    if not agent_reputation:
        return None

    raw = agent_reputation.get("score")
    if raw is None and isinstance(agent_reputation.get("reputation"), dict):
        raw = agent_reputation["reputation"].get("score")
    if raw is None:
        return None

    try:
        score = int(float(raw))
    except (TypeError, ValueError):
        return None
    return max(0, min(10000, score))


def _risk_profile_from_reputation(agent_reputation: dict[str, Any] | None) -> RiskProfileState:
    score = _extract_reputation_score(agent_reputation)
    if score is None:
        return "neutral"
    if score < 3000:
        return "conservative"
    if score > 7000:
        return "aggressive"
    return "neutral"


def _reputation_impact(agent_reputation: dict[str, Any] | None, risk_profile: RiskProfileState) -> str:
    score = _extract_reputation_score(agent_reputation)
    if score is None:
        return "No on-chain reputation data provided; use neutral risk budget."
    if risk_profile == "conservative":
        return (
            f"ERC-8004 reputation score is {score}/10000, below 3000. "
            "The agent must protect reputation capital with flat or very low-risk exposure."
        )
    if risk_profile == "aggressive":
        return (
            f"ERC-8004 reputation score is {score}/10000, above 7000. "
            "The agent may accept higher variance when factor evidence is aligned."
        )
    return (
        f"ERC-8004 reputation score is {score}/10000. "
        "Risk budget remains neutral until the reputation loop earns a stronger signal."
    )


def _reflection_from_settlement(
    last_settlement_pnl: float | None,
    memory_context: dict[str, Any] | None = None,
) -> str:
    """QuantAgent + Guardrails 自我反思入口。

    把上一笔结算结果与历史记忆轨迹拼接，生成更深层的策略约束。
    决策 agent 在写 decision_prompt 时会引用此反思文本。
    """
    if last_settlement_pnl is None:
        return "No previous settlement data"

    pnl = float(last_settlement_pnl)
    trajectory_line = _build_pnl_trajectory(memory_context)

    if pnl < -50:
        core = (
            f"Previous settlement lost {pnl:.2f} bps. "
            "Reflect on whether the last signal overfit momentum, ignored volatility, or carried excessive sizing; "
            "prefer switching or lowering exposure unless current factors strongly disagree."
        )
    elif pnl < 0:
        core = (
            f"Previous settlement lost {pnl:.2f} bps. "
            "Keep the same strategy only if factor alignment improved; otherwise reduce confidence."
        )
    elif pnl > 50:
        core = (
            f"Previous settlement gained {pnl:.2f} bps. "
            "Positive feedback supports continuity, but do not increase risk if volatility or funding is crowded."
        )
    else:
        core = (
            f"Previous settlement was {pnl:.2f} bps. "
            "Outcome was close to flat; favor current factor evidence over inertia."
        )

    if trajectory_line:
        return f"{core} {trajectory_line}"
    return core


def _build_pnl_trajectory(memory_context: dict[str, Any] | None) -> str:
    """基于记忆存储构建 PnL 轨迹描述，用于 Guardrails 连续亏损检测。"""
    if not memory_context:
        return ""

    retrieved = memory_context.get("retrieved", [])
    if not retrieved:
        return ""

    pnl_series = [float(item.get("pnlBps", 0.0)) for item in retrieved]
    consecutive_losses = 0
    for pnl_val in reversed(pnl_series):
        if pnl_val < 0:
            consecutive_losses += 1
        else:
            break

    if consecutive_losses >= 2:
        return (
            f"Guardrails alert: {consecutive_losses}-consecutive-loss streak detected in recent memory. "
            "Strongly recommend switching strategy, reducing confidence to <0.50, "
            "and guarding against overfitting the last factor snapshot."
        )

    avg_recent = sum(pnl_series) / len(pnl_series) if pnl_series else 0.0
    if avg_recent < -25:
        return (
            f"Recent memory trajectory shows negative average PnL ({avg_recent:.1f} bps). "
            "Reflect on systematic bias rather than blaming single-trade variance."
        )
    if avg_recent > 25:
        return (
            f"Recent memory trajectory is positive (avg {avg_recent:.1f} bps). "
            "Positive feedback loop supports continuity, but guard against over-confidence."
        )

    return ""


def _default_alpha_formula(factors: dict[str, float], risk_profile: RiskProfileState) -> str:
    """AlphaGPT 工程化兜底：没有 LLM 时也生成可审计的组合因子公式。"""
    vol_penalty = "0.45" if risk_profile == "conservative" else "0.30"
    funding_penalty = "0.35" if abs(factors.get("funding", 0.0)) > 1.0 else "0.20"
    momentum_weight = "0.55" if risk_profile == "aggressive" else "0.40"
    return (
        f"rank({momentum_weight}*decay_linear(momentum,6) "
        f"+ 0.30*rank(trend) + 0.20*rank(volume_pressure) "
        f"- {funding_penalty}*rank(abs(funding_rate)) "
        f"- {vol_penalty}*rank(realized_volatility))"
    )


def _default_formula_rationale(
    regime: str,
    factors: dict[str, float],
    risk_profile: RiskProfileState,
) -> str:
    """AlphaGPT 公式解释兜底：把公式和当前行情条件绑定。"""
    return (
        f"The generated composite factor blends momentum, trend, volume pressure, funding crowding, "
        f"and realized volatility because the current regime is classified as {regime}. "
        f"Momentum={factors.get('momentum', 0.0):.3f}, trend={factors.get('trend', 0.0):.3f}, "
        f"funding={factors.get('funding', 0.0):.3f}. "
        f"Risk profile is {risk_profile}, so volatility and funding penalties are adjusted before ranking."
    )


def _build_system_prompt(
    factor_summary: dict[str, Any],
    risk_profile: RiskProfileState,
    agent_reputation: dict[str, Any] | None,
    last_settlement_pnl: float | None,
    memory_context: dict[str, Any] | None = None,
    multi_agent_context: dict[str, Any] | None = None,
) -> str:
    """组装超级融合 System Prompt。

    这里不直接调用 LLM，而是把 Prompt 作为策略选择器的可审计输出，
    方便上层多智能体 Orchestrator 或后续 OpenAI 调用复用。
    """
    factor_snapshot = {
        item.get("id"): item.get("score")
        for item in factor_summary.get("factors", [])
        if item.get("score") is not None and not item.get("missing")
    }
    schema = LLMStrategyDecision.model_json_schema()
    prompt_parts = [
        "You are QuantAgent's strategy selection brain for Mantle DeFi trading.",
        "【Base / AlphaGPT Formula Generation】Do not merely choose a strategy. "
        "You must derive one custom alphanumeric composite alpha formula from the current factor_summary, "
        "for example rank(decay_linear(momentum,6)-rank(realized_volatility)), and explain why the formula "
        "is academically plausible under the current market regime.",
        "Return strict JSON matching this schema; do not add markdown or extra prose:",
        json.dumps(schema, ensure_ascii=False),
        "Current factor snapshot:",
        json.dumps(factor_snapshot, ensure_ascii=False, sort_keys=True),
    ]

    score = _extract_reputation_score(agent_reputation)
    if agent_reputation is not None:
        prompt_parts.append(
            "【FinMem On-chain Episodic Memory】"
            f"Current ERC-8004 reputation score is {score if score is not None else 'unknown'}; "
            f"riskProfileState should be {risk_profile}. "
            "If the score is below 3000, choose an extremely conservative or flat strategy. "
            "If the score is above 7000, aggressive high-risk strategies are allowed only when factors agree."
        )

    if last_settlement_pnl is not None:
        prompt_parts.append(
            "【QuantAgent Self-reflection】"
            f"The previous strategy settlement PnL was {float(last_settlement_pnl):.2f} bps. "
            "Deeply reflect on why the prior outcome happened and decide whether the strategy should switch, "
            "continue, or reduce confidence."
        )

    if memory_context:
        adaptive_prompt = memory_context.get("adaptivePrompt")
        if adaptive_prompt:
            prompt_parts.append(
                "【ATLAS Adaptive-OPRO】Use this performance-selected prompt mutation as the active optimization prior:\n"
                + json.dumps(adaptive_prompt, ensure_ascii=False, sort_keys=True)
            )
        prompt_parts.append(
            "【FinMem Retrieved Memories】Use these retrieved settlement memories as episodic evidence. "
            "Prefer strategies that improved reputation under similar factor states and avoid repeating recent loss patterns:\n"
            + json.dumps(memory_context, ensure_ascii=False, sort_keys=True)
        )

    if multi_agent_context:
        prompt_parts.append(
            "【QuantAgent Multi-Agent Reports】Synthesize the indicator, flow, memory, reputation, and risk-critic reports "
            "before finalizing the decision:\n"
            + json.dumps(multi_agent_context, ensure_ascii=False, sort_keys=True)
        )

    return "\n\n".join(prompt_parts)


def _safe_parse_llm_response(raw_payload: Any, defaults: LLMStrategyDecision) -> LLMStrategyDecision:
    """强类型解析 LLM JSON；缺字段或坏字段时安全降级。

    上游可以把 LLM 原始输出放在 factor_summary['llmStrategyDecision']、
    factor_summary['llmResponse'] 或 factor_summary['llm_response'] 中。
    """
    if raw_payload is None:
        return defaults

    try:
        if isinstance(raw_payload, str):
            parsed = json.loads(raw_payload)
        elif isinstance(raw_payload, dict):
            parsed = raw_payload
        else:
            raise TypeError(f"Unsupported LLM payload type: {type(raw_payload).__name__}")
    except (TypeError, json.JSONDecodeError):
        return defaults

    if not isinstance(parsed, dict):
        return defaults

    merged = defaults.model_dump()
    merged.update(parsed)

    try:
        return LLMStrategyDecision.model_validate(merged)
    except ValidationError:
        safe = defaults.model_dump()
        safe.update(
            {
                "strategyId": str(parsed.get("strategyId") or defaults.strategyId),
                "signalDirection": str(parsed.get("signalDirection") or defaults.signalDirection),
                "confidence": parsed.get("confidence", defaults.confidence),
                "topDrivers": parsed.get("topDrivers") if isinstance(parsed.get("topDrivers"), list) else defaults.topDrivers,
                "riskWarnings": parsed.get("riskWarnings") if isinstance(parsed.get("riskWarnings"), list) else defaults.riskWarnings,
                "explanation": str(parsed.get("explanation") or defaults.explanation),
                "alphaFormula": str(parsed.get("alphaFormula") or defaults.alphaFormula),
                "formulaRationale": str(parsed.get("formulaRationale") or defaults.formulaRationale),
                "riskProfileState": parsed.get("riskProfileState") if parsed.get("riskProfileState") in {"aggressive", "neutral", "conservative"} else defaults.riskProfileState,
                "reputationImpact": str(parsed.get("reputationImpact") or defaults.reputationImpact),
                "reflection": str(parsed.get("reflection") or defaults.reflection),
            }
        )
        try:
            return LLMStrategyDecision.model_validate(safe)
        except ValidationError:
            return defaults


def _apply_reputation_guardrails(
    strategy_id: str,
    confidence: float,
    direction: str,
    drivers: list[str],
    warnings: list[str],
    risk_profile: RiskProfileState,
) -> tuple[str, float, str, list[str], list[str]]:
    """FinMem 风险护栏：链上声誉低时强制保守，高时允许略微加风险。"""
    if risk_profile == "conservative":
        strategy_id = "bollinger"
        direction = "neutral"
        confidence = min(confidence, 0.55)
        drivers = [*drivers, "Low on-chain reputation forces conservative capital preservation."]
        warnings = [*warnings, "Reputation score below safety threshold; flat or low-risk posture required."]
    elif risk_profile == "aggressive":
        confidence = min(0.95, confidence + 0.03)
        drivers = [*drivers, "High on-chain reputation allows a larger risk budget when factors align."]
    return strategy_id, round(confidence, 2), direction, drivers[:5], warnings[:5]


def _apply_reflection_guardrails(
    confidence: float,
    drivers: list[str],
    warnings: list[str],
    last_settlement_pnl: float | None,
) -> tuple[float, list[str], list[str]]:
    """QuantAgent 自我反思护栏：上一笔亏损会降低本次置信度。"""
    if last_settlement_pnl is None:
        return confidence, drivers, warnings

    pnl = float(last_settlement_pnl)
    if pnl < -50:
        confidence = max(0.35, confidence - 0.12)
        warnings = [*warnings, "Self-reflection detected a material previous loss; confidence reduced."]
    elif pnl < 0:
        confidence = max(0.4, confidence - 0.05)
        warnings = [*warnings, "Previous settlement was negative; modest confidence haircut applied."]
    elif pnl > 50:
        confidence = min(0.95, confidence + 0.02)
        drivers = [*drivers, "Positive previous settlement supports strategy continuity."]
    return round(confidence, 2), drivers[:5], warnings[:5]


def _memory_context_summary(memory_context: dict[str, Any] | None) -> str:
    if not memory_context:
        return "No retrieved memory context."
    summary = memory_context.get("summary", {})
    retrieved = memory_context.get("retrieved", [])
    if not summary and not retrieved:
        return "No retrieved memory context."
    return (
        f"FinMem store has {summary.get('count', 0)} records, "
        f"avg PnL {summary.get('avgPnlBps', 0.0)} bps, "
        f"latest PnL {summary.get('latestPnlBps')} bps, "
        f"retrieved memories {len(retrieved)}."
    )


def _apply_memory_guardrails(
    confidence: float,
    drivers: list[str],
    warnings: list[str],
    memory_context: dict[str, Any] | None,
) -> tuple[float, list[str], list[str]]:
    if not memory_context:
        return confidence, drivers, warnings

    summary = memory_context.get("summary", {})
    latest_pnl = summary.get("latestPnlBps")
    avg_pnl = float(summary.get("avgPnlBps") or 0.0)
    if latest_pnl is not None and float(latest_pnl) < -50:
        confidence = max(0.35, confidence - 0.08)
        warnings = [*warnings, "FinMem retrieved a recent material loss; additional confidence haircut applied."]
    elif avg_pnl > 25 and summary.get("count", 0) >= 2:
        confidence = min(0.95, confidence + 0.02)
        drivers = [*drivers, "FinMem retrieved positive average settlement memory for this asset."]
    return round(confidence, 2), drivers[:6], warnings[:6]


def _memory_loss_streak(memory_context: dict[str, Any] | None) -> int:
    """FinPos 风控输入：从多时间尺度记忆里读取连续亏损。"""
    if not memory_context:
        return 0
    summary = memory_context.get("summary", {})
    try:
        return int(summary.get("consecutiveLosses") or 0)
    except (TypeError, ValueError):
        return 0


def _build_position_plan(
    *,
    direction: str,
    confidence: float,
    factors: dict[str, float],
    recent_vol: float,
    risk_profile: RiskProfileState,
    memory_context: dict[str, Any] | None,
    risk_warnings: list[str],
) -> dict[str, Any]:
    """FinPos 工程化落点：委托数量与风险决策智能体生成仓位计划。"""
    summary = (memory_context or {}).get("summary", {})
    current_exposure = float(summary.get("currentExposure") or 0.0)
    unrealized_pnl_bps = float(summary.get("unrealizedPnlBps") or 0.0)
    return QuantityRiskDecisionAgent().decide(
        direction=direction,
        confidence=confidence,
        factors=factors,
        recent_volatility=recent_vol,
        risk_profile=risk_profile,
        memory_context=memory_context,
        risk_warnings=risk_warnings,
        current_exposure=current_exposure,
        unrealized_pnl_bps=unrealized_pnl_bps,
    ).to_dict()


def select_strategy(
    symbol: str,
    factor_summary: dict[str, Any],
    ohlcv_df,
    agent_reputation: dict | None = None,
    last_settlement_pnl: float | None = None,
    memory_context: dict[str, Any] | None = None,
    multi_agent_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    factors = _factor_map(factor_summary)
    recent_vol = float(factor_summary.get("recentVolatility24h") or 0.0)
    regime = _classify_regime(factors, recent_vol)
    strategy_id, confidence, drivers = _pick_strategy(regime, factors)
    direction_decision = DirectionDecisionAgent().decide(regime=regime, factors=factors)
    direction = direction_decision.direction
    warnings = _risk_warnings(factors, regime, recent_vol)
    drivers = [*drivers, direction_decision.reasoning][:5]

    # FinMem：把 ERC-8004 链上声誉视作“情节记忆”，直接约束风险偏好。
    risk_profile = _risk_profile_from_reputation(agent_reputation)
    reputation_impact = _reputation_impact(agent_reputation, risk_profile)
    strategy_id, confidence, direction, drivers, warnings = _apply_reputation_guardrails(
        strategy_id,
        confidence,
        direction,
        drivers,
        warnings,
        risk_profile,
    )

    # QuantAgent：把上一次结算结果变成自我反思约束，影响本次置信度。
    reflection = _reflection_from_settlement(last_settlement_pnl, memory_context)
    confidence, drivers, warnings = _apply_reflection_guardrails(
        confidence,
        drivers,
        warnings,
        last_settlement_pnl,
    )
    confidence, drivers, warnings = _apply_memory_guardrails(
        confidence,
        drivers,
        warnings,
        memory_context,
    )

    if multi_agent_context:
        critic_warnings = multi_agent_context.get("riskCriticWarnings", [])
        warnings = [*warnings, *critic_warnings][:8]
        drivers = [*drivers, "QuantAgent multi-agent context synthesized indicator, flow, memory, and reputation reports."][:8]

        # P1-5: RiskCritic 置信度自动调节
        # 当多智能体上下文包含关键风险告警时，自动降低 confidence
        for warn in critic_warnings:
            if "volatility is high" in warn or "cap confidence" in warn:
                confidence = max(0.35, confidence - 0.08)
                drivers = [*drivers, "RiskCritic: volatility override applied, confidence capped."][:8]
            if "funding is crowded" in warn:
                confidence = max(0.35, confidence - 0.05)
                drivers = [*drivers, "RiskCritic: funding crowd override applied, confidence reduced."][:8]
            if "consecutive-loss streak" in warn or "Reflection critic" in warn:
                confidence = max(0.30, confidence - 0.12)
                strategy_id = "reversal_trend" if strategy_id in ("macd_bollinger", "breakout_swing") else "range_mean_reversion"
                drivers = [*drivers, "RiskCritic: consecutive loss override → strategy switched & confidence lowered."][:8]

    policy = build_policy_output(
        factors=factors,
        memory_context=memory_context,
        agent_reputation=agent_reputation,
        action=direction,
        base_confidence=confidence,
    )
    confidence = policy["policyConfidence"]

    bench = STRATEGY_BENCHMARKS[_benchmark_id(strategy_id)]
    regime_key = f"{regime}_sharpe" if f"{regime}_sharpe" in bench else "range_sharpe"
    sharpe = bench.get(regime_key, bench.get("range_sharpe", 0.0))

    benchmark_summary = {
        "regimeSharpe": sharpe,
        "winRate": bench["win_rate"],
        "maxDrawdownPct": bench["max_drawdown_pct"],
        "note": "Historical benchmark from prior QuantAgent/Hummingbot workflow experiments.",
    }
    chart = build_benchmark_chart(ohlcv_df, strategy_id)

    # AlphaGPT：默认生成组合因子公式；若上游 LLM 返回合法 JSON，则覆盖这些学术字段。
    default_decision = LLMStrategyDecision(
        strategyId=strategy_id,
        signalDirection=direction,
        confidence=confidence,
        topDrivers=drivers,
        riskWarnings=warnings,
        explanation="",
        alphaFormula=_default_alpha_formula(factors, risk_profile),
        formulaRationale=_default_formula_rationale(regime, factors, risk_profile),
        riskProfileState=risk_profile,
        reputationImpact=reputation_impact,
        reflection=reflection,
    )
    raw_llm_payload = (
        factor_summary.get("llmStrategyDecision")
        or factor_summary.get("llmResponse")
        or factor_summary.get("llm_response")
    )
    llm_decision = _safe_parse_llm_response(raw_llm_payload, default_decision)

    # 策略 ID 仍以确定性风控结果为主，避免 LLM 返回未知策略导致 benchmark 或执行层崩溃。
    if llm_decision.strategyId in STRATEGIES and risk_profile != "conservative":
        strategy_id = llm_decision.strategyId
        bench = STRATEGY_BENCHMARKS[_benchmark_id(strategy_id)]
        meta = STRATEGIES[strategy_id]
    else:
        meta = STRATEGIES[strategy_id]

    position_plan = _build_position_plan(
        direction=direction,
        confidence=confidence,
        factors=factors,
        recent_vol=recent_vol,
        risk_profile=risk_profile,
        memory_context=memory_context,
        risk_warnings=warnings,
    )

    system_prompt = _build_system_prompt(
        factor_summary=factor_summary,
        risk_profile=risk_profile,
        agent_reputation=agent_reputation,
        last_settlement_pnl=last_settlement_pnl,
        memory_context=memory_context,
        multi_agent_context=multi_agent_context,
    )

    return {
        "symbol": symbol.upper(),
        "modelVersion": MODEL_VERSION,
        "marketRegime": regime,
        "strategyId": strategy_id,
        "strategyName": meta["name"],
        "strategyDescription": meta["description"],
        "signalDirection": direction,
        "confidence": confidence,
        "directionDecision": {
            "schema": "quantagent.direction-decision.v1",
            "direction": direction,
            "regime": regime,
            "reasoning": direction_decision.reasoning,
        },
        "topDrivers": drivers,
        "riskWarnings": warnings,
        "positionPlan": position_plan,
        "policy": policy,
        "policyScore": policy["policyScore"],
        "criticValue": policy["criticValue"],
        "rewardFeatures": policy["rewardFeatures"],
        "benchmarkSummary": benchmark_summary,
        "benchmarkChart": chart,
        "alphaFormula": llm_decision.alphaFormula or default_decision.alphaFormula,
        "formulaRationale": llm_decision.formulaRationale or default_decision.formulaRationale,
        "riskProfileState": risk_profile,
        "reputationImpact": llm_decision.reputationImpact or reputation_impact,
        "reflection": llm_decision.reflection or reflection,
        "memoryContextSummary": _memory_context_summary(memory_context),
        "multiAgentContext": multi_agent_context or {},
        "llmSystemPrompt": system_prompt,
        "llmOutputSchema": LLMStrategyDecision.model_json_schema(),
        "explanation": (
            f"Regime classified as {regime}. {meta['name']} was selected because "
            f"prior benchmark evidence shows stronger workflow fit in this state "
            f"(regime Sharpe {sharpe:.2f}). Confidence {confidence:.0%}. "
            f"Risk profile is {risk_profile}; {reputation_impact}"
        ),
    }
