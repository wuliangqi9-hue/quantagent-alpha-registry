# Vendored Paper Reference Snapshot

These files are copied for architectural reference only. They are not imported by the QuantAgent Mantle runtime.

## FinMem

- Source: https://github.com/pipiku915/finmem-llm-stocktrading
- Snapshot commit: be814aa47970de9bf2fdd6a1d5a60ae5cf361b46
- License: MIT, preserved in `finmem/LICENSE`
- Kept: `puppy/`, config files, README, selected data-pipeline scripts
- Skipped: `.env`, `.git`, video files, sample zip data, large generated data

Useful references:

- `finmem/puppy/memorydb.py` for memory database structure
- `finmem/puppy/memory_functions/` for recency, importance, decay, and compound memory scoring
- `finmem/puppy/reflection.py` for reflection flow
- `finmem/puppy/prompts.py` for prompt organization

## QuantAgent

- Source: https://github.com/Y-Research-SBU/QuantAgent
- Snapshot commit: 92519f806286192345e940e7ab77496462d662b7
- License: MIT, preserved in `quantagent/LICENSE`
- Kept: core `*_agent.py`, graph setup/utilities, templates, tests, README files
- Skipped: `.git`, benchmark CSV corpus, image assets, generated static demo files
- Sanitized: placeholder API key strings in `default_config.py`

Useful references:

- `quantagent/trading_graph.py` for multi-agent graph wiring
- `quantagent/decision_agent.py` for final decision synthesis
- `quantagent/indicator_agent.py`, `pattern_agent.py`, and `trend_agent.py` for agent specialization
- `quantagent/agent_state.py` for shared state design

## Integration Rule

Do not import these modules directly into production code. First extract the idea into our own small adapter under `packages/` or `services/`, then add tests and attribution.
