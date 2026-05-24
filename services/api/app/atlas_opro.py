from __future__ import annotations

import hashlib
import json
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import (
    ATLAS_MAX_ITERATIONS,
    ATLAS_MUTATION_RATE,
    ATLAS_OPRO_ENABLED,
    ATLAS_OPRO_STORE_PATH,
)


# ---------------------------------------------------------------------------
# ATLAS Adaptive-OPRO — 动态提示词优化管道
# ---------------------------------------------------------------------------
# 参考报告第 2.3 节：Adaptive-OPRO 将 Prompt 视为可优化的超参数，
# 在每次 /api/settle 结算时根据 PnL 和随机市场反馈动态生成新的提示词。
# 核心逻辑：
#   1. 维护提示词基因库（Prompt Genome Store）
#   2. 基于性能指标（PnL bps, Sharpe, win-rate）进行选择/变异
#   3. 确保输出动作空间具备"订单感知性"（order-aware）
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------
# 提示词模板基类 — 订单感知动作空间
# ---------------------------------------------------------------

BASE_PROMPT_TEMPLATE = """You are QuantAgent, an autonomous position-aware trading agent operating on the Mantle network.

Current Date: {current_date}
Asset: {symbol}
Mode: {mode}

## Factor Engine Summary
{factors_block}

## Multi-Agent Context
{multi_agent_block}

## Memory & Past Performance
{memory_block}

## Your Task

1. **Directional Reasoning**:
   - Analyze macro regime, on-chain flows, volatility structure, and momentum.
   - Determine the most likely directional bias for the next {horizon}.

2. **Risk & Quantity Decision** (Position-Aware):
   - Current exposure: {current_exposure_pct}%
   - Max allowed slippage: {max_slippage_bps} bps
   - Risk budget remaining: {risk_budget_remaining}%
   - Based on the directional signal AND current position, decide:
     a) Order type: MARKET / LIMIT / OBSERVE
     b) Action: BUY / SELL / HOLD
     c) Size adjustment: {size_adjustment_rule}
     d) Limit price offset (if LIMIT): {limit_price_rule}
     e) Stop-loss placement: {stop_loss_rule}

3. **Execution Routing**:
   - For sizes > 0.5% of estimated pool depth: prefer Byreal RFQ (zero price impact, MEV resistant)
   - For smaller sizes: protected CLMM fallback via private mempool
   - NEVER route through public constant-product AMM directly

4. **Proof & Attestation**:
   - All decisions must be accompanied by a TEE attestation hash
   - Data sources must be verified via zkTLS (Reclaim Protocol)

Output a structured decision in JSON format matching the QuantAgent execution schema.
"""

# ---------------------------------------------------------------
# 可选突变子句（Mutation Operators）
# ---------------------------------------------------------------

MUTATION_OPERATORS: list[dict[str, Any]] = [
    {
        "id": "m001",
        "name": "add_market_microstructure_hint",
        "insert": "\n  **Market Microstructure**: Consider order-book depth imbalance, bid-ask spread, and recent trade size distribution.\n",
    },
    {
        "id": "m002",
        "name": "add_regime_switch_guard",
        "insert": "\n  **Regime Switch Guard**: If volatility regime changed in the last 2 hours, reduce position size by 30%.\n",
    },
    {
        "id": "m003",
        "name": "add_correlation_warning",
        "insert": "\n  **Cross-Asset Correlation**: Check BTC-ETH correlation; if > 0.85, treat signals as amplified rather than independent.\n",
    },
    {
        "id": "m004",
        "name": "add_funding_rate_sensitivity",
        "insert": "\n  **Funding Rate Sensitivity**: If perpetual funding rate exceeds 0.05% (8h), favor the paying side.\n",
    },
    {
        "id": "m005",
        "name": "add_twap_execution_preference",
        "insert": "\n  **TWAP Preference**: For size > 10% of 1h volume, prefer TWAP execution over single-block fill.\n",
    },
    {
        "id": "m006",
        "name": "add_mev_aware_timing",
        "insert": "\n  **MEV-Aware Timing**: Avoid executing in the same block as large mempool transactions; delay if necessary.\n",
    },
    {
        "id": "m007",
        "name": "add_inventory_risk_penalty",
        "insert": "\n  **Inventory Risk Penalty**: If inventory exceeds 50% of risk budget, apply a convex penalty to additional exposure.\n",
    },
    {
        "id": "m008",
        "name": "add_slippage_reversion_rule",
        "insert": "\n  **Slippage Reversion Rule**: After a high-slippage execution, wait for spread normalization before re-entering.\n",
    },
]


# ---------------------------------------------------------------
# 提示词基因组条目
# ---------------------------------------------------------------

@dataclass
class PromptGenome:
    """单条提示词基因组记录。"""

    prompt_id: str
    template: str
    active_mutations: list[str] = field(default_factory=list)
    generation: int = 0
    parent_id: str | None = None
    total_pnl_bps: float = 0.0
    total_settles: int = 0
    total_sharpe: float = 0.0
    win_rate: float = 0.0
    last_used_unix: int = 0
    created_unix: int = 0

    @property
    def avg_pnl_bps(self) -> float:
        if self.total_settles <= 0:
            return 0.0
        return self.total_pnl_bps / self.total_settles

    def apply_mutations(self, operators: list[dict[str, Any]]) -> str:
        """将激活的突变操作符注入模板中。"""
        result = self.template
        for op in operators:
            if op["id"] in self.active_mutations:
                # 在 "## Your Task" 之前插入新指令
                marker = "## Your Task"
                if marker in result:
                    result = result.replace(marker, op["insert"] + "\n" + marker)
                else:
                    result += "\n" + op["insert"]
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "promptId": self.prompt_id,
            "template": self.template,
            "activeMutations": self.active_mutations,
            "generation": self.generation,
            "parentId": self.parent_id,
            "stats": {
                "totalPnlBps": self.total_pnl_bps,
                "totalSettles": self.total_settles,
                "avgPnlBps": self.avg_pnl_bps,
                "totalSharpe": self.total_sharpe,
                "winRate": self.win_rate,
            },
            "lastUsedUnix": self.last_used_unix,
            "createdUnix": self.created_unix,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PromptGenome:
        stats = data.get("stats", {})
        return cls(
            prompt_id=data["promptId"],
            template=data["template"],
            active_mutations=data.get("activeMutations", []),
            generation=data.get("generation", 0),
            parent_id=data.get("parentId"),
            total_pnl_bps=float(stats.get("totalPnlBps", 0)),
            total_settles=int(stats.get("totalSettles", 0)),
            total_sharpe=float(stats.get("totalSharpe", 0)),
            win_rate=float(stats.get("winRate", 0)),
            last_used_unix=int(data.get("lastUsedUnix", 0)),
            created_unix=int(data.get("createdUnix", 0)),
        )


# ---------------------------------------------------------------
# 提示词基因组存储器
# ---------------------------------------------------------------

class OPROGenomeStore:
    """基于 JSONL 文件的提示词基因库。

    负责持久化存储、检索和更新提示词基因组。
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or ATLAS_OPRO_STORE_PATH
        self._genomes: dict[str, PromptGenome] = {}
        self._active_prompt_id: str | None = None
        self._load()

    # ---------- 持久化 ----------

    def _load(self) -> None:
        if not self._path.exists():
            return
        with open(self._path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    genome = PromptGenome.from_dict(json.loads(line))
                    self._genomes[genome.prompt_id] = genome
                except (json.JSONDecodeError, KeyError):
                    continue

    def _persist(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            for genome in self._genomes.values():
                f.write(json.dumps(genome.to_dict(), ensure_ascii=False) + "\n")

    # ---------- 核心操作 ----------

    def get_active(self) -> PromptGenome:
        """返回当前活跃的提示词基因组，若不存在则创建默认。"""
        if self._active_prompt_id and self._active_prompt_id in self._genomes:
            return self._genomes[self._active_prompt_id]
        return self._create_default()

    def _create_default(self) -> PromptGenome:
        genome = PromptGenome(
            prompt_id=_gen_prompt_id("default", 0),
            template=BASE_PROMPT_TEMPLATE,
            active_mutations=[],
            generation=0,
            created_unix=int(time.time()),
        )
        self._genomes[genome.prompt_id] = genome
        self._active_prompt_id = genome.prompt_id
        self._persist()
        return genome

    def update_from_settlement(
        self,
        *,
        prompt_id: str | None,
        prompt_template: str | None,
        pnl_bps: float,
    ) -> None:
        """基于单次结算结果更新基因组统计。"""
        target_id = prompt_id or self._active_prompt_id
        if not target_id or target_id not in self._genomes:
            return

        genome = self._genomes[target_id]
        genome.total_settles += 1
        genome.total_pnl_bps += pnl_bps
        genome.win_rate = (
            (genome.win_rate * (genome.total_settles - 1) + (1.0 if pnl_bps > 0 else 0.0))
            / genome.total_settles
        )
        genome.last_used_unix = int(time.time())

        if prompt_template and prompt_template != genome.template:
            genome.template = prompt_template

        self._persist()

    def trigger_adaptation(
        self,
        *,
        market_feedback: dict[str, Any] | None = None,
    ) -> PromptGenome | None:
        """触发一次 Adaptive-OPRO 演化周期。

        基于历史性能数据，选择最优基因组并通过突变生成新一代。
        """
        if not ATLAS_OPRO_ENABLED:
            return None

        feedback = market_feedback or {}

        # 1. 筛选有足够样本的基因组（至少 3 次结算）
        candidates = [g for g in self._genomes.values() if g.total_settles >= 3]
        if not candidates:
            return None

        # 2. 按平均 PnL 排序
        candidates.sort(key=lambda g: g.avg_pnl_bps, reverse=True)

        # 3. 选择表现最优的作为父代（或随机从 top 3 中选择一个）
        top_n = min(3, len(candidates))
        parent = random.choice(candidates[:top_n]) if top_n > 1 else candidates[0]

        # 4. 确定变异的突变算子
        current_mutations = set(parent.active_mutations)
        available_new = [op for op in MUTATION_OPERATORS if op["id"] not in current_mutations]
        available_remove = [op for op in MUTATION_OPERATORS if op["id"] in current_mutations]

        new_mutations = set(parent.active_mutations)

        # 受市场反馈影响的加权选择
        regime = feedback.get("regime", "normal")
        volatility_mult = feedback.get("volatilityMultiplier", 1.0)

        # 在高波动环境中，更倾向于添加风控相关的突变
        if volatility_mult > 1.5:
            risk_ops = [op for op in available_new if "risk" in op["name"] or "guard" in op["name"]]
            if risk_ops and random.random() < ATLAS_MUTATION_RATE * 2:
                chosen = random.choice(risk_ops)
                new_mutations.add(chosen["id"])

        # 标准突变：随机添加或移除
        for op in MUTATION_OPERATORS:
            if random.random() < ATLAS_MUTATION_RATE:
                if op["id"] in new_mutations:
                    new_mutations.discard(op["id"])
                else:
                    new_mutations.add(op["id"])

        # 5. 限制最大突变数量
        if len(new_mutations) > 5:
            new_mutations = set(random.sample(list(new_mutations), 5))

        # 6. 生成新一代基因组
        new_gen = parent.generation + 1
        if new_gen > ATLAS_MAX_ITERATIONS:
            return None  # 已达最大演化代数

        child = PromptGenome(
            prompt_id=_gen_prompt_id("gen", new_gen),
            template=parent.template,
            active_mutations=list(new_mutations),
            generation=new_gen,
            parent_id=parent.prompt_id,
            created_unix=int(time.time()),
        )

        self._genomes[child.prompt_id] = child
        self._active_prompt_id = child.prompt_id
        self._persist()

        return child

    def get_rendered_prompt(
        self,
        *,
        genome: PromptGenome | None = None,
        context: dict[str, Any],
    ) -> str:
        """将基因组与运行时上下文融合，生成最终提示词。"""
        genome = genome or self.get_active()
        template = genome.active_mutations and genome.apply_mutations(MUTATION_OPERATORS) or genome.template

        # 填充运行时上下文
        factors_block = context.get("factors_block", "")
        multi_agent_block = context.get("multi_agent_block", "")
        memory_block = context.get("memory_block", "")

        return template.format(
            current_date=context.get("current_date", time.strftime("%Y-%m-%d %H:%M:%S UTC")),
            symbol=context.get("symbol", "BTC"),
            mode=context.get("mode", "live"),
            factors_block=factors_block,
            multi_agent_block=multi_agent_block,
            memory_block=memory_block,
            horizon=context.get("horizon", "the next 4-hour window"),
            current_exposure_pct=context.get("current_exposure_pct", 0.0),
            max_slippage_bps=context.get("max_slippage_bps", 100),
            risk_budget_remaining=context.get("risk_budget_remaining", 100),
            size_adjustment_rule=context.get(
                "size_adjustment_rule",
                "Scale size linearly with confidence, capped at risk budget",
            ),
            limit_price_rule=context.get(
                "limit_price_rule",
                "Place limit order at (mid - 0.1% * spread) for buys, (mid + 0.1% * spread) for sells",
            ),
            stop_loss_rule=context.get(
                "stop_loss_rule",
                "Set stop-loss at 2 ATR below entry; trail by 1 ATR after 1% profit",
            ),
        )

    def summary(self) -> dict[str, Any]:
        active = self.get_active() if self._genomes else None
        return {
            "enabled": ATLAS_OPRO_ENABLED,
            "totalGenomes": len(self._genomes),
            "activePromptId": self._active_prompt_id,
            "activeGeneration": active.generation if active else 0,
            "activeMutations": active.active_mutations if active else [],
            "topPerformers": sorted(
                [g.to_dict() for g in self._genomes.values() if g.total_settles >= 3],
                key=lambda d: d["stats"]["avgPnlBps"],
                reverse=True,
            )[:5],
        }


# ---------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------

def _gen_prompt_id(prefix: str, generation: int) -> str:
    """生成唯一的提示词 ID。"""
    raw = f"{prefix}:{generation}:{time.time_ns()}:{random.getrandbits(32)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


# ---------------------------------------------------------------
# 模块级单例
# ---------------------------------------------------------------

_opro_store: OPROGenomeStore | None = None


def get_opro_store() -> OPROGenomeStore:
    global _opro_store
    if _opro_store is None:
        _opro_store = OPROGenomeStore()
    return _opro_store


def opro_status() -> dict[str, Any]:
    return get_opro_store().summary()


def trigger_opro_adaptation(
    market_feedback: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    store = get_opro_store()
    child = store.trigger_adaptation(market_feedback=market_feedback)
    if child is None:
        return None
    return {
        "schema": "quantagent.atlas-opro-adaptation.v1",
        "iteration": child.generation,
        "promptId": child.prompt_id,
        "mutations": child.active_mutations,
        "performanceDelta": float((market_feedback or {}).get("pnlBps", 0.0)),
        "selectedTemplate": child.template,
        "rationale": "Adaptive-OPRO selected a new prompt genome from settlement feedback.",
        "adapted": True,
        "newPromptId": child.prompt_id,
        "generation": child.generation,
        "parentId": child.parent_id,
        "newMutations": child.active_mutations,
    }
