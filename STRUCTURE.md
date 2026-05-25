# Project Structure

This repository is organized around a single judged flow:

```text
market state -> policy decision -> execution route -> proof bundle -> settlement feedback
```

## Top Level

```text
黑客松/
  apps/web/                 React dashboard
  services/api/             FastAPI orchestration
  packages/                 Reusable strategy, factor, memory, and agent modules
  contracts/                Mantle Solidity contracts
  data/sample/              Offline BTC/ETH/SOL data
  docs/                     Architecture and submission notes
  submissions/dorahacks/    Pitch and final checklist
  scripts/                  Local run, smoke, and Agent Card helper scripts
```

## `services/api`

FastAPI is the integration layer. It coordinates market data, factors, policy,
execution routing, proofs, settlement memory, and chain adapters.

Important files:

- `app/routers/analyze.py`
  Builds factor summary, multi-agent context, strategy selection, execution
  intent, decision report, signal hash, and initial ProofBundle.

- `app/routers/signal.py`
  Records the latest signal, settles PnL, appends memory, generates TEE/zkTLS
  proof fields, builds final ProofBundle, and creates ERC-8004-compatible
  reputation feedback.

- `app/routers/agent.py`
  Serves `/api/agent/card` and `/api/agent/erc8004`.

- `app/agent_card.py`
  Builds the Agent Registration File with `services`, `registrations`,
  `supportedTrust`, `x402Support`, and `cardHash`.

- `app/erc8004_adapter.py`
  Provides a stable identity / validation / reputation boundary. It returns
  structured fallback states when live registry values are not configured.

- `app/proof_bundle.py`
  Creates canonical proof bundles and proof hashes.

- `app/execution.py`
  Implements Byreal/RealClaw quote -> route -> receipt abstractions.

- `app/reclaim.py`, `app/tee.py`, `app/x402.py`
  Live-ready adapters with deterministic fallback behavior.

- `tests/test_api_flow.py`
  End-to-end API baseline for supported assets.

## `apps/web`

The dashboard is an agent cockpit, not a marketing page.

Important panels:

- `AgentPassport.tsx`
  ERC-8004 registry path, agent URI, validation status, reputation, memory,
  Byreal mode, and risk profile.

- `RegimeStrategy.tsx`
  Market regime, selected strategy, confidence, QTMRL policy score, critic value,
  AlphaGPT-style formula, and top drivers.

- `ExecutionPanel.tsx`
  Target exposure, route type, venue, slippage, MEV posture, quote expiry,
  execution mode, route rationale, and x402 audit.

- `MantleProofPanel.tsx`
  Signal hash, ProofBundle hash, data proof, TEE, zkTLS, settlement, and copy
  actions for decision report / ProofBundle JSON.

## `packages/factor-engine`

Computes chart-ready crypto factor summaries. Current factors include:

- momentum;
- volatility;
- trend;
- volume pressure;
- funding;
- open interest;
- Mantle-native gas, DEX liquidity, bridge flow, and staking yield proxies.

## `packages/strategy-selector`

Converts factors and memory into a strategy decision.

Important files:

- `selector.py`
  Main selection pipeline: regime, strategy, guardrails, benchmark evidence,
  position plan, policy output, prompt fields.

- `finpos.py`
  Direction and quantity/risk decision agents.

- `policy_blender.py`
  QTMRL/A2C-style state vector, critic value, policy score, confidence blending,
  and reward features.

- `benchmark.py`
  Benchmark constants and chart markers for judge-facing evidence.

## `packages/agent-memory`

Persistent settlement memory inspired by FinMem.

- `store.py` keeps JSONL records and retrieves similar prior settlements by
  recency, importance, factor similarity, and PnL impact.
- `atlas_opro.py` tracks prompt variants and updates their performance after settlement.
- The original FinMem work is treated as design provenance only. The repo no
  longer vendors third-party paper source snapshots.

Runtime memory files are generated under `data/` unless `MEMORY_STORE_PATH` and
`ATLAS_OPRO_STORE_PATH` are overridden. They are not required in git.

## `packages/agent-orchestrator`

Deterministic multi-agent context inspired by QuantAgent.

Sub-agents:

- Indicator agent;
- Flow agent;
- Memory agent;
- Reputation agent;
- Risk critic;
- A2C policy skeleton.

The output is consumed by the strategy selector and dashboard.

## `contracts`

Solidity contracts and Hardhat config.

- `SignalRegistry.sol`
  Project fallback registry for agent identity-inspired signal recording,
  validation request metadata, and reputation feedback.

- `QuantAgentExecutor.sol`
  Reclaim-compatible proof-gate shape for zkTLS-verified execution intents.

- `ERC8004AgentCard.sol`
  Experimental on-chain Agent Card metadata storage helper.

Generated `cache/`, build-info, and debug artifacts should stay out of git.

## `scripts`

- `smoke_test.py`
  Offline strategy smoke test for BTC, ETH, SOL.

- `register_agent_card.py`
  Prints the canonical Agent Card and next steps for public hosting /
  ERC-8004 registration.

- `run_api.ps1`, `run_web.ps1`
  Local development runners.

## Cleanup Policy

Safe to remove:

- `.pytest_cache/`;
- `.ruff_cache/`;
- `__pycache__/`;
- `apps/web/dist/`;
- `contracts/cache/`;
- runtime `data/agent_memory.jsonl` and `data/atlas_opro.jsonl`.
- vendored paper source snapshots or local-only experiment notes.

Do not remove unless intentionally resetting the local environment:

- `apps/web/node_modules/`;
- `contracts/node_modules/`;
- `services/api/.venv/`;
- `data/sample/`.
