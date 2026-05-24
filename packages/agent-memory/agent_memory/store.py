from __future__ import annotations

import json
import math
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class MemoryRecord:
    """FinMem 风格的轻量记忆条目。

    生产实现不直接依赖参考源码，而是吸收 FinMem 的核心思想：
    用 recency、importance、相似度和收益冲击对历史情节排序。
    """

    timestamp: float
    symbol: str
    signal_hash: str
    strategy_id: str
    direction: str
    pnl_bps: float
    confidence: float
    score: int
    market_regime: str
    alpha_formula: str
    risk_profile_state: str
    reflection: str
    factor_snapshot: dict[str, float] = field(default_factory=dict)
    reputation_score: float | None = None

    @classmethod
    def from_analysis(
        cls,
        analysis: dict[str, Any],
        settlement: dict[str, Any],
        *,
        reputation_score: float | None = None,
    ) -> "MemoryRecord":
        selection = analysis.get("selection", {})
        factors = analysis.get("factorSummary", {}).get("factors", [])
        factor_snapshot = {
            item.get("id"): float(item.get("score"))
            for item in factors
            if item.get("id") and item.get("score") is not None and not item.get("missing")
        }
        return cls(
            timestamp=time.time(),
            symbol=str(analysis.get("symbol") or settlement.get("symbol") or "").upper(),
            signal_hash=str(analysis.get("signalHash") or settlement.get("signalHash") or ""),
            strategy_id=str(selection.get("strategyId") or ""),
            direction=str(selection.get("signalDirection") or settlement.get("direction") or "neutral"),
            pnl_bps=float(settlement.get("pnlBps") or 0.0),
            confidence=float(selection.get("confidence") or settlement.get("confidence") or 0.0),
            score=int(settlement.get("score") or 0),
            market_regime=str(selection.get("marketRegime") or ""),
            alpha_formula=str(selection.get("alphaFormula") or ""),
            risk_profile_state=str(selection.get("riskProfileState") or "neutral"),
            reflection=str(selection.get("reflection") or "No previous settlement data"),
            factor_snapshot=factor_snapshot,
            reputation_score=reputation_score,
        )


class AgentMemoryStore:
    """JSONL memory store inspired by FinMem, built for hackathon reliability."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: MemoryRecord) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(record), ensure_ascii=False, sort_keys=True))
            f.write("\n")

    def load(self, symbol: str | None = None, limit: int | None = None) -> list[MemoryRecord]:
        if not self.path.exists():
            return []

        records: list[MemoryRecord] = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    record = MemoryRecord(**data)
                except (TypeError, json.JSONDecodeError):
                    continue
                if symbol and record.symbol != symbol.upper():
                    continue
                records.append(record)

        records.sort(key=lambda item: item.timestamp, reverse=True)
        return records[:limit] if limit else records

    def latest_pnl(self, symbol: str | None = None) -> float | None:
        records = self.load(symbol=symbol, limit=1)
        if not records:
            return None
        return records[0].pnl_bps

    def retrieve(
        self,
        *,
        symbol: str,
        factor_snapshot: dict[str, float],
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        now = time.time()
        scored: list[tuple[float, MemoryRecord, dict[str, float]]] = []
        for record in self.load(symbol=symbol):
            components = self._score_components(record, factor_snapshot, now)
            total = sum(components.values())
            scored.append((total, record, components))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "symbol": record.symbol,
                "signalHash": record.signal_hash,
                "strategyId": record.strategy_id,
                "direction": record.direction,
                "pnlBps": record.pnl_bps,
                "confidence": record.confidence,
                "marketRegime": record.market_regime,
                "alphaFormula": record.alpha_formula,
                "riskProfileState": record.risk_profile_state,
                "reflection": record.reflection,
                "reputationScore": record.reputation_score,
                "memoryScore": round(total, 4),
                "scoreComponents": {key: round(value, 4) for key, value in components.items()},
            }
            for total, record, components in scored[:limit]
        ]

    def summary(self, symbol: str | None = None) -> dict[str, Any]:
        records = self.load(symbol=symbol)
        if not records:
            return {
                "count": 0,
                "avgPnlBps": 0.0,
                "winRate": 0.0,
                "latestPnlBps": None,
                "lastReflection": "No previous settlement data",
            }

        avg_pnl = sum(item.pnl_bps for item in records) / len(records)
        wins = sum(1 for item in records if item.pnl_bps > 0)
        return {
            "count": len(records),
            "avgPnlBps": round(avg_pnl, 4),
            "winRate": round(wins / len(records), 4),
            "latestPnlBps": records[0].pnl_bps,
            "lastReflection": records[0].reflection,
            "lastStrategyId": records[0].strategy_id,
        }

    def _score_components(
        self,
        record: MemoryRecord,
        current_factors: dict[str, float],
        now: float,
    ) -> dict[str, float]:
        """FinMem 增强评分引擎。

        四维度记忆评分：
        - recency：指数衰减窗口（半衰期 72h）
        - importance：PnL 驱动的自适应重要性（组合绝对 PnL + 方向正确性）
        - similarity：余弦相似度（降至 0.65 以提升语义区分度）
        - pnlImpact：收益冲击（非线性 soft-sign 代替线性裁剪）
        """
        age_hours = max(0.0, (now - record.timestamp) / 3600)
        # 指数衰减，半衰期 72h
        recency = math.exp(-age_hours * math.log(2) / 72)

        # 自适应重要性：绝对 PnL + 方向正确性奖励
        abs_pnl_norm = min(1.0, abs(record.pnl_bps) / 200)
        direction_correct = 1.0 if record.pnl_bps > 0 else 0.0
        importance = 0.7 * abs_pnl_norm + 0.3 * direction_correct

        # 非线性收益冲击（soft-sign 替代线性裁剪）
        pnl_impact = math.tanh(record.pnl_bps / 150)

        # 余弦相似度：降至 0.65 放大语义差异
        similarity = self._cosine_similarity(record.factor_snapshot, current_factors)
        similarity_weighted = similarity * max(0.65, similarity)

        return {
            "recency": recency,
            "importance": importance,
            "similarity": similarity_weighted,
            "pnlImpact": pnl_impact,
        }

    @staticmethod
    def _cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
        keys = sorted(set(left) & set(right))
        if not keys:
            return 0.0
        dot = sum(left[key] * right[key] for key in keys)
        left_norm = math.sqrt(sum(left[key] ** 2 for key in keys))
        right_norm = math.sqrt(sum(right[key] ** 2 for key in keys))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return max(-1.0, min(1.0, dot / (left_norm * right_norm)))
