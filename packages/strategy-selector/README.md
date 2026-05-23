# Strategy Selector

Selects a strategy using factor state, market regime, and existing QuantAgent
or Hummingbot benchmark evidence.

## MVP Output

- `strategyId`
- `signalDirection`
- `confidence`
- `marketRegime`
- `topDrivers`
- `riskWarnings`
- `benchmarkSummary`

## Initial Strategy Pool

- SuperTrend
- Bollinger
- MACD + Bollinger

## Evidence Posture

Benchmark values are workflow evidence distilled from prior QuantAgent and
Hummingbot-style experiments. They should be presented as support for the
selector design, not as proof of future profitability.
