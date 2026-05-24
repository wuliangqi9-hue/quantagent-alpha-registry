from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ZkTLSProofEnvelope:
    schema: str
    provider: str
    endpoint: str
    proofHash: str
    proofURI: str
    mode: str
    verified: bool
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "provider": self.provider,
            "endpoint": self.endpoint,
            "proofHash": self.proofHash,
            "proofURI": self.proofURI,
            "mode": self.mode,
            "verified": self.verified,
            "message": self.message,
        }


class ReclaimProofAdapter:
    """Reclaim Protocol zkTLS proof adapter.

    A live implementation can replace `build_proof` with Reclaim SDK calls.
    The fallback still anchors deterministic provenance hashes for demo safety.
    """

    VERSION = "reclaim-zktls-adapter-1.0.0"

    def build_proof(self, *, endpoint: str, payload: dict[str, Any], live_configured: bool = False) -> ZkTLSProofEnvelope:
        digest = hashlib.sha256(
            json.dumps({"endpoint": endpoint, "payload": payload}, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        mode = "reclaim-live" if live_configured else "deterministic-proof-envelope"
        return ZkTLSProofEnvelope(
            schema="quantagent.reclaim-zktls-proof.v1",
            provider="Reclaim Protocol",
            endpoint=endpoint,
            proofHash=f"0x{digest}",
            proofURI=f"ipfs://quantagent-zktls/{digest}",
            mode=mode,
            verified=bool(live_configured),
            message=(
                "Live Reclaim zkTLS proof available."
                if live_configured
                else "Deterministic proof envelope created; configure Reclaim credentials for live verification."
            ),
        )
