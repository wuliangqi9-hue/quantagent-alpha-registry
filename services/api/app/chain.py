from __future__ import annotations

import json
from typing import Any

from .config import (
    AGENT_ID,
    AGENT_URI,
    CONTRACT_ADDRESS,
    EFFECTIVE_MANTLE_RPC_URL,
    EXPLORER_BASE,
    MANTLE_CHAIN_ID,
    PRIVATE_KEY,
    PRIVATE_MEMPOOL_RPC_URL,
    PROOF_URI_BASE,
    ROOT,
    VALIDATOR_ADDRESS,
)
from .erc8004 import build_reputation_feedback

ABI_PATHS = [
    ROOT / "contracts" / "artifacts" / "contracts" / "SignalRegistry.sol" / "SignalRegistry.json",
    ROOT / "contracts" / "artifacts" / "SignalRegistry.json",
]

CONTRACT_ABI = [
    {
        "inputs": [{"internalType": "string", "name": "agentURI", "type": "string"}],
        "name": "register",
        "outputs": [{"internalType": "uint256", "name": "agentId", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "agentId", "type": "uint256"},
            {"internalType": "bytes32", "name": "signalHash", "type": "bytes32"},
            {"internalType": "string", "name": "assetSymbol", "type": "string"},
            {"internalType": "string", "name": "strategyId", "type": "string"},
            {"internalType": "string", "name": "modelVersion", "type": "string"},
            {"internalType": "string", "name": "mode", "type": "string"},
            {"internalType": "address", "name": "validatorAddress", "type": "address"},
            {"internalType": "string", "name": "proofURI", "type": "string"},
            {"internalType": "bytes32", "name": "proofHash", "type": "bytes32"},
        ],
        "name": "recordSignalForAgent",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "signalHash", "type": "bytes32"},
            {"internalType": "string", "name": "assetSymbol", "type": "string"},
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
        "inputs": [
            {"internalType": "uint256", "name": "agentId", "type": "uint256"},
            {"internalType": "int128", "name": "value", "type": "int128"},
            {"internalType": "uint8", "name": "valueDecimals", "type": "uint8"},
            {"internalType": "string", "name": "tag1", "type": "string"},
            {"internalType": "string", "name": "tag2", "type": "string"},
            {"internalType": "string", "name": "endpoint", "type": "string"},
            {"internalType": "string", "name": "feedbackURI", "type": "string"},
            {"internalType": "bytes32", "name": "feedbackHash", "type": "bytes32"},
        ],
        "name": "giveFeedback",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "agentId", "type": "uint256"}],
        "name": "getReputationSummary",
        "outputs": [
            {"internalType": "uint64", "name": "count", "type": "uint64"},
            {"internalType": "int128", "name": "summaryValue", "type": "int128"},
            {"internalType": "uint8", "name": "summaryValueDecimals", "type": "uint8"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "agentId", "type": "uint256"}],
        "name": "ownerOf",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "agentId", "type": "uint256"}],
        "name": "tokenURI",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
]


def _load_abi() -> list[dict[str, Any]]:
    for path in ABI_PATHS:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("abi", data)
    return CONTRACT_ABI


def chain_ready() -> bool:
    return bool(CONTRACT_ADDRESS and PRIVATE_KEY)


def _web3_context() -> tuple[Any, Any, Any, Any]:
    if not chain_ready():
        raise RuntimeError("Set both SIGNAL_REGISTRY_ADDRESS and MANTLE_PRIVATE_KEY to submit on-chain.")
    try:
        from web3 import Web3
    except ImportError as exc:
        raise RuntimeError("web3 is required for on-chain recording") from exc

    w3 = Web3(Web3.HTTPProvider(EFFECTIVE_MANTLE_RPC_URL))
    if not w3.is_connected():
        raise RuntimeError(f"Cannot connect to Mantle RPC: {EFFECTIVE_MANTLE_RPC_URL}")
    account = w3.eth.account.from_key(PRIVATE_KEY)
    contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=_load_abi())
    return Web3, w3, account, contract


def _proof_hash(Web3: Any, payload: dict[str, Any]) -> bytes:
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return Web3.keccak(text=canonical)


def _build_dynamic_transaction(w3: Any, account: Any, fn: Any) -> dict[str, Any]:
    base = {
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "chainId": MANTLE_CHAIN_ID,
    }
    try:
        gas_estimate = fn.estimate_gas({"from": account.address})
        base["gas"] = int(gas_estimate * 1.2)
    except Exception:
        base["gas"] = 450000

    latest_block = w3.eth.get_block("latest")
    base_fee = latest_block.get("baseFeePerGas") if isinstance(latest_block, dict) else None
    if base_fee:
        try:
            priority = w3.eth.max_priority_fee
        except Exception:
            priority = w3.to_wei(0.01, "gwei")
        base["maxPriorityFeePerGas"] = int(priority)
        base["maxFeePerGas"] = int(base_fee * 2 + priority)
    else:
        base["gasPrice"] = int(w3.eth.gas_price)

    return fn.build_transaction(base)


def _send_transaction(w3: Any, account: Any, fn: Any) -> dict[str, Any]:
    tx = _build_dynamic_transaction(w3, account, fn)
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    tx_hex = receipt.transactionHash.hex()
    if not tx_hex.startswith("0x"):
        tx_hex = f"0x{tx_hex}"
    return {
        "recorded": receipt.status == 1,
        "txHash": tx_hex,
        "explorerUrl": f"{EXPLORER_BASE}/tx/{tx_hex}",
        "blockNumber": int(receipt.blockNumber),
        "gasUsed": int(receipt.gasUsed),
    }


def get_agent_status() -> dict[str, Any]:
    if not CONTRACT_ADDRESS:
        return {
            "configured": False,
            "identityRegistered": False,
            "agentId": AGENT_ID or None,
            "contractAddress": None,
            "proofMode": "demo-proof",
            "message": "SIGNAL_REGISTRY_ADDRESS is not configured.",
        }

    status: dict[str, Any] = {
        "configured": chain_ready(),
        "identityRegistered": False,
        "agentId": AGENT_ID or None,
        "contractAddress": CONTRACT_ADDRESS,
        "proofMode": "real-onchain" if chain_ready() else "demo-proof",
        "privateMempoolConfigured": bool(PRIVATE_MEMPOOL_RPC_URL),
    }
    if not chain_ready() or AGENT_ID <= 0:
        return status

    try:
        _, _, _, contract = _web3_context()
        owner = contract.functions.ownerOf(AGENT_ID).call()
        uri = contract.functions.tokenURI(AGENT_ID).call()
        count, summary_value, decimals = contract.functions.getReputationSummary(AGENT_ID).call()
        status.update(
            {
                "identityRegistered": True,
                "owner": owner,
                "agentURI": uri,
                "reputation": {
                    "count": int(count),
                    "summaryValue": int(summary_value),
                    "decimals": int(decimals),
                    "score": round(int(summary_value) / (10 ** int(decimals)), 4) if decimals else int(summary_value),
                },
            }
        )
    except Exception as exc:
        status["error"] = str(exc)
    return status


def register_agent_on_chain(agent_uri: str | None = None) -> dict[str, Any]:
    Web3, w3, account, contract = _web3_context()
    uri = agent_uri or AGENT_URI
    fn = contract.functions.register(uri)
    receipt = _send_transaction(w3, account, fn)
    receipt.update(
        {
            "mock": False,
            "proofMode": "real-onchain",
            "agentURI": uri,
            "message": "Agent identity NFT registration submitted. Read the Registered event for the new agentId.",
        }
    )
    return receipt


def record_signal_on_chain(
    signal_hash: str,
    symbol: str,
    strategy_id: str,
    model_version: str,
    mode: str,
    decision_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not chain_ready():
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

    Web3, w3, account, contract = _web3_context()
    hash_bytes = Web3.to_bytes(hexstr=signal_hash)
    proof_payload = decision_report or {
        "signalHash": signal_hash,
        "symbol": symbol,
        "strategyId": strategy_id,
        "modelVersion": model_version,
        "mode": mode,
    }
    proof_hash = _proof_hash(Web3, proof_payload)
    proof_uri = f"{PROOF_URI_BASE}/{signal_hash}"

    if AGENT_ID > 0 and VALIDATOR_ADDRESS:
        fn = contract.functions.recordSignalForAgent(
            AGENT_ID,
            hash_bytes,
            symbol,
            strategy_id,
            model_version,
            mode,
            Web3.to_checksum_address(VALIDATOR_ADDRESS),
            proof_uri,
            proof_hash,
        )
        layer = "identity+validation"
    else:
        fn = contract.functions.recordSignal(hash_bytes, symbol, strategy_id, model_version, mode)
        layer = "legacy-signal"

    receipt = _send_transaction(w3, account, fn)
    receipt.update(
        {
            "mock": False,
            "proofMode": "real-onchain",
            "mode": mode,
            "signalHash": signal_hash,
            "symbol": symbol,
            "strategyId": strategy_id,
            "modelVersion": model_version,
            "agentId": AGENT_ID or None,
            "proofURI": proof_uri if layer == "identity+validation" else None,
            "proofHash": proof_hash.hex(),
            "registryLayer": layer,
            "privateMempoolConfigured": bool(PRIVATE_MEMPOOL_RPC_URL),
        }
    )
    if layer == "legacy-signal":
        receipt["message"] = "Set AGENT_ID and VALIDATOR_ADDRESS to use the ERC-8004-inspired validation path."
    return receipt


def submit_reputation_feedback(
    value: int,
    *,
    signal_hash: str,
    tag1: str,
    tag2: str,
    feedback_payload: dict[str, Any],
) -> dict[str, Any]:
    erc8004_feedback = build_reputation_feedback(feedback_payload)
    fixed_score = erc8004_feedback["score"]
    if not chain_ready() or AGENT_ID <= 0:
        return {
            "recorded": False,
            "mock": True,
            "proofMode": "demo-proof",
            "agentId": AGENT_ID or None,
            "signalHash": signal_hash,
            "erc8004Feedback": erc8004_feedback,
            "message": "Set SIGNAL_REGISTRY_ADDRESS, MANTLE_PRIVATE_KEY, and AGENT_ID to write reputation feedback.",
        }

    Web3, w3, account, contract = _web3_context()
    feedback_hash = _proof_hash(Web3, feedback_payload)
    feedback_uri = f"{PROOF_URI_BASE}/feedback/{signal_hash}"
    fn = contract.functions.giveFeedback(
        AGENT_ID,
        int(fixed_score["value"]),
        int(fixed_score["valueDecimals"]),
        tag1,
        tag2,
        "quantagent-alpha-registry",
        feedback_uri,
        feedback_hash,
    )
    receipt = _send_transaction(w3, account, fn)
    receipt.update(
        {
            "mock": False,
            "proofMode": "real-onchain",
            "agentId": AGENT_ID,
            "signalHash": signal_hash,
            "feedbackValue": int(fixed_score["value"]),
            "feedbackDecimals": int(fixed_score["valueDecimals"]),
            "feedbackURI": feedback_uri,
            "feedbackHash": feedback_hash.hex(),
            "erc8004Feedback": erc8004_feedback,
        }
    )
    return receipt


def mock_record(signal_hash: str, symbol: str, strategy_id: str, model_version: str, mode: str) -> dict[str, Any]:
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
        "privateMempoolConfigured": bool(PRIVATE_MEMPOOL_RPC_URL),
        "message": "Demo mode: configure Mantle credentials to submit a real transaction.",
    }
