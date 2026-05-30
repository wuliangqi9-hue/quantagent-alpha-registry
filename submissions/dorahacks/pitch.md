# DoraHacks Pitch

## One-line Pitch

QuantAgent turns crypto factor research into explainable AI trading decisions,
then anchors each signal and settlement as verifiable Mantle reputation
evidence.

## Short Description

QuantAgent Alpha Registry is an AI trading agent for crypto markets. It
computes market, derivative, and Mantle-native factor signals, classifies the
market regime, selects a route and position plan, explains the decision, and
records signal and settlement evidence through an ERC-8004-compatible identity,
validation, and reputation layer on Mantle.

## Problem

AI trading bots are usually black boxes. Users cannot easily see why a strategy
was selected, what data influenced the decision, or whether the decision record
was later changed.

## Solution

QuantAgent computes crypto factors, selects a strategy based on regime and prior
benchmark evidence, explains the decision, and records a compact proof of that
decision on Mantle. After settlement, the agent can write feedback into its
reputation loop, turning a one-off signal into an accountable agent history.

## Required Track Answers

### What data sources are used?

The demo uses BTC, ETH, and SOL market snapshots with factor-engine generated
trend, volatility, momentum, volume, funding, open-interest, gas, and liquidity
features. The architecture includes Reclaim-compatible ZK-TLS proof envelopes so
live HTTPS market data can be attached to signal provenance.

### What role does AI play?

AI is used as the agent reasoning and policy layer. The system produces
multi-agent reports, FinPos position plans, A2C/QTMRL-style policy scores,
execution routes, and adaptive ATLAS prompt feedback after settlement. When an
LLM key is unavailable, the demo falls back to deterministic analyst mode so the
judge flow remains reliable.

### How does it create verifiable value on Mantle?

Each decision report is hashed, anchored on Mantle Sepolia, and later connected
to a PnL settlement and reputation feedback record. The Agent Card exposes the
agent identity, service endpoints, supported trust models, and registry
addresses so other agents or allocators can inspect the agent programmatically.

## Demo Flow

1. Select BTC, ETH, or SOL.
2. Run factor analysis.
3. Inspect regime classification and selected strategy.
4. Review the Agent Passport: identity, validation status, reputation, and Byreal mode.
5. Record the signal proof on Mantle.
6. Settle the latest signal and write reputation feedback.

## Why Mantle

Mantle provides the public execution and proof layer for the agent's decision
trail. The app uses Mantle to make off-chain strategy reasoning auditable,
validator-readable, and reputation-bearing.

## What Is Built

- FastAPI backend with market analysis, proof envelopes, and Mantle writes.
- Factor engine adapted from crypto factor research and Mantle-native signals.
- FinPos + A2C/QTMRL-style policy selection and reward feedback.
- React terminal dashboard with factor charts, agent reasoning, proof evidence, and risk posture.
- Solidity `SignalRegistry` and `ERC8004AgentCard` contracts for identity, validation, and reputation feedback.
- Byreal/RealClaw adapter layer for Mantle ecosystem execution intent and route selection.
- Docker deployment path for a public single-service demo.

## Tracks

- Primary: AI Alpha & Data
- Secondary: AI Trading & Strategy
- Additional fit: Agentic Wallets & Economy, Best UI/UX

## Limitations

The project is a transparent research-to-execution workflow, not a guaranteed
profit product. Benchmarks are workflow evidence and should be interpreted with
slippage, fees, sample size, and regime-shift risk in mind.
