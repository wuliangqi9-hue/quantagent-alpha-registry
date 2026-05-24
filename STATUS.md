# Project Status

Current state: **参赛级 demo baseline is implemented and tested locally.**

The repository now has a stable end-to-end path for:

```text
analyze -> record signal -> settle -> proof bundle -> reputation feedback
```

## Implemented

- FastAPI endpoints for health, assets, analysis, signal recording, settlement,
  memory, agent status, Agent Card, and ERC-8004 status.
- End-to-end API tests for BTC, ETH, and SOL offline-demo flow.
- React dashboard with Agent Passport, ProofBundle, execution routing, policy
  scoring, risk, benchmark, TEE, zkTLS, ATLAS, and x402 panels.
- Canonical decision report hashing and ProofBundle hashing.
- ERC-8004-compatible Agent Registration File at `/api/agent/card`.
- ERC-8004 adapter boundary for identity, validation, and reputation payloads.
- Project fallback `SignalRegistry.sol` for Mantle signal anchoring and
  reputation feedback.
- Reclaim-compatible `QuantAgentExecutor.sol` proof-gate contract shape.
- Byreal/RealClaw execution abstraction: quote -> route -> receipt.
- FinPos position plan and QTMRL/A2C-style policy scoring.
- FinMem-inspired JSONL memory and ATLAS prompt variant feedback loop.
- x402 payment policy audit with expected-alpha-vs-cost reasoning.
- Demo-safe fallback modes for unconfigured live providers.

## Verified

```powershell
python -m pytest services\api\tests
python -m unittest discover packages\strategy-selector\tests
python scripts\smoke_test.py
npm run build       # in apps/web
npm run compile     # in contracts
```

Notes:

- The frontend build currently emits only a Vite chunk-size warning.
- Generated caches, build outputs, and runtime JSONL files are not required in git.

## Not Live Yet

- Official ERC-8004 Identity Registry registration is not executed from this repo.
- `SIGNAL_REGISTRY_ADDRESS`, `AGENT_ID`, and `VALIDATOR_ADDRESS` still need real
  deployment values for final on-chain mode.
- Byreal/RealClaw execution is structured and simulated unless credentials are configured.
- Reclaim zkTLS and Phala TEE return deterministic proof metadata unless live credentials are configured.
- x402 payment flow produces auditable payment intents, but facilitator
  `/verify` and `/settle` are not wired as hard dependencies.
- Public app URL and demo video are not filled in.

## Next Best Actions

1. Deploy the single-service app publicly.
2. Deploy or configure the Mantle proof contract path.
3. Host the Agent Card and register it through the official ERC-8004 path.
4. Configure `AGENT_ID`, `VALIDATOR_ADDRESS`, `SIGNAL_REGISTRY_ADDRESS`, and
   `MANTLE_PRIVATE_KEY`.
5. Record one real signal transaction and one reputation feedback transaction.
6. Add 2-3 Mantle-native factors for stronger ecosystem fit.
7. Record the final 2-3 minute demo video.
