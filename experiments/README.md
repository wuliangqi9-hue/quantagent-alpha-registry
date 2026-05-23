# Experiments

Judge-friendly benchmark evidence is embedded in `packages/strategy-selector/strategy_selector/benchmark.py`.

Prior QuantAgent / Hummingbot backtests live on the desktop at:

- `Desktop/QuantAgent`
- `Desktop/实验/crypto_factor_module`

This hackathon MVP reuses the factor pipeline and transparent selector rules rather than duplicating full backtest infrastructure.

## Provenance

The benchmark constants in the MVP are distilled from prior QuantAgent and
Hummingbot-style experiments:

- rolling-window experiments across BTC, ETH, and SOL;
- market-regime grouping: bull, bear, and range;
- strategy candidates including SuperTrend, Bollinger, and MACD+Bollinger;
- selection logic evaluated as workflow evidence, not production alpha proof.

## How to Present These Results

Use this framing:

> The benchmark evidence demonstrates that the agent can connect factor state,
> market regime, and strategy choice in a reproducible workflow.

Avoid this framing:

> The benchmark proves this agent will make money.

## Next Evidence Upgrade

Before final submission, add a compact CSV or Markdown table with:

- strategy id;
- regime;
- Sharpe;
- win rate;
- max drawdown;
- source experiment file;
- caveat.
