from __future__ import annotations

from pathlib import Path
import os
import sys
import tempfile
import subprocess

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
TEST_DATA_DIR = Path(tempfile.gettempdir()) / "quantagent-api-tests"
TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
os.environ["QUANTAGENT_SKIP_DOTENV"] = "true"
for secret_key in (
    "MANTLE_PRIVATE_KEY",
    "SIGNAL_REGISTRY_ADDRESS",
    "MANTLE_ENABLE_ONCHAIN_WRITES",
    "AGENT_ID",
):
    os.environ.pop(secret_key, None)
os.environ.setdefault("MEMORY_STORE_PATH", str(TEST_DATA_DIR / "agent_memory.jsonl"))
os.environ.setdefault("ATLAS_OPRO_STORE_PATH", str(TEST_DATA_DIR / "atlas_opro.jsonl"))
os.environ.setdefault("ANALYSIS_SESSION_DIR", str(TEST_DATA_DIR / "analysis_sessions"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages" / "factor-engine"))
sys.path.insert(0, str(ROOT / "packages" / "strategy-selector"))
sys.path.insert(0, str(ROOT / "packages" / "agent-memory"))
sys.path.insert(0, str(ROOT / "packages" / "agent-orchestrator"))

from services.api.app.main import app  # noqa: E402
from services.api.app.byreal_router import calculate_cvar_limit  # noqa: E402


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


def test_byreal_perps_cvar_limit_endpoint() -> None:
    assert calculate_cvar_limit(1000.0) == 80.0

    response = client.get("/api/byreal/perps/cvar-limit", params={"capital": 1000})
    assert response.status_code == 200
    body = response.json()
    assert body["capital"] == 1000.0
    assert body["maxExposure"] == 80.0


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
        assert analysis_body["analysisId"]
        assert analysis_body["signalHash"].startswith("0x")
        assert analysis_body["selection"]["policy"]["schema"] == "quantagent.policy-blender.v1"
        assert analysis_body["executionIntent"]["routeDecision"]["schema"] == "quantagent.route-decision.v1"
        assert analysis_body["proofBundle"]["proofBundleHash"].startswith("0x")
        assert analysis_body["erc8004Status"]["identity"]["agentRegistry"].startswith("eip155:")

        record = client.post(
            "/api/record-signal",
            json={
                "useLastAnalysis": True,
                "analysisId": analysis_body["analysisId"],
                "signalHash": analysis_body["signalHash"],
            },
        )
        if os.getenv("SIGNAL_REGISTRY_ADDRESS") and os.getenv("MANTLE_PRIVATE_KEY"):
            assert record.status_code == 200, record.text
            assert record.json()["signalHash"] == analysis_body["signalHash"]
        else:
            assert record.status_code == 503, record.text
            assert record.json()["detail"]["code"] == "mantle-config-required"

        settle = client.post(
            "/api/settle",
            json={
                "useLastAnalysis": True,
                "analysisId": analysis_body["analysisId"],
                "signalHash": analysis_body["signalHash"],
            },
        )
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


def test_analysis_session_rejects_signal_hash_mismatch() -> None:
    analysis = client.post("/api/analyze", json={"symbol": "BTC", "mode": "offline-demo"})
    assert analysis.status_code == 200, analysis.text
    body = analysis.json()

    settle = client.post(
        "/api/settle",
        json={
            "useLastAnalysis": True,
            "analysisId": body["analysisId"],
            "signalHash": "0x" + "11" * 32,
        },
    )
    assert settle.status_code == 409


def test_api_imports_from_services_api_workdir() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import app.main; print('ok')"],
        cwd=ROOT / "services" / "api",
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
