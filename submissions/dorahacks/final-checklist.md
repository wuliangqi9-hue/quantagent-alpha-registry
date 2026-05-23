# Final Submission Checklist

## Required Links

- Public app URL
- Demo URL is not `localhost`, `127.0.0.1`, or a private LAN address
- GitHub repository
- Demo video
- Contract address or Mantle explorer transaction
- Registered agentId from the `Registered` event
- Validation request transaction or event
- Reputation feedback transaction or event

## Required Materials

- README with local setup and public deployment instructions
- Architecture diagram or architecture section
- One-line pitch
- Short project description
- Track selection
- Known limitations

## Technical Checks

- `/api/health` is reachable from the public URL
- Analyze works for BTC, ETH, and SOL
- Offline demo fallback tested
- Mantle proof panel clearly shows real-onchain or demo-proof mode
- Agent Passport shows identity, validation, reputation, and Byreal adapter status
- `AGENT_ID` and `VALIDATOR_ADDRESS` are configured for final recording
- `Record on Mantle` uses the `identity+validation` registry path
- `Settle Reputation` has been run at least once after a recorded signal
- `.env` final deployment is not left in mock-only mode
- `PRIVATE_MEMPOOL_RPC_URL` is configured if a protected Mantle RPC is available
- Gas values are estimated dynamically; no hardcoded live gas fees are used
- No broken buttons on the main demo path
- No private key or secret is committed

## Narrative Checks

- Does not claim guaranteed profit
- Explains why Mantle is necessary
- Explains how the signal hash links off-chain reasoning to on-chain proof
- Explains how ERC-8004-inspired identity, validation, and reputation close the agent loop
- Explains that Byreal / RealClaw is an execution adapter, while QuantAgent owns the alpha engine
- Mentions factor research and QuantAgent/Hummingbot lineage
