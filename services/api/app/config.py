from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
if os.getenv("QUANTAGENT_SKIP_DOTENV", "false").lower() != "true":
    load_dotenv(ROOT / ".env", override=False)

SAMPLE_DIR = ROOT / "data" / "sample"
FACTOR_ENGINE_DIR = ROOT / "packages" / "factor-engine"
STRATEGY_SELECTOR_DIR = ROOT / "packages" / "strategy-selector"
AGENT_MEMORY_DIR = ROOT / "packages" / "agent-memory"
AGENT_ORCHESTRATOR_DIR = ROOT / "packages" / "agent-orchestrator"
MEMORY_STORE_PATH = Path(os.getenv("MEMORY_STORE_PATH", str(ROOT / "data" / "agent_memory.jsonl")))
ATLAS_OPRO_STORE_PATH = Path(os.getenv("ATLAS_OPRO_STORE_PATH", str(ROOT / "data" / "atlas_opro.jsonl")))

MANTLE_RPC_URL = os.getenv("MANTLE_RPC_URL", "https://rpc.mantle.xyz")
PRIVATE_MEMPOOL_RPC_URL = os.getenv(
    "PRIVATE_MEMPOOL_RPC_URL",
    os.getenv("MANTLE_PRIVATE_MEMPOOL_RPC_URL", ""),
)
EFFECTIVE_MANTLE_RPC_URL = PRIVATE_MEMPOOL_RPC_URL or MANTLE_RPC_URL
MANTLE_CHAIN_ID = int(os.getenv("MANTLE_CHAIN_ID", "5000"))
MANTLE_ENABLE_ONCHAIN_WRITES = os.getenv("MANTLE_ENABLE_ONCHAIN_WRITES", "false").lower() == "true"
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
ERC8004_VALIDATION_REGISTRY_ADDRESS = os.getenv(
    "ERC8004_VALIDATION_REGISTRY_ADDRESS",
    "",
)
AGENT_CARD_BASE_URL = os.getenv("AGENT_CARD_BASE_URL", "")
PRIVATE_KEY = os.getenv("MANTLE_PRIVATE_KEY", "")
CHAIN_CONFIGURED = bool(MANTLE_ENABLE_ONCHAIN_WRITES and CONTRACT_ADDRESS and PRIVATE_KEY)
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
    "https://explorer.mantle.xyz",
)
# ---- TEE / Phala Network ----
PHALA_TEE_ENABLED = os.getenv("PHALA_TEE_ENABLED", "false").lower() != "false"
PHALA_ENCLAVE_ENDPOINT = os.getenv("PHALA_ENCLAVE_ENDPOINT", "")
PHALA_API_KEY = os.getenv("PHALA_API_KEY", "")

# ---- Reclaim Protocol / zkTLS ----
RECLAIM_ZKTLS_ENABLED = os.getenv("RECLAIM_ZKTLS_ENABLED", "false").lower() != "false"
RECLAIM_APP_ID = os.getenv("RECLAIM_APP_ID", "")
RECLAIM_APP_SECRET = os.getenv("RECLAIM_APP_SECRET", "")
RECLAIM_VERIFIER_ADDRESS = os.getenv(
    "RECLAIM_VERIFIER_ADDRESS",
    "0x0000000000000000000000000000000000000000",
)

# ---- ATLAS Adaptive-OPRO ----
ATLAS_OPRO_ENABLED = os.getenv("ATLAS_OPRO_ENABLED", "false").lower() != "false"
ATLAS_MAX_ITERATIONS = int(os.getenv("ATLAS_MAX_ITERATIONS", "20") or "20")
ATLAS_MUTATION_RATE = float(os.getenv("ATLAS_MUTATION_RATE", "0.15") or "0.15")

# ---- Byreal / RealClaw SDK ----
BYREAL_SDK_PATH = os.getenv("BYREAL_SDK_PATH", "")
REALCLAW_API_ENDPOINT = os.getenv("REALCLAW_API_ENDPOINT", "")
BYREAL_PERPS_LIVE_ENABLED = os.getenv("BYREAL_PERPS_LIVE_ENABLED", "false").lower() == "true"

# ---- FinPos 多时间尺度奖励 ----
FINPOS_MULTI_TIMESCALE_ENABLED = os.getenv("FINPOS_MULTI_TIMESCALE_ENABLED", "false").lower() != "false"

# ---- A2C 强化学习在线训练 ----
A2C_TRAINING_ENABLED = os.getenv("A2C_TRAINING_ENABLED", "false").lower() != "false"

# ---- x402 机器支付协议 ----
X402_ENABLED = bool(BLOCKY402_FACILITATOR_URL and X402_WALLET_ADDRESS)

SUPPORTED_ASSETS = ["BTC", "ETH", "SOL"]
