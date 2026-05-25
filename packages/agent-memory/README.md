# Agent Memory

Lightweight production adaptation of FinMem ideas for the Mantle QuantAgent.

This module is intentionally small:

- JSONL memory store for hackathon-safe deployment;
- recency, importance, similarity, and PnL-impact scoring;
- retrieval output that can be passed into the strategy selector;
- no runtime dependency on vendored paper source code.

The original FinMem project is used as design provenance. This repository keeps
only the production adaptation needed for the Mantle demo and does not vendor
third-party research snapshots.
