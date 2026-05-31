// SPDX-License-Identifier: MIT
pragma solidity ^0.8.4;

contract MockReclaimVerifier {
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

    function verifyProof(Proof calldata) external pure {}
}
