from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SAMPLE_DIR = ROOT / "data" / "sample"
FACTOR_ENGINE_DIR = ROOT / "packages" / "factor-engine"
STRATEGY_SELECTOR_DIR = ROOT / "packages" / "strategy-selector"
AGENT_MEMORY_DIR = ROOT / "packages" / "agent-memory"
AGENT_ORCHESTRATOR_DIR = ROOT / "packages" / "agent-orchestrator"
MEMORY_STORE_PATH = Path(os.getenv("MEMORY_STORE_PATH", str(ROOT / "data" / "agent_memory.jsonl")))
ATLAS_OPRO_STORE_PATH = Path(os.getenv("ATLAS_OPRO_STORE_PATH", str(ROOT / "data" / "atlas_opro.jsonl")))

MANTLE_RPC_URL = os.getenv("MANTLE_RPC_URL", "https://rpc.sepolia.mantle.xyz")
PRIVATE_MEMPOOL_RPC_URL = os.getenv(
    "PRIVATE_MEMPOOL_RPC_URL",
    os.getenv("MANTLE_PRIVATE_MEMPOOL_RPC_URL", ""),
)
EFFECTIVE_MANTLE_RPC_URL = PRIVATE_MEMPOOL_RPC_URL or MANTLE_RPC_URL
MANTLE_CHAIN_ID = int(os.getenv("MANTLE_CHAIN_ID", "5003"))
SIGNAL_REGISTRY_ADDRESS = os.getenv("SIGNAL_REGISTRY_ADDRESS", "")
QUANT_AGENT_EXECUTOR_ADDRESS = os.getenv("QUANT_AGENT_EXECUTOR_ADDRESS", "")
CONTRACT_ADDRESS = SIGNAL_REGISTRY_ADDRESS  # backward-compat alias
ERC8004_IDENTITY_REGISTRY_ADDRESS = os.getenv(
    "ERC8004_IDENTITY_REGISTRY_ADDRESS",
    "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432",
)
ERC8004_REPUTATION_REGISTRY_ADDRESS = os.getenv(
    "ERC8004_REPUTATION_REGISTRY_ADDRESS",
    "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63",
)
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
BLOCKY402_FACILITATOR_URL = os.getenv("BLOCKY402_FACILITATOR_URL", "")
X402_WALLET_ADDRESS = os.getenv("X402_WALLET_ADDRESS", "")
X402_MAX_AUTO_PAY_USD = float(os.getenv("X402_MAX_AUTO_PAY_USD", "0.25") or "0.25")
EXPLORER_BASE = os.getenv(
    "MANTLE_EXPLORER_BASE",
    "https://explorer.sepolia.mantle.xyz",
)

SUPPORTED_ASSETS = ["BTC", "ETH", "SOL"]
