from __future__ import annotations

from pathlib import Path
import os
import sys
import tempfile
from unittest.mock import patch

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
    "ONCHAIN_WRITE_AUTH_TOKEN",
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


client = TestClient(app)


def _analyze_offline(symbol: str = "BTC") -> dict:
    response = client.post("/api/analyze", json={"symbol": symbol, "mode": "offline-demo"})
    assert response.status_code == 200, response.text
    return response.json()


def test_memory_endpoint_hides_store_path() -> None:
    response = client.get("/api/memory")
    assert response.status_code == 200
    assert "storePath" not in response.json()


def test_api_gas_mirror() -> None:
    response = client.get("/api/gas")
    assert response.status_code == 200
    body = response.json()
    assert "network" in body


def test_auto_mode_offline_fallback_mode_label() -> None:
    with patch("services.api.app.data_loader.fetch_binance_klines", side_effect=RuntimeError("binance down")):
        response = client.post("/api/analyze", json={"symbol": "BTC", "mode": "auto"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mode"] == "offline-fallback"
    assert body["dataProof"]["verificationStatus"] == "deterministic-envelope"


def test_settle_preserves_settlement_when_proof_bundle_fails() -> None:
    analysis = _analyze_offline()
    with patch("services.api.app.routers.signal.build_proof_bundle", side_effect=RuntimeError("bundle failed")):
        response = client.post(
            "/api/settle",
            json={
                "useLastAnalysis": True,
                "analysisId": analysis["analysisId"],
                "signalHash": analysis["signalHash"],
            },
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["settlement"]["signalHash"] == analysis["signalHash"]
    assert isinstance(body["settlement"]["pnlBps"], (int, float))
    assert body["settlement"]["teeAttestation"]["attestationHash"].startswith("0x")
    assert body["settlement"]["proofBundleError"]["code"] == "proof-bundle-failed"
    assert body["chain"]["standardReputationFeedback"]["schema"] == "erc8004.reputation-feedback.v1"


def test_settle_returns_502_but_preserves_settlement_on_chain_failure(monkeypatch) -> None:
    analysis = _analyze_offline()
    monkeypatch.setattr("services.api.app.routers.signal.CHAIN_CONFIGURED", True)
    monkeypatch.setattr(
        "services.api.app.routers.signal._require_onchain_write_authorized",
        lambda *args, **kwargs: None,
    )

    async def _boom(*args, **kwargs):
        raise RuntimeError("rpc unavailable")

    monkeypatch.setattr("services.api.app.routers.signal._submit_reputation_feedback_async", _boom)
    response = client.post(
        "/api/settle",
        json={
            "useLastAnalysis": True,
            "analysisId": analysis["analysisId"],
            "signalHash": analysis["signalHash"],
        },
    )
    assert response.status_code == 502, response.text
    body = response.json()
    assert body["settlement"]["signalHash"] == analysis["signalHash"]
    assert body["chain"]["proofMode"] == "onchain-attempt-failed"
    assert "proofBundleHash" in body["settlement"]


def test_reclaim_claim_hash_uses_demo_prefix_when_simulated(monkeypatch) -> None:
    import services.api.app.reclaim as reclaim

    real_import = __import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "web3":
            raise ImportError("forced missing web3")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", fake_import)
    simulated = reclaim._keccak_256(b"claim", simulated=True)
    assert simulated == reclaim.hashlib.sha256(b"quantagent-simulated-claim:claim").digest()
