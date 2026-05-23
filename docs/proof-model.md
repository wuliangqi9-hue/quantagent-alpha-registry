# Proof Model

QuantAgent Alpha Registry uses Mantle as a decision audit trail and an
ERC-8004-inspired trust layer.

## What Is Stored On-chain

The MVP stores a compact decision proof:

- `signalHash`;
- `agentId`, when configured;
- `symbol`;
- `strategyId`;
- `modelVersion`;
- `mode`;
- `proofURI` and `proofHash`, when the agent validation path is configured;
- block timestamp emitted by the contract.

It also stores or emits:

- identity registration for the agent NFT;
- validation requests that bind a signal hash to a validator address;
- reputation feedback after settlement.

The full factor matrix is not stored on-chain because it is too large and
unnecessary for the MVP proof. The `proofHash` is a placeholder-compatible
anchor for a future zk proof or zkTLS provenance proof.

## What Is Hashed

The API builds a canonical decision report with:

- schema version;
- symbol;
- data mode;
- factor engine version;
- strategy selector version;
- selected strategy;
- signal direction;
- confidence;
- factor summaries;
- top drivers;
- risk warnings;
- benchmark summary;
- limitations.

The report is serialized with sorted JSON keys and hashed with SHA-256.

## Why This Matters

The hash lets judges and future users verify that a specific off-chain decision
report corresponds to the compact record published on Mantle.

This does not prove future profitability. It proves decision traceability.

## ERC-8004 Mapping

This project does not claim to be a complete canonical ERC-8004 production
implementation. For the hackathon MVP, `SignalRegistry.sol` combines the three
layers into one inspectable contract:

- Identity: `register`, `registerWithWallet`, `ownerOf`, and `tokenURI`;
- Validation: `recordSignalForAgent`, `validationRequest`, and
  `validationResponse`;
- Reputation: `giveFeedback` and `getReputationSummary`.

## MVP Trust Boundary

- Off-chain: data loading, factor calculation, strategy selection, explanation.
- On-chain: agent identity, immutable timestamped decision proof, validation
  request, and reputation feedback.
- UI: connects the human-readable report to the recorded hash.
