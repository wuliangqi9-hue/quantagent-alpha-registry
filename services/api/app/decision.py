from __future__ import annotations

import hashlib
import json
from typing import Any


def build_decision_report(
    symbol: str,
    mode: str,
    factor_summary: dict[str, Any],
    selection: dict[str, Any],
    data_proof: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema": "quantagent.signal-report.v1",
        "symbol": symbol.upper(),
        "mode": mode,
        "modelVersion": f"{factor_summary.get('modelVersion')}+{selection.get('modelVersion')}",
        "marketRegime": selection["marketRegime"],
        "strategyId": selection["strategyId"],
        "strategyName": selection.get("strategyName"),
        "signalDirection": selection["signalDirection"],
        "confidence": selection["confidence"],
        "factors": factor_summary.get("factors"),
        "topDrivers": selection.get("topDrivers"),
        "riskWarnings": selection.get("riskWarnings"),
        "benchmarkSummary": selection.get("benchmarkSummary"),
        "positionPlan": selection.get("positionPlan"),
        "dataProof": data_proof,
        "timestamp": factor_summary.get("latestTimestamp"),
        "source": {
            "factorEngine": factor_summary.get("modelVersion"),
            "strategySelector": selection.get("modelVersion"),
            "dataMode": mode,
        },
        "limitations": [
            "This report is workflow evidence, not a guaranteed profit claim.",
            "Slippage, fees, and regime shifts can materially change live outcomes.",
        ],
    }


def signal_hash(report: dict[str, Any]) -> str:
    payload = json.dumps(report, sort_keys=True, default=str)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"0x{digest}"
