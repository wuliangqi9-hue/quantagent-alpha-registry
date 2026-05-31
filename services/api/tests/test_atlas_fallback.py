from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from services.api.app.routers.signal import _dedup_prompt_append  # noqa: E402


def test_dedup_prompt_append_does_not_repeat_clause() -> None:
    prompt = "Prioritize risk control."
    clause = "Loss-window score -0.1000: reduce exposure."
    once = _dedup_prompt_append(prompt, clause)
    twice = _dedup_prompt_append(once, clause)

    assert twice.count(clause) == 1


def test_dedup_prompt_append_caps_length() -> None:
    prompt = "x" * 4000
    result = _dedup_prompt_append(prompt, "reduce exposure", max_chars=100)

    assert len(result) <= 100
