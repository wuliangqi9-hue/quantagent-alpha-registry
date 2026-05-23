// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title SignalRegistry
/// @notice Records compact proofs of off-chain QuantAgent decisions on Mantle.
contract SignalRegistry {
    event SignalRecorded(
        bytes32 indexed signalHash,
        string symbol,
        string strategyId,
        string modelVersion,
        string mode,
        uint256 timestamp
    );

    mapping(bytes32 => bool) public recorded;

    function recordSignal(
        bytes32 signalHash,
        string calldata symbol,
        string calldata strategyId,
        string calldata modelVersion,
        string calldata mode
    ) external {
        require(signalHash != bytes32(0), "empty hash");
        require(!recorded[signalHash], "already recorded");
        recorded[signalHash] = true;
        emit SignalRecorded(
            signalHash,
            symbol,
            strategyId,
            modelVersion,
            mode,
            block.timestamp
        );
    }
}
