# Proof Model

QuantAgent Alpha Registry uses Mantle as a decision audit trail.

## What Is Stored On-chain

The MVP stores a compact decision proof:

- `signalHash`;
- `symbol`;
- `strategyId`;
- `modelVersion`;
- `mode`;
- block timestamp emitted by the contract.

The full factor matrix is not stored on-chain because it is too large and
unnecessary for the MVP proof.

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

## MVP Trust Boundary

- Off-chain: data loading, factor calculation, strategy selection, explanation.
- On-chain: immutable timestamped decision proof.
- UI: connects the human-readable report to the recorded hash.
