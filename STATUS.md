# Project Status

Current state: hackathon MVP is implemented locally and prepared for public
deployment.

## Implemented

- Factor engine adapted from prior crypto factor research.
- Offline BTC, ETH, and SOL demo snapshots.
- Live Binance data path with offline fallback.
- Strategy selector with regime classification.
- Strategy selector now includes paper-inspired AlphaGPT formula fields, FinMem reputation guardrails, and QuantAgent settlement reflection hooks.
- Benchmark evidence and risk caveats.
- FastAPI backend with `/api/*` routes.
- React dashboard with factor charts, Agent Passport, benchmark chart, risk panel, and proof panel.
- Decision report JSON and SHA-256 signal hash.
- Solidity `SignalRegistry` contract with ERC-8004-inspired identity, validation, and reputation layers.
- Dynamic gas estimation and optional private/protected RPC configuration.
- Byreal/RealClaw execution-intent adapter with simulation fallback.
- Reputation settlement endpoint for post-signal feedback.
- Docker single-service deployment path.
- DoraHacks pitch, demo outline, and final checklist.
- Sanitized FinMem and QuantAgent source snapshots under `references/papers/` for future architecture extraction.

## Not Yet Final

- Public app URL is not filled in.
- `SignalRegistry` deployment address is not filled in.
- `AGENT_ID` and `VALIDATOR_ADDRESS` are not filled in.
- Real Mantle explorer transaction is not saved yet.
- Real validation and reputation feedback events are not saved yet.
- Demo video is not recorded yet.

## Recommended Next Actions

1. Deploy the Docker app publicly.
2. Deploy `SignalRegistry` to Mantle Sepolia or required network.
3. Register the agent identity and configure `AGENT_ID` plus `VALIDATOR_ADDRESS`.
4. Configure public environment variables, including private/protected RPC if available.
5. Record one real signal proof and one reputation feedback.
6. Record demo video.
7. Submit DoraHacks materials.
