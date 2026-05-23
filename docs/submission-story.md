# Submission Story

Use this as the north star for README, DoraHacks fields, and the demo video.

## Core Sentence

QuantAgent Alpha Registry makes AI trading decisions explainable and auditable:
factor reasoning happens off-chain, while agent identity, validation requests,
and reputation feedback are recorded on Mantle.

## What Judges Should Remember

- It is not a chatbot wrapped around a wallet.
- It is not claiming guaranteed alpha.
- It is a transparent agent workflow:
  - compute factors;
  - classify regime;
  - choose strategy;
  - explain risk;
  - record proof on Mantle;
  - settle the signal into reputation feedback.

## Why It Fits The Hackathon

AI Trading & Strategy:

- Agent selects a trading strategy from factor evidence.
- Strategy choice is explainable and benchmark-aware.
- Reputation feedback closes the loop after the signal is settled.

AI Alpha & Data:

- Factors and risk warnings expose useful alpha context.
- Offline fallback and chart-ready summaries make the analysis usable.

Mantle Ecosystem:

- Mantle is the audit trail for agent decisions.
- The proof layer already exposes identity, validation, and reputation surfaces.
- Byreal/RealClaw integration shows a path from alpha generation to Mantle-native execution.

## Differentiator

Most AI trading demos stop at an answer. QuantAgent records the decision trail
and then feeds outcomes back into reputation. That makes the agent inspectable
after the fact instead of being a disposable black-box signal.

## Proof Story

The UI can copy the full decision report JSON. The API hashes that canonical
report and records the compact hash metadata through `SignalRegistry`. With
`AGENT_ID` and `VALIDATOR_ADDRESS` configured, the same transaction opens a
validation request. `/api/settle` then calculates feedback and writes it to the
reputation registry.

## Honest Limitations

- Demo strategy pool is intentionally small.
- Benchmarks are limited workflow evidence.
- Slippage and fees are not fully modeled.
- Real on-chain recording requires a configured contract and funded wallet.
- This MVP records decisions and reputation; it does not custody funds or
  auto-execute trades.
