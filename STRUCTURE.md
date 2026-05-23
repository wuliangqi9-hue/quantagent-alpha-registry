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
- submit or clearly label Mantle proof mode.

Public API endpoints:

- `GET /api/health`
- `GET /api/assets`
- `POST /api/analyze`
- `POST /api/record-signal`
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

### `contracts`

Mantle signal-recording layer.

MVP contract function:

```solidity
recordSignal(bytes32 signalHash, string symbol, string strategyId, string modelVersion, string mode)
```

The contract emits `SignalRecorded` and does not custody funds or execute trades.
It exists to prove decision traceability.

### `data/sample`

Offline BTC, ETH, and SOL snapshots.

This is a deliberate reliability feature: the demo can continue if live APIs are
slow, blocked, or rate-limited.

### `experiments`

Judge-friendly benchmark provenance and caveats.

The MVP embeds compact benchmark constants in the strategy selector; this folder
explains where the evidence came from and how it should be presented.

### `submissions/dorahacks`

Final submission materials:

- pitch;
- demo video outline;
- final checklist.

## Completion Path

1. Deploy the Docker single-service app to a public URL.
2. Deploy `SignalRegistry` to Mantle Sepolia or the official required network.
3. Configure `SIGNAL_REGISTRY_ADDRESS` and `MANTLE_PRIVATE_KEY` in the public service.
4. Record at least one real signal and save the Mantle explorer link.
5. Record the 2-3 minute demo video.
6. Submit public app URL, repository, video, and contract/explorer link.
