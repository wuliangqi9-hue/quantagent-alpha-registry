# DoraHacks Pitch

## One-line Pitch

QuantAgent turns crypto factor research into an explainable, backtestable, and
on-chain auditable AI trading agent on Mantle.

## Short Description

QuantAgent Alpha Registry is an AI trading research agent for crypto markets. It
computes market, derivative, and on-chain-inspired factors, classifies the
market regime, selects a strategy from a transparent candidate pool, explains
the decision, and records a compact proof of that decision on Mantle.

## Problem

AI trading bots are usually black boxes. Users cannot easily see why a strategy
was selected, what data influenced the decision, or whether the decision record
was later changed.

## Solution

QuantAgent computes crypto factors, selects a strategy based on regime and prior
benchmark evidence, explains the decision, and records a compact proof of that
decision on Mantle.

## Demo Flow

1. Select BTC, ETH, or SOL.
2. Run factor analysis.
3. Inspect regime classification and selected strategy.
4. Review benchmark evidence and risk caveats.
5. Record the signal proof on Mantle or view explicit demo-proof mode.

## Why Mantle

Mantle provides the public execution and proof layer for the agent's decision
trail. The app uses Mantle to make off-chain strategy reasoning auditable.

## What Is Built

- FastAPI backend with live Binance data and offline fallback snapshots.
- Factor engine adapted from prior crypto factor research.
- Strategy selector using SuperTrend, Bollinger, and MACD+Bollinger candidates.
- React dashboard with factor charts, benchmark evidence, and risk warnings.
- Solidity `SignalRegistry` contract for compact decision hash records.
- Docker deployment path for a public single-service demo.

## Tracks

- Primary: AI Trading & Strategy
- Secondary: AI Alpha & Data

## Limitations

The project is a transparent research-to-execution workflow, not a guaranteed
profit product. Benchmarks are workflow evidence and should be interpreted with
slippage, fees, sample size, and regime-shift risk in mind.
