from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class PromptVariant:
    """ATLAS Adaptive-OPRO prompt variant record."""

    id: str
    template: str
    created_at: float
    source: str
    uses: int = 0
    avg_pnl_bps: float = 0.0
    last_pnl_bps: float = 0.0


class AdaptiveOPROStore:
    """Performance-driven prompt optimizer for noisy trading rewards.

    The implementation is deterministic by default, with a clear seam for an
    LLM mutation backend once credentials are available.
    """

    DEFAULT_TEMPLATE = (
        "Prioritize position-aware decisions, explicit slippage guards, "
        "multi-timescale reward feedback, and reputation preservation."
    )

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def best_variant(self) -> PromptVariant:
        variants = self.load()
        if not variants:
            return PromptVariant(
                id="atlas-default",
                template=self.DEFAULT_TEMPLATE,
                created_at=time.time(),
                source="default",
            )
        variants.sort(key=lambda item: (item.avg_pnl_bps, item.last_pnl_bps, item.uses), reverse=True)
        return variants[0]

    def update_from_settlement(self, *, prompt_id: str | None, prompt_template: str | None, pnl_bps: float) -> PromptVariant:
        variants = self.load()
        target_id = prompt_id or "atlas-default"
        target = next((item for item in variants if item.id == target_id), None)
        if target is None:
            target = PromptVariant(
                id=target_id,
                template=prompt_template or self.DEFAULT_TEMPLATE,
                created_at=time.time(),
                source="settlement",
            )
            variants.append(target)

        total = target.avg_pnl_bps * target.uses + pnl_bps
        target.uses += 1
        target.avg_pnl_bps = round(total / target.uses, 4)
        target.last_pnl_bps = round(pnl_bps, 4)

        if pnl_bps < -50:
            variants.append(self._mutate(target, "defensive-loss-recovery"))
        elif pnl_bps > 50:
            variants.append(self._mutate(target, "continuation-winner"))

        self._write(variants[-12:])
        return target

    def load(self) -> list[PromptVariant]:
        if not self.path.exists():
            return []
        variants: list[PromptVariant] = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    variants.append(PromptVariant(**json.loads(line)))
                except (TypeError, json.JSONDecodeError):
                    continue
        return variants

    def _mutate(self, base: PromptVariant, source: str) -> PromptVariant:
        if source == "defensive-loss-recovery":
            suffix = " After losses, require lower exposure, stricter stop-loss, and RFQ/protected routing."
        else:
            suffix = " After wins, allow continuity only if volatility and funding remain uncrowded."
        return PromptVariant(
            id=f"atlas-{int(time.time() * 1000)}-{source}",
            template=f"{base.template}{suffix}",
            created_at=time.time(),
            source=source,
        )

    def _write(self, variants: list[PromptVariant]) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            for item in variants:
                f.write(json.dumps(asdict(item), ensure_ascii=False, sort_keys=True))
                f.write("\n")
