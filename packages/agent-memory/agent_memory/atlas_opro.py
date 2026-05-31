from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class PromptMutations(BaseModel):
    variants: list[str] = Field(min_length=3, max_length=3)
    rationale: str = Field(min_length=8, max_length=1200)


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

    def update_from_settlement(
        self,
        *,
        prompt_id: str | None,
        prompt_template: str | None,
        pnl_bps: float,
        history: list[dict[str, Any]] | None = None,
    ) -> PromptVariant:
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

        if pnl_bps < 0:
            variants.extend(self._llm_mutations(target, pnl_bps=pnl_bps, history=history or []))
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
                line = line.strip()
                if not line:
                    continue
                try:
                    variants.append(PromptVariant(**json.loads(line)))
                except (TypeError, json.JSONDecodeError, ValueError):
                    continue
        return variants

    def append_variant(self, template: str, *, source: str = "external-adaptive-engine") -> PromptVariant:
        variant = PromptVariant(
            id=f"atlas-{int(time.time() * 1000)}-{source}",
            template=template,
            created_at=time.time(),
            source=source,
        )
        variants = self.load()
        variants.append(variant)
        self._write(variants[-12:])
        return variant

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

    def _llm_mutations(
        self,
        base: PromptVariant,
        *,
        pnl_bps: float,
        history: list[dict[str, Any]],
    ) -> list[PromptVariant]:
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            return [
                self._mutate(base, "defensive-loss-recovery"),
                PromptVariant(
                    id=f"atlas-{int(time.time() * 1000)}-volatility-penalty",
                    template=f"{base.template} Loss reflection: penalize high volatility and reduce exposure until short-window reward recovers.",
                    created_at=time.time(),
                    source="config-required-deterministic",
                ),
                PromptVariant(
                    id=f"atlas-{int(time.time() * 1000)}-liquidity-check",
                    template=f"{base.template} Loss reflection: require liquidity depth, gas, and slippage checks before any directional increase.",
                    created_at=time.time(),
                    source="config-required-deterministic",
                ),
            ]
        try:
            from openai import OpenAI
        except ImportError:
            return [self._mutate(base, "defensive-loss-recovery")]

        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if os.getenv("OPENAI_BASE_URL"):
            client_kwargs["base_url"] = os.getenv("OPENAI_BASE_URL")
        client = OpenAI(**client_kwargs)
        model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        payload = {
            "basePrompt": base.template,
            "latestPnlBps": pnl_bps,
            "history": history[-12:],
        }
        parsed = client.beta.chat.completions.parse(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Generate exactly three concise system-prompt variants for a trading agent after a loss. Do not claim guaranteed profits.",
                },
                {"role": "user", "content": json.dumps(payload, sort_keys=True, default=str)},
            ],
            response_format=PromptMutations,
        ).choices[0].message.parsed
        if parsed is None:
            return [self._mutate(base, "defensive-loss-recovery")]
        now = int(time.time() * 1000)
        return [
            PromptVariant(
                id=f"atlas-{now}-{idx}",
                template=variant,
                created_at=time.time(),
                source="openai-structured-opro",
            )
            for idx, variant in enumerate(parsed.variants, start=1)
        ]

    def _write(self, variants: list[PromptVariant]) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            for item in variants:
                data = asdict(item)
                data["template"] = str(data.get("template", "")).replace("\r\n", "\n").replace("\r", "\n")
                f.write(json.dumps(data, ensure_ascii=False, sort_keys=True))
                f.write("\n")
