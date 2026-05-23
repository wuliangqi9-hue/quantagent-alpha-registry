# Goals

## Primary Goal

Build a hackathon-ready AI trading agent that converts existing crypto factor
research and QuantAgent strategy-selection experiments into a usable, explainable,
and on-chain auditable Mantle application.

The goal is not to claim stable trading profit. The goal is to prove that a
research-grounded agent can:

- compute meaningful crypto factors;
- select a strategy based on market state and historical evidence;
- explain its reasoning in trader-friendly language;
- publish a verifiable decision record on Mantle.

## Target Tracks

Primary track:

- AI Trading & Strategy

Secondary track:

- AI Alpha & Data

Optional extension only if time allows:

- Agentic Wallets & Economy

## MVP Demo Flow

1. User opens the dashboard.
2. User chooses `BTC`, `ETH`, `SOL`, or enters a token address.
3. The app fetches or loads recent market data.
4. The factor engine generates a factor matrix.
5. The agent identifies the market regime: `bull`, `bear`, or `range`.
6. The strategy selector chooses one candidate strategy:
   - SuperTrend
   - Bollinger
   - MACD + Bollinger
7. The UI shows:
   - selected strategy;
   - signal direction;
   - confidence score;
   - key factor drivers;
   - risk warnings;
   - historical benchmark summary.
8. The app writes a compact signal record to Mantle:
   - `signalHash`
   - `symbol`
   - `strategyId`
   - `modelVersion`
   - `timestamp`
9. The UI links to the Mantle explorer transaction.

## MVP Lock

The first public version must include only four core systems:

- factor engine;
- strategy selector;
- dashboard;
- Mantle signal-recording contract.

Everything else is optional until this loop works end to end. Optional items
include ERC-8004 integration, wallet automation, live execution, zk proofs,
private mempools, and multi-agent orchestration.

## Decision Record Shape

Each on-chain record should be small and cheap. The contract stores or emits a
compact proof of a decision, not the full factor matrix.

Recommended payload:

- `signalHash`: hash of the full off-chain decision report;
- `symbol`: selected asset or token;
- `strategyId`: selected strategy;
- `modelVersion`: factor and selector version;
- `timestamp`: block or backend decision time;
- `mode`: `live` or `offline-demo`.

## Success Criteria

Engineering:

- Publicly accessible frontend; localhost is development-only and cannot be the submitted demo URL.
- Demo can run in both live-data mode and offline sample-data mode.
- Reproducible backend service or documented local run path.
- At least one verified Mantle contract or transaction flow.
- Clear README with setup, architecture, and demo instructions.
- Open-source code for the app, factor pipeline, strategy selector, and contract.

Product:

- A judge can understand the value proposition in 30 seconds.
- A judge can complete the demo flow in under 3 minutes.
- The dashboard makes factor, strategy, risk, and on-chain proof visible.
- Key factor drivers and benchmark results are shown visually, not only as text.

Research:

- Existing crypto factor research is translated into a short explainable factor list.
- Existing QuantAgent/Hummingbot experiments are used as benchmark evidence.
- Limitations are stated honestly: sample size, low-trade windows, backtest risk,
  slippage, and live-market uncertainty.

## Non-goals

- Do not promise guaranteed profit.
- Do not attempt full autonomous treasury management in the MVP.
- Do not build every sponsor integration at once.
- Do not introduce heavy infrastructure such as message queues or analytical databases unless the MVP truly needs them.
- Do not over-focus on ERC-8004, zkTLS, TEE, or private mempools unless official
  requirements make them necessary.
- Do not submit a pure research report without an interactive demo.

## Demo Reliability Requirements

The live demo must not depend on external APIs being perfectly available. Keep a recent offline market snapshot in `data/sample/` and make the backend able to switch to it when live APIs fail, rate-limit, or respond too slowly.

For the hackathon MVP, prefer a deployable single backend service over a complex microservice stack. FastAPI or a similar lightweight API server is enough unless parallel streaming, queueing, or large historical storage becomes an actual bottleneck.

## Evaluation Posture

The project should be presented as a transparent AI research and execution
system, not as a guaranteed profit machine. Backtest results should be framed as
evidence of the selector workflow, with explicit caveats around sample size,
transaction costs, slippage, and changing market regimes.

## Recommended Narrative

QuantAgent is a bridge between quantitative research and transparent Web3
execution. It does not ask users to trust a black-box trading bot. Instead, it
shows the factors, explains the strategy choice, and records the decision trail
on Mantle.



