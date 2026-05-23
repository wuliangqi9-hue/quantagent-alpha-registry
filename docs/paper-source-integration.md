# Paper Source Integration Notes

This repo now includes small reference snapshots from the two papers/projects
with usable public code:

- `references/papers/finmem`
- `references/papers/quantagent`

They are MIT-licensed reference material. They are not imported by the runtime.

## What To Borrow First

### FinMem

Best source files:

- `references/papers/finmem/puppy/memorydb.py`
- `references/papers/finmem/puppy/memory_functions/`
- `references/papers/finmem/puppy/reflection.py`
- `references/papers/finmem/puppy/prompts.py`

Recommended adaptation:

1. Build our own `packages/agent-memory/` module.
2. Store settlement records with `signalHash`, `pnlBps`, `strategyId`,
   `alphaFormula`, `riskProfileState`, and `reputationScore`.
3. Score memories with recency, importance, and PnL impact.
4. Feed the top memories into `select_strategy(...)` as structured context.

### QuantAgent

Best source files:

- `references/papers/quantagent/agent_state.py`
- `references/papers/quantagent/trading_graph.py`
- `references/papers/quantagent/indicator_agent.py`
- `references/papers/quantagent/pattern_agent.py`
- `references/papers/quantagent/trend_agent.py`
- `references/papers/quantagent/decision_agent.py`

Recommended adaptation:

1. Split our selector into specialized workers:
   - factor analyst;
   - regime analyst;
   - risk critic;
   - reputation critic;
   - final decision agent.
2. Keep the current deterministic selector as the final safety layer.
3. Let LLM agents propose only extra fields like `alphaFormula`,
   `formulaRationale`, and `reflection` until tests are stable.

## What Not To Copy Directly

- Do not import these reference modules directly into `services/api`.
- Do not copy their dependency stacks into the main requirements file yet.
- Do not bring benchmark CSV corpora or image assets into the main app.
- Do not use any `.env` or credential-like files from external repos.

## Immediate Next Implementation Slice

The highest-value next slice is:

1. Create `packages/agent-memory/agent_memory/`.
2. Implement a tiny JSONL memory store inspired by FinMem.
3. Add `/api/memory` and update `/api/settle` to persist each settlement.
4. Feed last high-impact memory into `select_strategy(...)`.
5. Show memory/reflection evidence in the frontend Agent Passport.
