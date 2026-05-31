"""Register or preview the ERC-8004 Agent Card URI.

This script is intentionally conservative: by default it prints the canonical
Agent Card and required environment variables. When live registry integration is
configured, the on-chain call can be added behind the same input contract.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.api.app.agent_card import build_agent_card  # noqa: E402
from services.api.app.config import AGENT_CARD_BASE_URL, AGENT_URI, PUBLIC_API_BASE_URL  # noqa: E402


def main() -> None:
    base_url = (AGENT_CARD_BASE_URL or os.getenv("PUBLIC_API_BASE_URL") or PUBLIC_API_BASE_URL).rstrip("/")
    if "localhost" in base_url or "127.0.0.1" in base_url:
        raise SystemExit("Refusing to generate a final Agent Card with a localhost base URL.")
    card = build_agent_card(base_url)
    output = {
        "mode": "preview",
        "agentURI": AGENT_URI,
        "agentCardEndpoint": f"{base_url.rstrip('/')}/api/agent/card",
        "card": card,
        "nextSteps": [
            "Upload this Agent Card JSON to IPFS/Arweave or serve it from the public API.",
            "Set AGENT_URI to the resulting public URI.",
            "Use the official ERC-8004 Identity Registry client to register AGENT_URI on Mantle.",
        ],
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
