from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .qtmrl import A2CPolicyEngine


# ---------------------------------------------------------------------------
# QuantAgent-inspired shared state (参照 agent_state.py 的 TypedDict 模式)
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class AgentState:
    """QuantAgent 风格多智能体共享状态。

    借鉴参考源码中 IndicatorAgentState / trading_graph 的 TypedDict 设计，
    但改为 dataclass 以保证 hackathon 可部署性和类型安全。
    """

    symbol: str
    factor_summary: dict[str, Any]
    memory_context: dict[str, Any]
    agent_reputation: dict[str, Any] | None

    # 因子引擎完整快照（P1-6：深度打通 Factor Engine → Agent 管线）
    factor_snapshot: dict[str, float] = field(default_factory=dict)

    # 每个 agent 分析完成后填充各自报告
    indicator_report: str = ""
    flow_report: str = ""
    memory_report: str = ""
    reputation_report: str = ""
    risk_warnings: list[str] = field(default_factory=list)

    # 决策输入快照（供下游 selector 或 LLM prompt 使用）
    decision_inputs: dict[str, Any] = field(default_factory=dict)


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


# ---------------------------------------------------------------------------
# 独立的 Agent 类 — 参照 indicator_agent / pattern_agent / trend_agent 拆分
# ---------------------------------------------------------------------------


class IndicatorAgent:
    """技术指标智能体 — 解析动量、趋势、波动率因子并生成人类可读报告。

    参照 indicator_agent.py 的 LLM-tool-calling 模式，但用确定性规则替代 LLM 调用，
    保证 hackathon 离线 demo 稳定运行。
    """

    SLOTS = ("_state",)
    VERSION = "indicator-agent-1.0.0"

    def __init__(self) -> None:
        self._state: AgentState | None = None

    def analyze(self, state: AgentState) -> str:
        self._state = state
        factors = _factor_map(state.factor_summary)
        momentum = factors.get("momentum", 0.0)
        trend = factors.get("trend", 0.0)
        volatility = abs(factors.get("volatility", 0.0))
        sym = state.symbol
        return (
            f"Indicator agent [{self.VERSION}]: {sym} momentum is "
            f"{_bias_from_value(momentum, 'bullish', 'bearish')}; "
            f"trend is {_bias_from_value(trend, 'supportive', 'weak')}; "
            f"volatility score is {volatility:.3f}."
        )


class FlowAgent:
    """资金流向智能体 — 解析 funding rate 和 open interest 拥挤度。

    参照 pattern_agent.py 的专用分析职责，但不引入图像生成管道，
    仅对数值做阈值判断。
    """

    VERSION = "flow-agent-1.0.0"

    def analyze(self, state: AgentState) -> str:
        factors = _factor_map(state.factor_summary)
        funding = factors.get("funding", 0.0)
        open_interest = factors.get("open_interest", 0.0)
        crowding = (
            "elevated" if abs(funding) > 1.0 or open_interest > 1.0 else "contained"
        )
        return (
            f"Flow agent [{self.VERSION}]: funding score {funding:.3f} and "
            f"open-interest score {open_interest:.3f}; crowding risk is {crowding}."
        )


class MemoryAgent:
    """记忆智能体 — 汇总历史结算记录并上报平均/最新 PnL。

    对应 FinMem BrainDB 的查询层，从 memory_context 提取 summary 信息，
    不直接依赖 database 路径。
    """

    VERSION = "memory-agent-1.0.0"

    def analyze(self, state: AgentState) -> str:
        summary = (state.memory_context or {}).get("summary", {})
        return (
            f"Memory agent [{self.VERSION}]: {summary.get('count', 0)} stored "
            f"settlements, average PnL {summary.get('avgPnlBps', 0.0)} bps, "
            f"latest PnL {summary.get('latestPnlBps')} bps."
        )


class ReputationAgent:
    """声誉智能体 — 读取 ERC-8004 链上声誉分数。

    参照 decision_agent 对 agent_reputation 的检查逻辑，
    以确定性方式提取 reputation.score 并生成报告。
    """

    VERSION = "reputation-agent-1.0.0"

    def _extract_score(self, agent_reputation: dict[str, Any] | None) -> int | None:
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
        return score

    def analyze(self, state: AgentState) -> str:
        score = self._extract_score(state.agent_reputation)
        if score is not None:
            return f"Reputation agent [{self.VERSION}]: ERC-8004 score {score}/10000."
        return (
            f"Reputation agent [{self.VERSION}]: no on-chain score available; "
            "use neutral policy."
        )


class RiskCritic:
    """风险评论智能体 — 检查波动率、拥挤度和近期亏损，输出告警列表。

    参照 QuantAgent 决策之前的风险护栏逻辑，
    是最终 decision_agent 的安全层。
    """

    VERSION = "risk-critic-1.0.0"

    def analyze(self, state: AgentState) -> list[str]:
        factors = _factor_map(state.factor_summary)
        volatility = abs(factors.get("volatility", 0.0))
        funding = factors.get("funding", 0.0)
        summary = (state.memory_context or {}).get("summary", {})
        warnings: list[str] = []

        if volatility > 1.5:
            warnings.append(
                "Risk critic: volatility is high; cap confidence and position size."
            )
        if abs(funding) > 1.0:
            warnings.append(
                "Risk critic: funding is crowded; avoid unhedged directional overreach."
            )
        if summary.get("latestPnlBps") is not None and summary.get("latestPnlBps", 0) < 0:
            warnings.append(
                "Reflection critic: latest settlement was negative; require stronger confirmation."
            )
        if not warnings:
            warnings.append(
                "Risk critic: no critical override from deterministic agent graph."
            )

        return warnings


# ---------------------------------------------------------------------------
# Agent Orchestrator — 参照 trading_graph.py 的 multi-agent graph 编排
# ---------------------------------------------------------------------------


class AgentOrchestrator:
    """QuantAgent 风格多智能体编排器。

    顺序执行各 Agent 的分析函数，将结果聚合成统一的
    multi-agent context dict，输出格式与旧版
    `build_agent_context()` 完全兼容。

    参照 trading_graph.py 中的 graph 启动逻辑，
    但用简单的顺序管道替代 LangGraph 状态图，
    以降低 hackathon 依赖复杂度。
    """

    VERSION = "agent-orchestrator-2.0.0"

    def __init__(self) -> None:
        self.indicator = IndicatorAgent()
        self.flow = FlowAgent()
        self.memory = MemoryAgent()
        self.reputation = ReputationAgent()
        self.critic = RiskCritic()
        self.a2c = A2CPolicyEngine()

    def run(
        self,
        *,
        symbol: str,
        factor_summary: dict[str, Any],
        memory_context: dict[str, Any],
        agent_reputation: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """执行完整的多智能体分析管道。"""
        state = AgentState(
            symbol=symbol.upper(),
            factor_summary=factor_summary,
            memory_context=memory_context,
            agent_reputation=agent_reputation,
            factor_snapshot={
                item["id"]: float(item["score"])
                for item in factor_summary.get("factors", [])
                if item.get("score") is not None and not item.get("missing")
            },
        )

        # 依次调用各 Agent
        state.indicator_report = self.indicator.analyze(state)
        state.flow_report = self.flow.analyze(state)
        state.memory_report = self.memory.analyze(state)
        state.reputation_report = self.reputation.analyze(state)
        state.risk_warnings = self.critic.analyze(state)
        a2c_decision = self.a2c.evaluate(
            factor_summary=factor_summary,
            memory_context=memory_context,
        )

        # 聚合决策输入 — P1-6: 包含因子引擎完整元数据
        factors = state.factor_snapshot or _factor_map(factor_summary)
        summary = memory_context.get("summary", {})
        rep_score = self.reputation._extract_score(agent_reputation)
        state.decision_inputs = {
            "momentum": factors.get("momentum", 0.0),
            "trend": factors.get("trend", 0.0),
            "volatility": abs(factors.get("volatility", 0.0)),
            "funding": factors.get("funding", 0.0),
            "openInterest": factors.get("open_interest", 0.0),
            "memoryCount": summary.get("count", 0),
            "latestPnlBps": summary.get("latestPnlBps"),
            "reputationScore": rep_score,
            # Factor Engine 元数据 — 下游可直接消费完整因子上下文
            "factorEngineVersion": factor_summary.get("modelVersion", "unknown"),
            "factorTimestamp": factor_summary.get("latestTimestamp"),
            "recentVolatility24h": factor_summary.get("recentVolatility24h", 0.0),
            "factorCount": len([f for f in factor_summary.get("factors", []) if f.get("score") is not None]),
            "activeFactorColumns": factor_summary.get("rawFactorColumns", []),
            "qtmrlA2C": a2c_decision.to_dict(),
        }

        return {
            "schema": "quantagent.multi-agent-context.v2",
            "symbol": state.symbol,
            "orchestratorVersion": self.VERSION,
            "indicatorReport": state.indicator_report,
            "flowReport": state.flow_report,
            "memoryReport": state.memory_report,
            "reputationReport": state.reputation_report,
            "riskCriticWarnings": state.risk_warnings,
            "decisionInputs": state.decision_inputs,
            "qtmrlA2C": a2c_decision.to_dict(),
            # P1-6: 完整因子引擎快照 — 各下游 Agent 可直接引用
            "factorSnapshot": state.factor_snapshot,
            "factorEngineModelVersion": factor_summary.get("modelVersion"),
        }


# 向后兼容的别名 — 旧调用代码无需改动
_global_orchestrator = AgentOrchestrator()


def build_agent_context(
    *,
    symbol: str,
    factor_summary: dict[str, Any],
    memory_context: dict[str, Any],
    agent_reputation: dict[str, Any] | None,
) -> dict[str, Any]:
    """向后兼容的快捷入口：内部委托给 AgentOrchestrator.run()。

    新代码可以直接实例化 AgentOrchestrator 来复用各 Agent 类。
    """
    return _global_orchestrator.run(
        symbol=symbol,
        factor_summary=factor_summary,
        memory_context=memory_context,
        agent_reputation=agent_reputation,
    )
