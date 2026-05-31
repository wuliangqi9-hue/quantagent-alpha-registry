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

interface IERC20Like {
    function transferFrom(address from, address to, uint256 value) external returns (bool);
}

/// @title QuantAgentExecutor
/// @notice zkTLS proof gate for QuantAgent execution intents.
/// @dev Verifies Reclaim proof, binds it to the submitted payload, anchors the
/// execution signal, and optionally emits/settles a testnet RFQ transfer.
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

    struct SettlementIntent {
        address asset;
        address from;
        address to;
        uint256 amount;
        bytes32 routeHash;
    }

    event TradeProofVerified(
        uint256 indexed agentId,
        bytes32 indexed signalHash,
        string assetSymbol,
        bytes32 proofHash
    );

    event SettlementIntentExecuted(
        uint256 indexed agentId,
        bytes32 indexed signalHash,
        address indexed asset,
        address from,
        address to,
        uint256 amount,
        bytes32 routeHash,
        bool tokenTransfer
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
        _verifyAndRecord(proof, payload);
    }

    function executeTradeWithProofAndSettlement(
        IReclaim.Proof memory proof,
        TradePayload calldata payload,
        SettlementIntent calldata settlement
    ) external {
        _verifyAndRecord(proof, payload);
        bool tokenTransfer = settlement.asset != address(0)
            && settlement.from != address(0)
            && settlement.to != address(0)
            && settlement.amount > 0;
        if (tokenTransfer) {
            bytes32 expectedRouteHash = settlementIntentHash(settlement);
            require(settlement.routeHash == expectedRouteHash, "settlement route mismatch");
            require(_proofContainsHash(proof, expectedRouteHash), "settlement/proof mismatch");
            require(
                IERC20Like(settlement.asset).transferFrom(settlement.from, settlement.to, settlement.amount),
                "settlement transfer failed"
            );
        }
        emit SettlementIntentExecuted(
            payload.agentId,
            payload.signalHash,
            settlement.asset,
            settlement.from,
            settlement.to,
            settlement.amount,
            settlement.routeHash,
            tokenTransfer
        );
    }

    function settlementIntentHash(SettlementIntent calldata settlement) public pure returns (bytes32) {
        return keccak256(abi.encode(settlement.asset, settlement.from, settlement.to, settlement.amount));
    }

    function _verifyAndRecord(
        IReclaim.Proof memory proof,
        TradePayload calldata payload
    ) internal {
        IReclaim(reclaimAddress).verifyProof(proof);
        require(_proofBindsPayload(proof, payload), "proof/payload mismatch");
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

    function _proofBindsPayload(
        IReclaim.Proof memory proof,
        TradePayload calldata payload
    ) internal pure returns (bool) {
        bytes memory parameters = bytes(proof.claimInfo.parameters);
        bytes memory context = bytes(proof.claimInfo.context);
        bool signalBound = _contains(parameters, _bytes32Hex(payload.signalHash))
            || _contains(context, _bytes32Hex(payload.signalHash));
        bool agentBound = _containsAgentId(parameters, payload.agentId)
            || _containsAgentId(context, payload.agentId);
        return signalBound && agentBound;
    }

    function _proofContainsHash(
        IReclaim.Proof memory proof,
        bytes32 expectedHash
    ) internal pure returns (bool) {
        bytes memory expected = _bytes32Hex(expectedHash);
        return _contains(bytes(proof.claimInfo.parameters), expected)
            || _contains(bytes(proof.claimInfo.context), expected);
    }

    function _containsAgentId(bytes memory haystack, uint256 agentId) internal pure returns (bool) {
        bytes memory decimalId = _uintDecimal(agentId);
        return _contains(haystack, abi.encodePacked('"agentId":', decimalId))
            || _contains(haystack, abi.encodePacked('"agentId":"', decimalId, '"'))
            || _contains(haystack, abi.encodePacked("agentId=", decimalId))
            || _contains(haystack, abi.encodePacked("agent_id=", decimalId));
    }

    function _contains(bytes memory haystack, bytes memory needle) internal pure returns (bool) {
        if (needle.length == 0 || haystack.length < needle.length) {
            return false;
        }
        for (uint256 i = 0; i <= haystack.length - needle.length; i++) {
            bool matched = true;
            for (uint256 j = 0; j < needle.length; j++) {
                if (haystack[i + j] != needle[j]) {
                    matched = false;
                    break;
                }
            }
            if (matched) {
                return true;
            }
        }
        return false;
    }

    function _bytes32Hex(bytes32 value) internal pure returns (bytes memory) {
        bytes16 symbols = "0123456789abcdef";
        bytes memory out = new bytes(66);
        out[0] = "0";
        out[1] = "x";
        for (uint256 i = 0; i < 32; i++) {
            uint8 b = uint8(value[i]);
            out[2 + i * 2] = symbols[b >> 4];
            out[3 + i * 2] = symbols[b & 0x0f];
        }
        return out;
    }

    function _uintDecimal(uint256 value) internal pure returns (bytes memory) {
        if (value == 0) {
            bytes memory zero = new bytes(1);
            zero[0] = "0";
            return zero;
        }
        uint256 temp = value;
        uint256 digits;
        while (temp != 0) {
            digits++;
            temp /= 10;
        }
        bytes memory out = new bytes(digits);
        while (value != 0) {
            digits -= 1;
            out[digits] = bytes1(uint8(48 + (value % 10)));
            value /= 10;
        }
        return out;
    }
}
