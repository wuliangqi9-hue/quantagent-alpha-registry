from __future__ import annotations

import hashlib
import json
from typing import Any


SCHEMA = "quantagent.proof-bundle.v1"


def stable_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return f"0x{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def build_proof_bundle(
    *,
    decision_report: dict[str, Any],
    data_proof: dict[str, Any] | None,
    execution_intent: dict[str, Any],
    route_decision: dict[str, Any] | None = None,
    tee_attestation: dict[str, Any] | None = None,
    zktls_proof: dict[str, Any] | None = None,
    settlement: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the canonical proof bundle tying data, decision, execution, and settlement."""
    decision_hash = decision_report.get("signalHash") or stable_hash(decision_report)
    bundle = {
        "schema": SCHEMA,
        "decisionReportHash": decision_hash,
        "dataProof": data_proof,
        "teeAttestation": tee_attestation,
        "zktlsProof": zktls_proof,
        "executionIntent": execution_intent,
        "routeDecision": route_decision,
        "settlementHash": settlement.get("settlementHash") if settlement else None,
        "signalHash": decision_hash,
        "symbol": decision_report.get("symbol"),
        "mode": decision_report.get("mode"),
        "messages": [
            "Decision report hash binds strategy reasoning and factor inputs.",
            "Data proof anchors the market-data provenance path.",
            "TEE and zkTLS fields can run in simulated or live verification mode.",
            "Execution route explains slippage and MEV posture before any transaction.",
        ],
    }
    bundle["proofBundleHash"] = proof_bundle_hash(bundle)
    return bundle


def proof_bundle_hash(bundle: dict[str, Any]) -> str:
    payload = {key: value for key, value in bundle.items() if key != "proofBundleHash"}
    return stable_hash(payload)
