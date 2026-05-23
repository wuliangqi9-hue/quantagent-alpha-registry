from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SAMPLE_DIR = ROOT / "data" / "sample"
FACTOR_ENGINE_DIR = ROOT / "packages" / "factor-engine"
STRATEGY_SELECTOR_DIR = ROOT / "packages" / "strategy-selector"

MANTLE_RPC_URL = os.getenv("MANTLE_RPC_URL", "https://rpc.sepolia.mantle.xyz")
MANTLE_CHAIN_ID = int(os.getenv("MANTLE_CHAIN_ID", "5003"))
CONTRACT_ADDRESS = os.getenv("SIGNAL_REGISTRY_ADDRESS", "")
PRIVATE_KEY = os.getenv("MANTLE_PRIVATE_KEY", "")
CHAIN_CONFIGURED = bool(CONTRACT_ADDRESS and PRIVATE_KEY)
EXPLORER_BASE = os.getenv(
    "MANTLE_EXPLORER_BASE",
    "https://explorer.sepolia.mantle.xyz",
)

SUPPORTED_ASSETS = ["BTC", "ETH", "SOL"]
