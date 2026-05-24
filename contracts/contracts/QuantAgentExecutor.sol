// SPDX-License-Identifier: MIT
pragma solidity ^0.8.4;


/// @notice Minimal Reclaim interface matching the official verifier-solidity-sdk.
/// Uses identical struct layouts so our code calls the real on-chain verifier,
/// but avoids importing the SDK's inline-assembly-heavy source code during compilation.
interface IReclaim {
    struct CompleteClaimData {
        bytes32 identifier;
        address owner;
        uint32 timestampS;
        uint32 epoch;
    }

    struct SignedClaim {
        CompleteClaimData claim;
        bytes[] signatures;
    }

    struct ClaimInfo {
        string provider;
        string parameters;
        string context;
    }

    struct Proof {
        ClaimInfo claimInfo;
        SignedClaim signedClaim;
    }

    function verifyProof(Proof calldata proof) external view;
}

interface ISignalRegistryLike {
    function recordSignalForAgent(
        uint256 agentId,
        bytes32 signalHash,
        string calldata assetSymbol,
        string calldata strategyId,
        string calldata modelVersion,
        string calldata mode,
        address validatorAddress,
        string calldata proofURI,
        bytes32 proofHash
    ) external;
}

/// @title QuantAgentExecutor
/// @notice zkTLS proof gate for QuantAgent execution intents.
/// @dev Verifies Reclaim proof before anchoring an execution signal. Actual Byreal
/// RFQ settlement can be wired behind the same proof gate in production.
contract QuantAgentExecutor {
    address public immutable reclaimAddress;
    ISignalRegistryLike public immutable signalRegistry;

    struct TradePayload {
        uint256 agentId;
        bytes32 signalHash;
        string assetSymbol;
        string strategyId;
        string modelVersion;
        string mode;
        string proofURI;
        bytes32 proofHash;
    }

    event TradeProofVerified(
        uint256 indexed agentId,
        bytes32 indexed signalHash,
        string assetSymbol,
        bytes32 proofHash
    );

    constructor(address _reclaimAddress, address _signalRegistry) {
        require(_reclaimAddress != address(0), "reclaim required");
        require(_signalRegistry != address(0), "registry required");
        reclaimAddress = _reclaimAddress;
        signalRegistry = ISignalRegistryLike(_signalRegistry);
    }

    function executeTradeWithProof(
        IReclaim.Proof memory proof,
        TradePayload calldata payload
    ) external {
        IReclaim(reclaimAddress).verifyProof(proof);
        signalRegistry.recordSignalForAgent(
            payload.agentId,
            payload.signalHash,
            payload.assetSymbol,
            payload.strategyId,
            payload.modelVersion,
            payload.mode,
            reclaimAddress,
            payload.proofURI,
            payload.proofHash
        );
        emit TradeProofVerified(payload.agentId, payload.signalHash, payload.assetSymbol, payload.proofHash);
    }
}
