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
  "agentId": null,
  "agentConfigured": false,
  "proofMode": "demo-proof",
  "supportedAssets": ["BTC", "ETH", "SOL"],
  "byreal": {"mode": "simulation"},
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
- `analysisId`: short-lived session id required by record and settle calls;
- `signalHash`: hash of the off-chain decision report;
- `factorSummary.factors`: chart-ready factor scores;
- `selection.strategyName`: selected strategy;
- `selection.riskWarnings`: risk caveats;
- `contractAddress`: configured registry address, if available;
- `agent`: ERC-8004-inspired identity and reputation status;
- `executionIntent`: Byreal/RealClaw execution adapter intent.

## Agent Status

```bash
curl https://your-public-app.example.com/api/agent
```

Before final submission, this should show a configured contract and a registered
`agentId`.

## Record Signal

```bash
curl -X POST https://your-public-app.example.com/api/record-signal \
  -H "Content-Type: application/json" \
  -d "{\"useLastAnalysis\":true,\"analysisId\":\"<analysisId-from-analyze>\",\"signalHash\":\"<signalHash-from-analyze>\"}"
```

If Mantle credentials are configured, this returns an explorer URL. Otherwise it
returns a clearly labeled demo-proof response.

With `AGENT_ID` and `VALIDATOR_ADDRESS` configured, `registryLayer` should be
`identity+validation`.

## Settle Reputation

```bash
curl -X POST https://your-public-app.example.com/api/settle \
  -H "Content-Type: application/json" \
  -d "{\"useLastAnalysis\":true,\"analysisId\":\"<analysisId-from-analyze>\",\"signalHash\":\"<signalHash-from-analyze>\"}"
```

This compares the latest benchmark-window price movement against the signal
direction, creates a feedback score, and writes it to the reputation layer when
Mantle credentials are configured.
