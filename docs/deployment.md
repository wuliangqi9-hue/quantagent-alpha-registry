# Deployment Guide

The final DoraHacks submission must use a public URL. Localhost is acceptable
for development only and must not be submitted as the demo link.

## Recommended Path: Docker Single Service

The most reliable deployment path is the included `Dockerfile`. It builds the
React dashboard in a Node stage, then serves the built dashboard from FastAPI in
a Python runtime stage.

Render can use the included `render.yaml`.

Expected public routes:

- `/` serves the dashboard.
- `/api/health` verifies the API is alive.
- `/api/analyze` runs factor analysis and strategy selection.
- `/api/record-signal` records or clearly reports proof mode.
- `/api/agent` reports identity and reputation status.
- `/api/settle` calculates settlement feedback and writes reputation when configured.

## Alternative Path: Native Single Public API Service

Deploy one FastAPI service that also serves the built React dashboard.

Build command:

```bash
pip install -r services/api/requirements.txt
cd apps/web
npm ci
npm run build
cd ../..
```

Start command:

```bash
uvicorn services.api.app.main:app --host 0.0.0.0 --port $PORT
```

## Environment Variables

Required only for real Mantle recording:

```text
MANTLE_RPC_URL=https://rpc.sepolia.mantle.xyz
MANTLE_CHAIN_ID=5003
MANTLE_EXPLORER_BASE=https://explorer.sepolia.mantle.xyz
MANTLE_PRIVATE_KEY=<funded private key>
SIGNAL_REGISTRY_ADDRESS=<deployed SignalRegistry address>
AGENT_ID=<Registered event agentId>
VALIDATOR_ADDRESS=<validator wallet or service address>
PROOF_URI_BASE=ipfs://your-proof-base
```

When these are missing, the app uses demo-proof mode. Demo-proof mode is useful
for development and backup demos, but the final submission should include at
least one real Mantle explorer link if possible.

Optional but recommended:

```text
PRIVATE_MEMPOOL_RPC_URL=<protected Mantle RPC endpoint>
BYREAL_API_BASE=<Byreal or RealClaw endpoint>
BYREAL_API_KEY=<adapter credential>
BYREAL_SIMULATION_MODE=false
```

`PRIVATE_MEMPOOL_RPC_URL` is preferred over `MANTLE_RPC_URL` for transaction
broadcasts when set. The API estimates gas dynamically from the current block;
there are no fixed gas fee constants in the final path.

Where to put them:

- local API run: root `.env`;
- public deployment: hosting provider environment variables;
- Hardhat deployment: `contracts/.env`.

## Separate Web/API Deployment

If the web app is deployed separately, set:

```text
VITE_API_URL=https://your-public-api.example.com/api
```

Do not point `VITE_API_URL` at localhost for the final build.

## Pre-submit Checks

- Public app URL opens the dashboard.
- Public `/api/health` returns `status: ok`.
- Analyze works for BTC, ETH, and SOL.
- The data mode badge clearly shows `live` or `offline-demo`.
- The proof panel shows either a Mantle explorer link or a clearly labeled
  demo-proof status.
- Agent Passport shows a configured `agentId` for final judging.
- `Record on Mantle` uses `identity+validation`, not the legacy signal path.
- `Settle Reputation` writes feedback on-chain or clearly reports why it is in
  backup demo mode.
