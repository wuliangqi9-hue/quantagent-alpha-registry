from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, Field


class AgentReport(BaseModel):
    report: str = Field(min_length=8, max_length=1200)
    confidence: float = Field(ge=0.0, le=1.0)
    numeric_bias: float = Field(ge=-3.0, le=3.0)
    risk_flags: list[str] = Field(default_factory=list, max_length=8)


class LLMUnavailable(RuntimeError):
    pass


class StructuredLLMClient:
    """OpenAI-compatible structured-output client.

    The client uses the official OpenAI Python SDK when OPENAI_API_KEY is
    configured. It returns Pydantic-validated objects so downstream API schemas
    remain stable.
    """

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        self.base_url = os.getenv("OPENAI_BASE_URL", "")

    def configured(self) -> bool:
        return bool(self.api_key)

    def report(
        self,
        *,
        role: str,
        symbol: str,
        factor_summary: dict[str, Any],
        memory_context: dict[str, Any],
        agent_reputation: dict[str, Any] | None,
    ) -> AgentReport:
        if not self.configured():
            raise LLMUnavailable("OPENAI_API_KEY is not configured.")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMUnavailable("Install openai>=1.68.0 to enable structured LLM agents.") from exc

        client_kwargs: dict[str, Any] = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        client = OpenAI(**client_kwargs)
        prompt = (
            "You are a production trading-agent submodule. Return concise, "
            "auditable analysis only. Do not invent on-chain transactions or "
            "credentials. Use the numeric factor summary and memory context."
        )
        payload = {
            "role": role,
            "symbol": symbol,
            "factorSummary": factor_summary,
            "memoryContext": memory_context,
            "agentReputation": agent_reputation,
        }

        completion = client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": str(payload)},
            ],
            response_format=AgentReport,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise LLMUnavailable("OpenAI structured output returned no parsed payload.")
        return parsed


def config_required_report(role: str, symbol: str, factors: dict[str, float]) -> AgentReport:
    signal = sum(factors.values()) / max(len(factors), 1)
    return AgentReport(
        report=(
            f"{role} [{symbol}]: deterministic analyst mode active. Factor evidence "
            "is normalized, scored, and constrained by risk posture before policy blending."
        ),
        confidence=0.42,
        numeric_bias=max(-3.0, min(3.0, signal)),
        risk_flags=["deterministic-analyst-mode"],
    )
