# Agent Memory

Lightweight production adaptation of FinMem ideas for the Mantle QuantAgent.

This module is intentionally small:

- JSONL memory store for hackathon-safe deployment;
- recency, importance, similarity, and PnL-impact scoring;
- retrieval output that can be passed into the strategy selector;
- no dependency on the vendored FinMem reference code.

Reference source snapshot:

- `references/papers/finmem/puppy/memorydb.py`
- `references/papers/finmem/puppy/memory_functions/`
