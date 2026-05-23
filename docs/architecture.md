# Architecture Decisions

This document captures the early engineering choices that should keep the
project shippable during the hackathon.

## Architecture Thesis

QuantAgent Alpha Registry should be a simple, reliable, public demo of an
explainable AI trading agent with on-chain decision proofs.

It should not start as a distributed trading platform. The first version should
be a deployable web app plus a lightweight API and one Mantle contract.

## MVP Architecture

```text
public web dashboard
  -> /api routes served by services/api
    -> factor-engine
    -> strategy-selector
    -> explanation builder
    -> Mantle signal recorder
  -> Mantle explorer link
```

## Backend Decision

Use a single API service for the MVP. In production, the API can also serve the
built React dashboard from `apps/web/dist`.

Recommended stack:

- FastAPI or similar lightweight HTTP framework;
- local CSV/JSON snapshots for offline demo mode;
- simple in-memory request flow;
- direct contract call through a wallet key or prepared transaction path.

Avoid for the MVP:

- NATS or Kafka;
- ClickHouse;
- separate worker orchestration;
- autonomous fund custody;
- complex multi-agent scheduling.

These tools are valid later, but they add deployment and debugging risk before
the core demo is proven.

## Data Mode

The app should support two modes:

- `live`: fetch current market data from external APIs when available;
- `offline-demo`: load curated snapshots from `data/sample/`.

The frontend should visibly label which mode is active. Offline mode is not a
failure path; it is a reliability feature for the judge demo.

## Factor Engine Scope

Start with factors that can be explained quickly:

- momentum;
- volatility;
- trend strength;
- volume pressure;
- funding rate, if available;
- open interest, if available;
- basic on-chain activity, if available.

Do not block MVP delivery on hard-to-source metrics like MVRV, SOPR, full wallet
clustering, options surfaces, or tick-level order book imbalance.

## Strategy Selector Scope

The selector should begin as a transparent rules-and-evidence layer over the
existing experiment results.

It should output:

- selected strategy;
- market regime;
- confidence;
- top factor drivers;
- risk warnings;
- benchmark evidence.

LLM-generated prose can be added after deterministic outputs are stable.

## On-chain Scope

The first contract records decision proofs only. It should emit an event with:

- signal hash;
- symbol;
- strategy id;
- model version;
- mode;
- timestamp.

The contract should not hold user funds, execute trades, or manage an autonomous
vault in the MVP.

Proof modes:

- `real-onchain`: contract address and private key are configured, and the API
  submits a Mantle transaction.
- `demo-proof`: contract credentials are missing, so the UI shows a clearly
  labeled backup proof state without pretending a transaction happened.

## Frontend Scope

The first screen must be the usable dashboard, not a landing page.

The dashboard should show:

- selected asset;
- factor radar or bar chart;
- market regime;
- selected strategy;
- confidence and risk warnings;
- benchmark chart;
- Mantle transaction proof.
