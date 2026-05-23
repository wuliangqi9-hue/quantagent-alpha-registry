# Project Structure

This document describes the current engineering structure for the hackathon MVP.

## Repository Layout

```text
黑客松/
  README.md
  GOALS.md
  STRUCTURE.md
  Dockerfile
  render.yaml
  docs/
    architecture.md
    api-examples.md
    deployment.md
    milestones.md
    risk-register.md
    demo-script.md
    judging-checklist.md
    factor-notes.md
    submission-story.md
  apps/
    web/
      README.md
      package.json
      src/
  services/
    api/
      README.md
      requirements.txt
      app/
  packages/
    agent-memory/
      README.md
      agent_memory/
    agent-orchestrator/
      README.md
      agent_orchestrator/
    factor-engine/
      README.md
      crypto_factors/
      factor_engine/
    strategy-selector/
      README.md
      strategy_selector/
  contracts/
    README.md
    contracts/
    scripts/
  data/
    sample/
  experiments/
    README.md
  references/
    papers/
      finmem/
      quantagent/
  submissions/
    dorahacks/
      pitch.md
      demo-video-outline.md
      final-checklist.md
```

## Module Responsibilities

### `apps/web`

React dashboard for judges and users.

Current screens:

- asset and data-mode controls;
- factor radar and factor bar chart;
- Agent Passport with identity, validation, reputation, and Byreal status;
- market regime and selected strategy panel;
- benchmark chart with caveats;
- risk warning panel;
- Mantle proof panel;
- submission posture notes.

### `services/api`

FastAPI backend that coordinates the demo flow.

Responsibilities:

- serve the built React dashboard in single-service deployments;
- expose `/api/*` routes for the frontend;
- load live market data when available;
- fall back to `data/sample/` snapshots for reliable demos;
- call the factor engine;
- call the strategy selector;
- build the decision report and signal hash;
- expose Byreal/RealClaw execution intent;
- submit or clearly label Mantle proof mode.
- settle a signal and write reputation feedback when configured.
- retrieve FinMem-inspired memory and build QuantAgent-inspired multi-agent context.

Public API endpoints:

- `GET /api/health`
- `GET /api/assets`
- `POST /api/analyze`
- `POST /api/record-signal`
- `GET /api/agent`
- `POST /api/agent/register`
- `GET /api/byreal/status`
- `POST /api/settle`
- `GET /api/memory`
- `GET /api/demo/sample`

Unprefixed routes also exist for local development and FastAPI docs.

### `packages/factor-engine`

Reusable factor computation module adapted from the existing crypto factor
research.

Current factor groups:

- momentum;
- volatility;
- trend;
- volume pressure;
- funding rate;
- open interest.

Optional later factors:

- MVRV;
- SOPR;
- smart-money wallet flow;
- DEX liquidity shock;
- order book imbalance;
- options implied-volatility skew.

### `packages/strategy-selector`

Strategy selection logic based on factor state, market regime, and prior
QuantAgent/Hummingbot workflow evidence.

Initial strategy pool:

- SuperTrend;
- Bollinger;
- MACD + Bollinger.

Outputs:

- `strategyId`;
- `strategyName`;
- signal direction;
- confidence;
- explanation;
- risk warnings;
- benchmark summary;
- chart-ready benchmark data.
- AlphaGPT-style formula and rationale;
- FinMem memory summary;
- QuantAgent multi-agent context.

### `packages/agent-memory`

Production module inspired by FinMem.

Responsibilities:

- persist settlement memories as JSONL;
- retrieve similar memories by recency, importance, factor similarity, and PnL impact;
- expose latest PnL and summary fields for strategy reflection.

### `packages/agent-orchestrator`

Production module inspired by QuantAgent's agent graph.

Responsibilities:

- build deterministic indicator, flow, memory, reputation, and risk critic reports;
- provide structured context to the strategy selector and frontend;
- keep the multi-agent shape without requiring a heavy graph runtime for the MVP.

### `contracts`

Mantle agent registry layer.

Core contract functions:

```solidity
register(string agentURI)
recordSignalForAgent(uint256 agentId, bytes32 signalHash, string symbol, string strategyId, string modelVersion, string mode, address validatorAddress, string proofURI, bytes32 proofHash)
giveFeedback(uint256 agentId, int128 value, uint8 valueDecimals, string tag1, string tag2, string endpoint, string feedbackURI, bytes32 feedbackHash)
```

The contract emits identity, validation, and reputation events and does not
custody funds or execute trades. It exists to prove decision traceability and
agent accountability.

### `data/sample`

Offline BTC, ETH, and SOL snapshots.

This is a deliberate reliability feature: the demo can continue if live APIs are
slow, blocked, or rate-limited.

### `experiments`

Judge-friendly benchmark provenance and caveats.

The MVP embeds compact benchmark constants in the strategy selector; this folder
explains where the evidence came from and how it should be presented.

### `references/papers`

Sanitized MIT-licensed source snapshots copied for architecture reference only.
They are not imported by runtime code.

Current references:

- FinMem source snapshot for memory database, recency/importance scoring, and reflection flow.
- QuantAgent source snapshot for multi-agent graph structure and analyst/decision-agent split.

### `submissions/dorahacks`

Final submission materials:

- pitch;
- demo video outline;
- final checklist.

## Completion Path

1. Deploy the Docker single-service app to a public URL.
2. Deploy `SignalRegistry` to Mantle Sepolia or the official required network.
3. Register the agent and configure `AGENT_ID`, `VALIDATOR_ADDRESS`, `SIGNAL_REGISTRY_ADDRESS`, and `MANTLE_PRIVATE_KEY` in the public service.
4. Record at least one real signal and save the Mantle explorer link.
5. Settle one signal and save the reputation feedback evidence.
6. Record the 2-3 minute demo video.
7. Submit public app URL, repository, video, and contract/explorer link.
