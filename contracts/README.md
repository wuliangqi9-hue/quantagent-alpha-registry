# Contracts

Mantle signal-recording layer.

## MVP Scope

The MVP contract records decision proofs only. It should not custody user funds
or execute trades.

## Contract Function

```solidity
recordSignal(bytes32 signalHash, string symbol, string strategyId, string modelVersion, string mode)
```

## Contract Event

```solidity
SignalRecorded(bytes32 indexed signalHash, string symbol, string strategyId, string modelVersion, string mode, uint256 timestamp)
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

For public deployment, set the same address in the hosting provider environment.
Do not commit `contracts/.env` or the root `.env`.
