---
title: QuantAgent Demo
emoji: 🤖
colorFrom: blue
colorTo: gray
sdk: docker
pinned: false
---

# 🤖 QuantAgent Alpha Registry

> A trust-minimized AI trading agent network built on ERC-8004-compatible identity, TEE-ready inference, ZK-TLS-ready data provenance, and Mantle on-chain reputation.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Node.js](https://img.shields.io/badge/Node.js-18.x-green.svg)](https://nodejs.org/)
[![Smart Contracts](https://img.shields.io/badge/Contracts-Solidity_0.8.20-363636.svg)](https://soliditylang.org/)

## Live Demo

- Public app: [https://wuliangqi-quantagent-demo.hf.space](https://wuliangqi-quantagent-demo.hf.space)
- Health check: [https://wuliangqi-quantagent-demo.hf.space/api/health](https://wuliangqi-quantagent-demo.hf.space/api/health)
- Agent card: [https://wuliangqi-quantagent-demo.hf.space/api/agent/card](https://wuliangqi-quantagent-demo.hf.space/api/agent/card)
- GitHub repository: [https://github.com/wuliangqi9-hue/quantagent-alpha-registry](https://github.com/wuliangqi9-hue/quantagent-alpha-registry)

## One-Line Pitch

QuantAgent turns crypto factor research into explainable AI trading decisions, then anchors each signal and settlement as verifiable Mantle reputation evidence.

## Why This Matters

AI trading bots are usually black boxes. Users cannot verify which data drove a decision, whether the model followed its stated policy, or whether a later performance claim was rewritten after the fact.

QuantAgent solves that trust gap with a full research-to-reputation loop:

```text
market data -> factor engine -> agent reasoning -> FinPos/A2C policy
-> execution route -> proof bundle -> Mantle signal anchor
-> settlement -> ERC-8004-compatible reputation feedback
```

The goal is not to promise profit. The goal is to make autonomous trading agents inspectable, accountable, and composable inside the Mantle ecosystem.

## Hackathon Track Alignment

| Track | How QuantAgent Fits |
|---|---|
| AI Alpha & Data | Converts market, derivative, and Mantle-native factor data into visible strategy signals and proof bundles. |
| AI Trading & Strategy | Runs an autonomous analysis, policy selection, route selection, signal recording, and settlement loop. |
| Agentic Wallets & Economy | Exposes ERC-8004-compatible identity, reputation feedback, Byreal/RealClaw execution routing, and x402-ready payment policy. |
| Best UI/UX | Uses a professional terminal-style dashboard with agent reasoning, proof state, route state, and judge-facing evidence in one flow. |

## Deployed Mantle Evidence

| Item | Value |
|---|---|
| Network | Mantle Sepolia |
| Chain ID | `5003` |
| Agent wallet / validator | `0x807cb49DA72a147c3CD90c8915eF5FA66c34712b` |
| SignalRegistry | `0x51e36B22FfC325CCE9d57343e187da4b28474e6e` |
| ERC8004AgentCard | `0x38b9dC3A6E09472c2FEcCD0cACaA7DD62C7f8b26` |
| Agent ID | `1` |
| Agent registration tx | [0x8e69...ae1e](https://explorer.sepolia.mantle.xyz/tx/0x8e69fdb2b011c607b92f2b05ef19cf661004520e311bf457520003d2ede2ae1e) |
| Signal record tx | [0xbff8...7272](https://explorer.sepolia.mantle.xyz/tx/0xbff86ebeb0db60905d082a9b300db7d950051552e6fba35be2b65d319b707272) |
| Reputation settlement tx | [0xeba4...1851](https://explorer.sepolia.mantle.xyz/tx/0xeba460e73ac9159913ce97363f0919b46ed2a69152f5b0610ca221ad6ea11851) |

## Core Innovations & Technical Foundations

### 1. ZK-TLS and Data Provenance

In quantitative trading, data authenticity directly affects strategy validity. Traditional oracle flows can introduce centralized trust assumptions. QuantAgent includes a Reclaim-compatible ZK-TLS adapter so external HTTPS market data can be wrapped in a proof envelope before being attached to a decision report.

- Technical basis: Reclaim Protocol style proof envelopes for TLS-origin commitments.
- Research foundation: DECO, *Liberating Web Data Using Decentralized Oracles for TLS* (Zhang et al., ACM CCS 2020).
- Current demo mode: deterministic proof envelopes are available by default; live Reclaim credentials can switch the adapter to production proof generation.

### 2. TEE-Ready Trustless Inference

Data provenance is only half of the trust problem. The agent must also prove that a decision was produced by the stated policy. QuantAgent includes a Phala/TEE-ready adapter that binds model inputs, code measurement, output hash, and settlement metadata into an attestation object.

- Technical basis: enclave-isolated inference using SGX/Nitro/Phala-style remote attestation patterns.
- Research foundation: *Town Crier: An Authenticated Data Feed for Smart Contracts* (Zhang et al., IEEE S&P 2016).
- Current demo mode: deterministic TEE attestation envelopes are available by default; live enclave credentials can enable hardware-backed attestations.

### 3. Regime-Aware A2C Reinforcement Learning

Crypto markets are non-stationary, so static rule selection is fragile. QuantAgent implements a lightweight Advantage Actor-Critic path in `packages/strategy-selector`, using factor state, FinPos position context, reward features, drawdown pressure, and route risk to influence policy blending.

- Technical basis: a pure-Python / NumPy-friendly A2C training path without heavyweight model-serving dependencies.
- Research foundation: *Asynchronous Methods for Deep Reinforcement Learning* (Mnih et al., ICML 2016) and deep reinforcement learning work on algorithmic trading.
- Product value: the UI shows confidence, critic value, position plan, risk flags, and post-settlement reward feedback instead of hiding model behavior.

### 4. ERC-8004-Compatible Agent Tokenization

QuantAgent packages the agent identity, service endpoints, trust models, signal hashes, and reputation feedback into an ERC-8004-compatible agent card and registry flow.

- Technical basis: `ERC8004AgentCard.sol`, `SignalRegistry.sol`, and FastAPI adapters for identity, reputation, and validation metadata.
- Mantle value: low-cost L2 writes make repeated signal anchoring and settlement feedback practical for autonomous agents.
- Ecosystem value: agent reputation can become a reusable primitive for allocators, other agents, and future strategy marketplaces.

## System Architecture

```text
quantagent-alpha-registry/
├── apps/web/                    React + Vite terminal dashboard
├── contracts/                   Hardhat contracts and deployment scripts
├── packages/agent-memory/       settlement memory and adaptive prompt variants
├── packages/agent-orchestrator/ multi-agent reasoning and policy context
├── packages/factor-engine/      market, derivative, and Mantle-native factors
├── packages/strategy-selector/  FinPos, A2C, and strategy selection
├── services/api/                FastAPI API, proof adapters, and chain writes
├── docs/                        architecture, proof, deployment, and judging notes
└── submissions/dorahacks/       pitch, video outline, and final checklist
```

## Demo Flow for Judges

1. Open the public app.
2. Select BTC, ETH, or SOL.
3. Click **Run analysis** to generate factor summary, agent reasoning, policy selection, route selection, and proof bundle.
4. Open the Command or Research room to inspect the factor radar, agent terminal, risk posture, and decision workspace.
5. Click **Record signal** to anchor the current decision hash on Mantle.
6. Click **Settle reputation** to calculate PnL feedback and write the reputation result.
7. Open the Mantle Explorer links shown in the proof panel.

## Local Quick Start

### Prerequisites

- Node.js 18+
- Python 3.10+
- npm or pnpm
- PowerShell, Bash, or another modern shell

### Install and configure

```bash
git clone https://github.com/wuliangqi9-hue/quantagent-alpha-registry.git
cd quantagent-alpha-registry

cp .env.example .env
cp contracts/.env.example contracts/.env
```

### Run the API

```powershell
./scripts/run_api.ps1
```

The API starts on `http://localhost:8000`.

### Run the web app

```powershell
./scripts/run_web.ps1
```

The web app starts on `http://localhost:5173`.

### Compile contracts

```bash
cd contracts
npm install
npx hardhat compile
npx hardhat run scripts/deploy.js --network mantleSepolia
```

## Environment Variables

Required for live Mantle writes:

```env
MANTLE_RPC_URL=https://rpc.sepolia.mantle.xyz
MANTLE_CHAIN_ID=5003
MANTLE_EXPLORER_BASE=https://explorer.sepolia.mantle.xyz
MANTLE_ENABLE_ONCHAIN_WRITES=true
MANTLE_ALLOW_PUBLIC_WRITES=false
ONCHAIN_WRITE_AUTH_TOKEN=...
MANTLE_PRIVATE_KEY=...
SIGNAL_REGISTRY_ADDRESS=0x51e36B22FfC325CCE9d57343e187da4b28474e6e
ERC8004_IDENTITY_REGISTRY_ADDRESS=0x38b9dC3A6E09472c2FEcCD0cACaA7DD62C7f8b26
AGENT_ID=1
AGENT_CARD_BASE_URL=https://wuliangqi-quantagent-demo.hf.space
AGENT_URI=https://wuliangqi-quantagent-demo.hf.space/api/agent/card
```

`MANTLE_ENABLE_ONCHAIN_WRITES=true` means the API has a funded signer and can
build Mantle transactions. Public deployments should keep
`MANTLE_ALLOW_PUBLIC_WRITES=false` and use `ONCHAIN_WRITE_AUTH_TOKEN` for trusted
write sessions. A response labeled `onchain-write-locked` means the decision and
proof bundle were computed, but no new Mantle transaction was broadcast.

Optional live intelligence and proof adapters:

```env
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini
ATLAS_OPRO_ENABLED=true
RECLAIM_APP_ID=...
RECLAIM_APP_SECRET=...
RECLAIM_VERIFIER_ADDRESS=...
PHALA_TEE_ENABLED=true
PHALA_ENCLAVE_ENDPOINT=...
PHALA_API_KEY=...
BYREAL_API_BASE=...
BYREAL_API_KEY=...
BLOCKY402_FACILITATOR_URL=...
X402_WALLET_ADDRESS=...
```

## Verification Commands

```powershell
ruff check packages/ --ignore E402,E501
ruff check services/api/ --ignore E402,E501
python -m compileall packages/agent-memory packages/agent-orchestrator packages/factor-engine packages/strategy-selector services/api/app scripts
python -m unittest discover packages/strategy-selector/tests
python -m pytest services\api\tests -q
cd apps\web && npm run build
cd ..\..\contracts && npm run compile
```

## Known Limitations

- The public demo is configured for Mantle Sepolia. The same deployment scripts and environment variables are designed for production Mantle deployment.
- OpenAI, Reclaim, Phala, Byreal, and x402 adapters are live-ready but require sponsor or provider credentials.
- Deterministic proof envelopes are labeled as demo/simulated proof. They are not presented as live Reclaim zkTLS or hardware TEE verification unless credentials are configured and the adapter reports verified output.
- The project demonstrates verifiable strategy workflow infrastructure; it does not provide investment advice or guaranteed returns.

## Judge Resources

- [Demo script](./docs/demo-script.md)
- [Architecture](./docs/architecture.md)
- [Proof model](./docs/proof-model.md)
- [Judging checklist](./docs/judging-checklist.md)
- [DoraHacks pitch](./submissions/dorahacks/pitch.md)

## Disclaimer

This project contains experimental financial algorithms and smart contracts. It is provided for hackathon demonstration and research purposes only. It is not investment, financial, legal, or tax advice. Always audit contracts and risk controls before using real capital.
