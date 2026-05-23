# Milestones

The goal is a stable public demo with a clear Mantle proof story.

## Completed MVP Foundations

- Scope locked around factor engine, strategy selector, dashboard, and signal registry.
- Offline BTC, ETH, and SOL sample data added.
- Factor engine wrapper adapted from existing crypto factor work.
- Strategy selector implemented with regime classification and benchmark evidence.
- FastAPI service exposes `/api/*` routes.
- React dashboard shows factors, strategy decision, risk, benchmark evidence, and proof state.
- `SignalRegistry` contract now covers ERC-8004-inspired identity, validation, and reputation.
- Byreal/RealClaw adapter and reputation settlement endpoint exist.
- Docker single-service deployment path exists.
- Submission pitch, demo outline, and checklist exist.

## Remaining Before Final Submission

1. Deploy the public app.
2. Deploy `SignalRegistry` to Mantle Sepolia or the official required network.
3. Register the QuantAgent identity and set `AGENT_ID`.
4. Configure the public service with `SIGNAL_REGISTRY_ADDRESS`, `VALIDATOR_ADDRESS`, and a funded signing key.
5. Record at least one real signal and save the Mantle explorer link.
6. Settle at least one signal and save the reputation feedback evidence.
7. Record the 2-3 minute demo video.
8. Submit public URL, repository, video, and contract/explorer link.

## Definition of Final Done

- The submitted demo URL is public and not localhost.
- `/api/health` works from the public URL.
- Analyze works for BTC, ETH, and SOL.
- Proof panel shows either a real Mantle explorer link or clearly labeled demo-proof mode.
- Final on-chain mode shows agent identity, validation request, and reputation feedback.
- README explains setup, deployment, architecture, limitations, and value proposition.
- Submission materials can be understood without live narration.
