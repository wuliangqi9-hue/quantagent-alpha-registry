from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SAMPLE_DIR = ROOT / "data" / "sample"
FACTOR_ENGINE_DIR = ROOT / "packages" / "factor-engine"
STRATEGY_SELECTOR_DIR = ROOT / "packages" / "strategy-selector"

MANTLE_RPC_URL = os.getenv("MANTLE_RPC_URL", "https://rpc.sepolia.mantle.xyz")
PRIVATE_MEMPOOL_RPC_URL = os.getenv(
    "PRIVATE_MEMPOOL_RPC_URL",
    os.getenv("MANTLE_PRIVATE_MEMPOOL_RPC_URL", ""),
)
EFFECTIVE_MANTLE_RPC_URL = PRIVATE_MEMPOOL_RPC_URL or MANTLE_RPC_URL
MANTLE_CHAIN_ID = int(os.getenv("MANTLE_CHAIN_ID", "5003"))
CONTRACT_ADDRESS = os.getenv("SIGNAL_REGISTRY_ADDRESS", "")
PRIVATE_KEY = os.getenv("MANTLE_PRIVATE_KEY", "")
CHAIN_CONFIGURED = bool(CONTRACT_ADDRESS and PRIVATE_KEY)
AGENT_ID = int(os.getenv("AGENT_ID", "0") or "0")
AGENT_URI = os.getenv(
    "AGENT_URI",
    "https://example.com/quantagent-alpha-registry/agent.json",
)
VALIDATOR_ADDRESS = os.getenv("VALIDATOR_ADDRESS", "")
PROOF_URI_BASE = os.getenv("PROOF_URI_BASE", "ipfs://quantagent-demo-proof")
BYREAL_API_BASE = os.getenv("BYREAL_API_BASE", "")
BYREAL_API_KEY = os.getenv("BYREAL_API_KEY", "")
BYREAL_SIMULATION_MODE = os.getenv("BYREAL_SIMULATION_MODE", "true").lower() != "false"
EXPLORER_BASE = os.getenv(
    "MANTLE_EXPLORER_BASE",
    "https://explorer.sepolia.mantle.xyz",
)

SUPPORTED_ASSETS = ["BTC", "ETH", "SOL"]
