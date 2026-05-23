from __future__ import annotations

from typing import Any


def _factor_map(factor_summary: dict[str, Any]) -> dict[str, float]:
    return {
        item["id"]: float(item["score"])
        for item in factor_summary.get("factors", [])
        if item.get("score") is not None and not item.get("missing")
    }


def _bias_from_value(value: float, positive: str, negative: str) -> str:
    if value > 0.25:
        return positive
    if value < -0.25:
        return negative
    return "neutral"


def build_agent_context(
    *,
    symbol: str,
    factor_summary: dict[str, Any],
    memory_context: dict[str, Any],
    agent_reputation: dict[str, Any] | None,
) -> dict[str, Any]:
    """QuantAgent 风格多智能体上下文。

    借鉴参考源码里的 indicator/pattern/trend/decision agent 拆分，但保持
    轻量、确定性、可部署。输出会进入 selector 的 prompt 和前端解释层。
    """

    factors = _factor_map(factor_summary)
    momentum = factors.get("momentum", 0.0)
    trend = factors.get("trend", 0.0)
    volatility = abs(factors.get("volatility", 0.0))
    funding = factors.get("funding", 0.0)
    open_interest = factors.get("open_interest", 0.0)
    memory_summary = memory_context.get("summary", {})

    indicator_report = (
        f"Indicator agent: {symbol} momentum is {_bias_from_value(momentum, 'bullish', 'bearish')}; "
        f"trend is {_bias_from_value(trend, 'supportive', 'weak')}; volatility score is {volatility:.3f}."
    )
    flow_report = (
        f"Flow agent: funding score {funding:.3f} and open-interest score {open_interest:.3f}; "
        f"crowding risk is {'elevated' if abs(funding) > 1.0 or open_interest > 1.0 else 'contained'}."
    )
    memory_report = (
        f"Memory agent: {memory_summary.get('count', 0)} stored settlements, "
        f"average PnL {memory_summary.get('avgPnlBps', 0.0)} bps, "
        f"latest PnL {memory_summary.get('latestPnlBps')} bps."
    )

    reputation_score = None
    if isinstance(agent_reputation, dict):
        reputation_score = agent_reputation.get("score")
        if reputation_score is None and isinstance(agent_reputation.get("reputation"), dict):
            reputation_score = agent_reputation["reputation"].get("score")
    reputation_report = (
        f"Reputation agent: ERC-8004 score {reputation_score}/10000."
        if reputation_score is not None
        else "Reputation agent: no on-chain score available; use neutral policy."
    )

    warnings: list[str] = []
    if volatility > 1.5:
        warnings.append("Risk critic: volatility is high; cap confidence and position size.")
    if abs(funding) > 1.0:
        warnings.append("Risk critic: funding is crowded; avoid unhedged directional overreach.")
    if memory_summary.get("latestPnlBps") is not None and memory_summary.get("latestPnlBps", 0) < 0:
        warnings.append("Reflection critic: latest settlement was negative; require stronger confirmation.")
    if not warnings:
        warnings.append("Risk critic: no critical override from deterministic agent graph.")

    return {
        "schema": "quantagent.multi-agent-context.v1",
        "symbol": symbol.upper(),
        "indicatorReport": indicator_report,
        "flowReport": flow_report,
        "memoryReport": memory_report,
        "reputationReport": reputation_report,
        "riskCriticWarnings": warnings,
        "decisionInputs": {
            "momentum": momentum,
            "trend": trend,
            "volatility": volatility,
            "funding": funding,
            "openInterest": open_interest,
            "memoryCount": memory_summary.get("count", 0),
            "latestPnlBps": memory_summary.get("latestPnlBps"),
            "reputationScore": reputation_score,
        },
    }
