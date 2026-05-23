# API Examples

Public deployments should expose these endpoints under `/api/*`.

## Health

```bash
curl https://your-public-app.example.com/api/health
```

Expected shape:

```json
{
  "status": "ok",
  "contractConfigured": false,
  "proofMode": "demo-proof",
  "supportedAssets": ["BTC", "ETH", "SOL"],
  "apiPrefixes": ["", "/api"]
}
```

## Analyze

```bash
curl -X POST https://your-public-app.example.com/api/analyze \
  -H "Content-Type: application/json" \
  -d "{\"symbol\":\"BTC\",\"mode\":\"offline-demo\"}"
```

Important response fields:

- `mode`: `live` or `offline-demo`;
- `signalHash`: hash of the off-chain decision report;
- `factorSummary.factors`: chart-ready factor scores;
- `selection.strategyName`: selected strategy;
- `selection.riskWarnings`: risk caveats;
- `contractAddress`: configured registry address, if available.

## Record Signal

```bash
curl -X POST https://your-public-app.example.com/api/record-signal \
  -H "Content-Type: application/json" \
  -d "{\"useLastAnalysis\":true}"
```

If Mantle credentials are configured, this returns an explorer URL. Otherwise it
returns a clearly labeled demo-proof response.
