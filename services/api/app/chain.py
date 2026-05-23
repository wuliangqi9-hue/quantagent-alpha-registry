from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .config import CONTRACT_ADDRESS, EXPLORER_BASE, MANTLE_CHAIN_ID, MANTLE_RPC_URL, PRIVATE_KEY, ROOT

ABI_PATH = ROOT / "contracts" / "artifacts" / "SignalRegistry.json"

CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "bytes32", "name": "signalHash", "type": "bytes32"},
            {"internalType": "string", "name": "symbol", "type": "string"},
            {"internalType": "string", "name": "strategyId", "type": "string"},
            {"internalType": "string", "name": "modelVersion", "type": "string"},
            {"internalType": "string", "name": "mode", "type": "string"},
        ],
        "name": "recordSignal",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "bytes32", "name": "signalHash", "type": "bytes32"},
            {"indexed": False, "internalType": "string", "name": "symbol", "type": "string"},
            {"indexed": False, "internalType": "string", "name": "strategyId", "type": "string"},
            {"indexed": False, "internalType": "string", "name": "modelVersion", "type": "string"},
            {"indexed": False, "internalType": "string", "name": "mode", "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"},
        ],
        "name": "SignalRecorded",
        "type": "event",
    },
]


def _load_abi() -> list[dict[str, Any]]:
    if ABI_PATH.exists():
        data = json.loads(ABI_PATH.read_text(encoding="utf-8"))
        return data.get("abi", data)
    return CONTRACT_ABI


def record_signal_on_chain(
    signal_hash: str,
    symbol: str,
    strategy_id: str,
    model_version: str,
    mode: str,
) -> dict[str, Any]:
    if not CONTRACT_ADDRESS or not PRIVATE_KEY:
        return {
            "recorded": False,
            "mock": True,
            "proofMode": "demo-proof",
            "mode": mode,
            "signalHash": signal_hash,
            "message": "Set both SIGNAL_REGISTRY_ADDRESS and MANTLE_PRIVATE_KEY to submit on-chain.",
            "explorerUrl": None,
            "txHash": None,
        }

    try:
        from web3 import Web3
    except ImportError as exc:
        raise RuntimeError("web3 is required for on-chain recording") from exc

    w3 = Web3(Web3.HTTPProvider(MANTLE_RPC_URL))
    account = w3.eth.account.from_key(PRIVATE_KEY)
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACT_ADDRESS),
        abi=_load_abi(),
    )
    hash_bytes = Web3.to_bytes(hexstr=signal_hash)
    tx = contract.functions.recordSignal(
        hash_bytes,
        symbol,
        strategy_id,
        model_version,
        mode,
    ).build_transaction(
        {
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "chainId": MANTLE_CHAIN_ID,
            "gas": 300000,
            "maxFeePerGas": w3.to_wei(0.05, "gwei"),
            "maxPriorityFeePerGas": w3.to_wei(0.01, "gwei"),
        }
    )
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    tx_hex = receipt.transactionHash.hex()
    if not tx_hex.startswith("0x"):
        tx_hex = f"0x{tx_hex}"
    return {
        "recorded": receipt.status == 1,
        "mock": False,
        "proofMode": "real-onchain",
        "mode": mode,
        "signalHash": signal_hash,
        "txHash": tx_hex,
        "explorerUrl": f"{EXPLORER_BASE}/tx/{tx_hex}",
        "blockNumber": int(receipt.blockNumber),
    }


def mock_record(signal_hash: str, symbol: str, strategy_id: str, model_version: str, mode: str) -> dict[str, Any]:
    ts = int(time.time())
    pseudo = f"{signal_hash}-{ts}"[-16:]
    tx_hash = f"0x{'0' * 24}{pseudo.replace('0x', '')[:16]}"
    return {
        "recorded": False,
        "mock": True,
        "proofMode": "demo-proof",
        "mode": mode,
        "signalHash": signal_hash,
        "symbol": symbol,
        "strategyId": strategy_id,
        "modelVersion": model_version,
        "txHash": None,
        "explorerUrl": None,
        "message": "Demo mode: configure Mantle credentials to submit a real transaction.",
    }
