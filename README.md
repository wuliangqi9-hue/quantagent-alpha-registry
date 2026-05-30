---
title: QuantAgent Demo
emoji: 🔥
colorFrom: blue
colorTo: gray
sdk: docker
pinned: false
---

# QuantAgent Alpha Registry

QuantAgent Alpha Registry is a Mantle Turing Test hackathon project that turns factor research into a verifiable trading workflow. It combines a FastAPI backend, a React terminal UI, and Mantle Sepolia on-chain writes for signal anchoring and reputation feedback.

Live demo: [https://wuliangqi-quantagent-demo.hf.space](https://wuliangqi-quantagent-demo.hf.space)

## What it does

- Generates multi-agent market analysis from BTC, ETH, and SOL factor data
- Selects direction, exposure, and route with FinPos and QTMRL-inspired policy layers
- Anchors signal hashes and settlement feedback on Mantle Sepolia
- Publishes an ERC-8004-compatible Agent Card and identity metadata
- Exposes proof artifacts for zkTLS, TEE, and reputation review

## Current deployment

- Network: Mantle Sepolia
- Chain ID: `5003`
- SignalRegistry: `0x51e36B22FfC325CCE9d57343e187da4b28474e6e`
- ERC8004 Identity Registry: `0x38b9dC3A6E09472c2FEcCD0cACaA7DD62C7f8b26`
- Reputation Registry: `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63`
- Agent ID: `1`
- Agent Card: [`/api/agent/card`](https://wuliangqi-quantagent-demo.hf.space/api/agent/card)

## Architecture

```text
market data -> factor summary -> multi-agent reasoning -> route selection
-> proof bundle -> signal hash -> Mantle write -> settlement -> reputation feedback
```

### Backend

- `services/api/` - FastAPI orchestration, signal recording, settlement, proof bundle generation
- `packages/factor-engine/` - factor extraction and Mantle-native indicators
- `packages/strategy-selector/` - selection, FinPos, QTMRL, and policy blending
- `packages/agent-orchestrator/` - multi-agent report assembly and fallback structured analysis
- `packages/agent-memory/` - settlement memory and ATLAS prompt variants

### Frontend

- `apps/web/` - React + TypeScript dashboard
- Command view with three-column layout
- Agent terminal, proof panel, decision summary, and judging evidence panels
- Responsive mobile fallback

## Run locally

```powershell
python -m pytest services\api\tests -q
cd apps\web
npm run build
npm run dev -- --host 127.0.0.1 --port 5173
```

The API is served by the FastAPI app on `http://127.0.0.1:8000`.

## Environment

Required for live on-chain writes:

```env
MANTLE_RPC_URL=https://rpc.sepolia.mantle.xyz
MANTLE_CHAIN_ID=5003
MANTLE_EXPLORER_BASE=https://explorer.sepolia.mantle.xyz
MANTLE_ENABLE_ONCHAIN_WRITES=true
SIGNAL_REGISTRY_ADDRESS=0x51e36B22FfC325CCE9d57343e187da4b28474e6e
ERC8004_IDENTITY_REGISTRY_ADDRESS=0x38b9dC3A6E09472c2FEcCD0cACaA7DD62C7f8b26
ERC8004_REPUTATION_REGISTRY_ADDRESS=0x8004BAa17C55a88189AE136b182e5fdA19dE9b63
AGENT_ID=1
AGENT_CARD_BASE_URL=https://wuliangqi-quantagent-demo.hf.space
AGENT_URI=https://wuliangqi-quantagent-demo.hf.space/api/agent/card
MANTLE_PRIVATE_KEY=...
```

Optional live adapters:

```env
OPENAI_API_KEY=...
ATLAS_OPRO_ENABLED=true
BYREAL_API_BASE=...
BYREAL_API_KEY=...
RECLAIM_APP_ID=...
RECLAIM_APP_SECRET=...
RECLAIM_VERIFIER_ADDRESS=...
PHALA_TEE_ENABLED=true
PHALA_ENCLAVE_ENDPOINT=...
PHALA_API_KEY=...
BLOCKY402_FACILITATOR_URL=...
X402_WALLET_ADDRESS=...
```

## Public endpoints

- `GET /api/health`
- `GET /api/agent/card`
- `POST /api/analyze`
- `POST /api/record-signal`
- `POST /api/settle`
- `GET /api/memory`

## Submission notes

- The demo is open-source and deployable on Hugging Face Spaces
- On-chain writes target Mantle Sepolia
- The frontend is public and does not require localhost
- Signal and reputation actions are backend-signed, so wallet connection is optional for the demo

## Repo layout

```text
apps/web/                    React dashboard
services/api/                FastAPI backend and on-chain adapters
packages/factor-engine/      Factor computation
packages/strategy-selector/  FinPos and policy selection
packages/agent-memory/       Memory and prompt adaptation
packages/agent-orchestrator/ Multi-agent report assembly
contracts/                   Mantle contracts and deployment scripts
docs/                        Deployment and architecture notes
submissions/dorahacks/       Hackathon submission assets
```
