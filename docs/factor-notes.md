# Factor Notes

This document keeps the MVP factor scope small and explainable.

## MVP Factors

### Momentum

Purpose:

Identify short-term continuation or reversal pressure.

Frontend explanation:

Positive momentum means recent price action supports trend-following strategies.
Extreme momentum can also trigger reversal risk warnings.

### Volatility

Purpose:

Measure recent uncertainty and position sizing risk.

Frontend explanation:

High volatility reduces confidence and increases slippage risk.

### Trend Strength

Purpose:

Classify whether the market is trending or ranging.

Frontend explanation:

Strong trend conditions favor SuperTrend-style strategies. Range conditions
favor mean-reversion strategies.

### Volume Pressure

Purpose:

Detect whether recent moves are supported by trading activity.

Frontend explanation:

Price moves with stronger volume are treated as more credible than thin moves.

### Funding Rate

Purpose:

Capture leveraged long/short crowding when derivative data is available.

Frontend explanation:

Extreme positive funding may indicate crowded longs and squeeze risk. Extreme
negative funding may indicate crowded shorts.

### Open Interest

Purpose:

Detect leverage buildup and liquidation fragility when derivative data is
available.

Frontend explanation:

Rising open interest during sharp moves can increase liquidation risk.

## Optional Later Factors

These are useful but should not block the MVP:

- MVRV;
- SOPR;
- smart-money wallet flow;
- DEX liquidity shock;
- order book imbalance;
- options implied-volatility skew.

## Factor Hygiene

- Shift features before using them for decisions to reduce look-ahead bias.
- Label missing external data clearly.
- Avoid backward-filling low-frequency chain metrics.
- Winsorize extreme standardized values when shown in the UI.
- Keep factor explanations short enough for a judge to understand quickly.

