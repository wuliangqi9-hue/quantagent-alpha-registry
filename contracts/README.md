# Contracts

Mantle agent trust layer.

## MVP Scope

The MVP contract is an ERC-8004-inspired combined registry:

- identity: register an agent NFT and `agentURI`;
- validation: bind each signal hash to a validation request;
- reputation: write feedback after signal settlement.

It should not custody user funds or execute trades.

## Core Functions

```solidity
register(string agentURI)
recordSignalForAgent(uint256 agentId, bytes32 signalHash, string symbol, string strategyId, string modelVersion, string mode, address validatorAddress, string proofURI, bytes32 proofHash)
giveFeedback(uint256 agentId, int128 value, uint8 valueDecimals, string tag1, string tag2, string endpoint, string feedbackURI, bytes32 feedbackHash)
```

`recordSignal(...)` remains available as a backward-compatible legacy path, but
the final hackathon flow should use `recordSignalForAgent(...)`.

## Key Events

```solidity
Registered(uint256 indexed agentId, string agentURI, address indexed owner)
SignalRecorded(uint256 indexed agentId, bytes32 indexed signalHash, ...)
ValidationRequest(address indexed validatorAddress, uint256 indexed agentId, string requestURI, bytes32 indexed requestHash)
NewFeedback(uint256 indexed agentId, address indexed clientAddress, ...)
```

## Deployment

```powershell
cd contracts
npm.cmd install
npm.cmd run compile
```

Copy `contracts/.env.example` to `contracts/.env`, then fill the private key:

```text
MANTLE_RPC_URL=https://rpc.sepolia.mantle.xyz
MANTLE_CHAIN_ID=5003
MANTLE_PRIVATE_KEY=<funded private key>
```

Deploy:

```powershell
npm.cmd run deploy:sepolia
```

Copy the deployed address into the root `.env` as
`SIGNAL_REGISTRY_ADDRESS=<address>`.

Then register the agent through the API:

```bash
curl -X POST https://your-public-app.example.com/api/agent/register \
  -H "Content-Type: application/json" \
  -d "{\"agentURI\":\"https://your-public-app.example.com/agent.json\"}"
```

Read the `Registered` event to get `agentId`, then set:

```text
AGENT_ID=<agentId>
VALIDATOR_ADDRESS=<validator wallet>
```

For public deployment, set the same address in the hosting provider environment.
Do not commit `contracts/.env` or the root `.env`.
