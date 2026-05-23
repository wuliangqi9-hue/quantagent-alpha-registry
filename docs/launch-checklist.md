# Launch Checklist

Use this in the final hour before DoraHacks submission.

## Public App

- Public URL opens the dashboard.
- Public URL is not localhost, `127.0.0.1`, or a private LAN address.
- `/api/health` returns `status: ok`.
- `proofMode` is understood and visible.

## Demo Flow

- Analyze works for BTC.
- Analyze works for ETH.
- Analyze works for SOL.
- Offline demo mode works.
- Live mode either works or falls back cleanly.
- Record on Mantle button returns a real explorer link or a clearly labeled
  demo-proof message.
- Copy decision report JSON works.

## Mantle Proof

- Contract address is available if real on-chain mode is used.
- Explorer link opens.
- Signal hash in the UI matches the recorded transaction metadata.
- No private key is present in the repository or public logs.

## Submission Package

- README is current.
- Pitch is concise.
- Demo video is 2-3 minutes.
- Architecture diagram is available.
- Limitations are stated honestly.
- Repository excludes `node_modules`, `.venv`, `.env`, and bulky generated files.
