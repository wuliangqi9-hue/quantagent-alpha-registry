# QuantAgent Alpha Registry

QuantAgent turns crypto factor research into an explainable, backtestable, and
on-chain auditable AI trading agent on Mantle.

## Built MVP

- **Factor engine** — adapted from `crypto_factor_module` (market, derivative, on-chain factors)
- **Strategy selector** — SuperTrend / Bollinger / MACD+Bollinger with regime classification
- **API** — FastAPI with live Binance fallback to `data/sample/`
- **Dashboard** — React + Recharts factor radar, benchmark chart, Mantle proof panel
- **Contract** — `SignalRegistry.sol` records compact decision hashes on Mantle

## Why it is different

Most AI trading demos stop at an answer. QuantAgent Alpha Registry records a
decision trail:

- factor scores and strategy reasoning are generated off-chain;
- the decision report is hashed;
- the hash and metadata are recorded through a Mantle proof layer;
- the UI keeps risk caveats and proof mode visible.

## Architecture

```mermaid
flowchart LR
  A["Judge/User"] --> B["React dashboard"]
  B --> C["FastAPI /api"]
  C --> D["Factor engine"]
  C --> E["Strategy selector"]
  C --> F["Decision report + hash"]
  F --> G["SignalRegistry on Mantle"]
  G --> H["Mantle Explorer proof"]
```

## Quick start

Localhost is for development only. The final DoraHacks submission must use a
public app URL and must not submit `localhost`, `127.0.0.1`, or a private LAN
address as the demo link.

### 1. Smoke test (offline)

```powershell
cd "c:\Users\yhy05\Desktop\黑客松"
python scripts\smoke_test.py
```

### 2. API

```powershell
.\scripts\run_api.ps1
```

### 3. Web

```powershell
.\scripts\run_web.ps1
```

Open `http://localhost:5173` for local development. Click **Analyze**, then
**Record on Mantle**.

For final submission, deploy the app publicly. The simplest path is a single
FastAPI service that serves the built React dashboard and exposes API routes
under `/api/*`.

## API

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Health check |
| `GET /api/assets` | BTC, ETH, SOL |
| `POST /api/analyze` | Factors + strategy + decision report |
| `POST /api/record-signal` | Mantle proof or explicit demo-mode proof |
| `GET /api/demo/sample` | Sample data preview |

## Mantle contract

```powershell
cd contracts
npm install
npm run compile
# Copy contracts/.env.example to contracts/.env and set MANTLE_PRIVATE_KEY, then:
npm run deploy:sepolia
```

Copy `.env.example` to root `.env`, then set the deployed address as
`SIGNAL_REGISTRY_ADDRESS`.

Without `SIGNAL_REGISTRY_ADDRESS` and `MANTLE_PRIVATE_KEY`, the app stays in
demo-proof mode. This keeps the judge flow reliable, but the final submission
should include at least one real Mantle transaction or contract address.

## Public deployment

See [docs/deployment.md](docs/deployment.md). Before submission, verify:

- public app URL works without localhost;
- `/api/health` reports `status: ok`;
- `Record on Mantle` returns an explorer transaction or a clearly labeled demo
  proof if the contract is intentionally not configured yet.

## Project layout

```text
packages/factor-engine/     # crypto_factors + MVP summary
packages/strategy-selector/ # regime + strategy selection
services/api/               # FastAPI
apps/web/                   # React dashboard
contracts/                  # SignalRegistry.sol
data/sample/                # BTC, ETH, SOL offline snapshots
```

## Docs

See [STATUS.md](STATUS.md), [GOALS.md](GOALS.md), [STRUCTURE.md](STRUCTURE.md), and `docs/` for hackathon scope and judging alignment.

Submission-focused docs:

- [docs/deployment.md](docs/deployment.md)
- [docs/api-examples.md](docs/api-examples.md)
- [docs/architecture-diagram.md](docs/architecture-diagram.md)
- [docs/proof-model.md](docs/proof-model.md)
- [docs/submission-story.md](docs/submission-story.md)
- [docs/launch-checklist.md](docs/launch-checklist.md)
- [docs/repo-hygiene.md](docs/repo-hygiene.md)
- [submissions/dorahacks/pitch.md](submissions/dorahacks/pitch.md)
- [submissions/dorahacks/final-checklist.md](submissions/dorahacks/final-checklist.md)
