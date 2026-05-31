from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages" / "strategy-selector"))

from services.api.app import a2c_adapter  # noqa: E402
from services.api.app.a2c_adapter import run_a2c_training_step  # noqa: E402
from services.api.app.finpos import MultiTimescaleReward  # noqa: E402


def _payload() -> dict:
    return {
        "symbol": "BTC",
        "factorSummary": {
            "factors": [
                {"id": "momentum", "score": 0.4, "missing": False},
                {"id": "trend", "score": 0.2, "missing": False},
                {"id": "volatility", "score": 0.3, "missing": False},
                {"id": "funding", "score": 0.05, "missing": False},
            ]
        },
        "memory": {
            "summary": {
                "latestPnlBps": 12.0,
                "avgPnlBps": 5.0,
                "maxDrawdownBps": -40.0,
                "consecutiveLosses": 0,
            },
            "retrieved": [{"pnlBps": 10.0}, {"pnlBps": -3.0}],
        },
        "selection": {"signalDirection": "long"},
    }


def test_run_a2c_training_step_uses_current_contract(tmp_path) -> None:
    rewards = MultiTimescaleReward(
        immediate_pnl_bps=15.0,
        direction_correct=True,
        medium_window_pnl_bps=25.0,
        exposure_penalty_bps=0.0,
        composite_score=0.33,
    )

    result = run_a2c_training_step(
        symbol="BTC",
        payload=_payload(),
        agent={"reputation": {"score": 7200}},
        finpos_rewards=rewards,
        checkpoint_dir=str(tmp_path),
    )

    assert result is not None
    assert result.get("error") is None
    assert result["symbol"] == "BTC"
    assert result["reward"] == 0.33
    assert len(result["stateVector"]) == 10
    assert result["finposReward"]["composite_score"] is not None


def test_run_a2c_training_step_reports_diagnostic_error(tmp_path, monkeypatch) -> None:
    def broken_state_vector(**_: object) -> dict[str, float]:
        raise TypeError("contract mismatch")

    monkeypatch.setattr(a2c_adapter, "build_state_vector", broken_state_vector)

    result = run_a2c_training_step(
        symbol="BTC",
        payload=_payload(),
        agent={},
        finpos_rewards=object(),
        checkpoint_dir=str(tmp_path),
    )

    assert result is not None
    assert result["schema"] == "quantagent.a2c-training-error.v1"
    assert result["trained"] is False
