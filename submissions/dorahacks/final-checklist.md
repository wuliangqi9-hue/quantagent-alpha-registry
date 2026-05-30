# Final Submission Checklist

## Required Links

- Public app URL: `https://wuliangqi-quantagent-demo.hf.space`
- Demo URL is not `localhost`, `127.0.0.1`, or a private LAN address
- GitHub repository: `https://github.com/wuliangqi9-hue/quantagent-alpha-registry`
- Demo video
- Contract address or Mantle explorer transaction:
  - `SignalRegistry`: `0x51e36B22FfC325CCE9d57343e187da4b28474e6e`
  - `ERC8004AgentCard`: `0x38b9dC3A6E09472c2FEcCD0cACaA7DD62C7f8b26`
- Registered agentId from the `Registered` event: `1`
- Agent registration transaction: `0x8e69fdb2b011c607b92f2b05ef19cf661004520e311bf457520003d2ede2ae1e`
- Signal record transaction: `0xbff86ebeb0db60905d082a9b300db7d950051552e6fba35be2b65d319b707272`
- Reputation feedback transaction: `0xeba460e73ac9159913ce97363f0919b46ed2a69152f5b0610ca221ad6ea11851`

## Required Materials

- README with local setup and public deployment instructions: ready
- Architecture diagram or architecture section: ready
- One-line pitch: ready
- Short project description: ready
- Track selection: ready
- Known limitations: ready

## Technical Checks

- `/api/health` is reachable from the public URL
- Analyze works for BTC, ETH, and SOL
- Offline demo fallback tested
- Mantle proof panel clearly shows real-onchain or demo-proof mode
- Agent Passport shows identity, validation, reputation, and Byreal adapter status
- `AGENT_ID` and `VALIDATOR_ADDRESS` are configured for final recording
- `Record signal` writes a live Mantle signal transaction
- `Settle reputation` has been run at least once after a recorded signal
- `.env` final deployment is not left in mock-only mode
- `PRIVATE_MEMPOOL_RPC_URL` is configured if a protected Mantle RPC is available
- Gas values are estimated dynamically; no hardcoded live gas fees are used
- No broken buttons on the main demo path
- No private key or secret is committed

## Narrative Checks

- Does not claim guaranteed profit
- Explains why Mantle is necessary
- Explains how the signal hash links off-chain reasoning to on-chain proof
- Explains how ERC-8004-compatible identity, validation, and reputation close the agent loop
- Explains that Byreal / RealClaw is an execution adapter, while QuantAgent owns the alpha engine
- Mentions factor research and QuantAgent/Hummingbot lineage
