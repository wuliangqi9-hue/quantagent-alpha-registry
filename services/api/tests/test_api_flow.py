from __future__ import annotations

from pathlib import Path
import os
import sys
import tempfile

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
TEST_DATA_DIR = Path(tempfile.gettempdir()) / "quantagent-api-tests"
TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MEMORY_STORE_PATH", str(TEST_DATA_DIR / "agent_memory.jsonl"))
os.environ.setdefault("ATLAS_OPRO_STORE_PATH", str(TEST_DATA_DIR / "atlas_opro.jsonl"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages" / "factor-engine"))
sys.path.insert(0, str(ROOT / "packages" / "strategy-selector"))
sys.path.insert(0, str(ROOT / "packages" / "agent-memory"))
sys.path.insert(0, str(ROOT / "packages" / "agent-orchestrator"))

from services.api.app.main import app  # noqa: E402


client = TestClient(app)


def test_health_and_agent_card_contract() -> None:
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    card = client.get("/api/agent/card")
    assert card.status_code == 200
    body = card.json()
    assert body["schema"] == "erc8004.agent-registration-file.v1"
    assert body["agentRegistry"].startswith("eip155:")
    assert "services" in body and len(body["services"]) >= 3
    assert "x402Support" in body
    assert "supportedTrust" in body


def test_offline_demo_flow_for_supported_assets() -> None:
    for symbol in ["BTC", "ETH", "SOL"]:
        analysis = client.post(
            "/api/analyze",
            json={"symbol": symbol, "mode": "offline-demo"},
        )
        assert analysis.status_code == 200, analysis.text
        analysis_body = analysis.json()
        assert analysis_body["symbol"] == symbol
        assert analysis_body["mode"] == "offline-demo"
        assert analysis_body["signalHash"].startswith("0x")
        assert analysis_body["selection"]["policy"]["schema"] == "quantagent.policy-blender.v1"
        assert analysis_body["executionIntent"]["routeDecision"]["schema"] == "quantagent.route-decision.v1"
        assert analysis_body["proofBundle"]["proofBundleHash"].startswith("0x")
        assert analysis_body["erc8004Status"]["identity"]["agentRegistry"].startswith("eip155:")

        record = client.post("/api/record-signal", json={"useLastAnalysis": True})
        assert record.status_code == 200, record.text
        assert record.json()["signalHash"] == analysis_body["signalHash"]

        settle = client.post("/api/settle", json={"useLastAnalysis": True})
        assert settle.status_code == 200, settle.text
        settle_body = settle.json()
        settlement = settle_body["settlement"]
        assert settlement["signalHash"] == analysis_body["signalHash"]
        assert isinstance(settlement["pnlBps"], (int, float))
        assert settlement["teeAttestation"]["attestationHash"].startswith("0x")
        assert settlement["zktlsProof"]["proofHash"].startswith("0x")
        assert settlement["proofBundleHash"].startswith("0x")
        assert settlement["proofBundle"]["proofBundleHash"] == settlement["proofBundleHash"]
        assert settle_body["chain"]["standardReputationFeedback"]["schema"] == "erc8004.reputation-feedback.v1"
