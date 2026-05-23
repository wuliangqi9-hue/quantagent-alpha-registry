# Architecture Diagram

```mermaid
flowchart TD
  U["User / Judge"] --> W["React Dashboard"]
  W --> API["FastAPI Service"]
  API --> DATA["Live Binance Data or data/sample Fallback"]
  API --> FE["Factor Engine"]
  API --> SS["Strategy Selector"]
  FE --> REPORT["Decision Report"]
  SS --> REPORT
  REPORT --> HASH["SHA-256 Signal Hash"]
  HASH --> CHAIN["SignalRegistry Contract"]
  CHAIN --> EXPLORER["Mantle Explorer Link"]
  REPORT --> W
  EXPLORER --> W
```

## Trust Boundary

- Factor computation and strategy selection happen off-chain.
- The full decision report is hashed off-chain.
- Mantle stores the compact proof, not the entire factor matrix.
- Users can compare the report hash with the chain record.

## MVP Boundary

The MVP records decisions only. It does not custody funds and does not
automatically execute trades.
