# Sample Data

Offline demo snapshots live here.

## Files

- `btc.csv` — sourced from `crypto_factor_module` sample input (~1200 hourly bars)
- `eth.csv` — scaled derivative of BTC sample
- `sol.csv` — scaled derivative of BTC sample

## Purpose

The demo must continue working if external APIs fail, rate-limit, or respond too
slowly. Offline mode should be clearly labeled in the UI.

## Regenerate ETH/SOL

```powershell
python scripts\make_sample_data.py
```

The generated ETH and SOL files are deterministic scaled variants of the BTC
snapshot. They are for reliable demo coverage only, not market research claims.
