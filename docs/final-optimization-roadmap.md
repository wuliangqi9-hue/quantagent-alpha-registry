# QuantAgent Final Optimization Roadmap

This roadmap turns the frontier Agentic AI and cryptographic infrastructure
research into an implementation backlog for the Mantle Turing Test hackathon.
The goal is not to ship every research concept at once, but to make the MVP
progressively closer to a verifiable, position-aware, execution-safe trading
agent.

## North Star

QuantAgent should evolve from an offline factor dashboard into an autonomous
agent with four visible properties:

1. Position-aware decisions: every signal includes direction, target exposure,
   order type, slippage limits, and exit guards.
2. Multi-timescale feedback: settlement writes single-trade PnL, rolling PnL,
   cumulative PnL, drawdown, win rate, and loss streaks back into memory.
3. Execution safety: the API produces an auditable execution intent that prefers
   protected routes, RFQ-style venues, and private mempool paths when risk is high.
4. Cryptographic readiness: identity, reputation, and validation semantics remain
   compatible with the ERC-8004 trustless-agent model.

## P0 Implementation Slice

These items must be code-level features before the final submission.

| Area | Task | Acceptance Signal |
| --- | --- | --- |
| FinPos | Split strategy output into direction and quantity/risk controls. | `selection.positionPlan` includes exposure, slippage, stop-loss, take-profit, and rationale. |
| Settlement | Store multi-timescale performance. | `/api/settle` returns rolling PnL, cumulative PnL, max drawdown, win rate, and consecutive losses. |
| Execution | Expand Byreal/RealClaw execution intent. | `executionIntent` exposes route type, venue preference, slippage guard, MEV requirement, and amount policy. |
| Frontend | Show agent posture in 30 seconds. | Dashboard displays target exposure, order type, execution route, and settlement health. |

## Refactor File Map

|重构路径|涉及的核心任务|外部依赖库与 API|
|---|---|---|
|packages/strategy-selector/|FinPos direction agent and quantity/risk agent; continuous position transitions; crash de-risk tests|packages/factor-engine|
|packages/agent-orchestrator/|QTMRL A2C policy output; multi-agent decision inputs; ATLAS prompt feedback wiring|packages/agent-memory, openai-sdk-ready adapter|
|services/api/|Byreal RFQ/RealClaw execution intent; x402 micropayment middleware; ERC-8004 fixed-point feedback payloads|@byreal-io/agent-skills-ready, Blocky402-ready|
|contracts/|SignalRegistry ERC-8004-inspired registry; QuantAgentExecutor Reclaim proof gate|@reclaimprotocol/verifier-solidity-sdk-compatible|

## P1 Competitive Layer

These deepen the story after P0 is stable.

- Add active data acquisition to `agent-orchestrator`: low confidence or high
  risk triggers additional factor checks before final selection.
- Introduce an Adaptive-OPRO prompt registry that records prompt variants and
  their settlement outcomes.
- Wrap `SignalRegistry` calls with explicit Identity, Validation, and Reputation
  service names so the app reads as ERC-8004 compatible even before full SDK use.
- Add a tiny deterministic alpha-formula evaluator to compare generated formulas
  against realized outcomes.

## P2 Research Interfaces

These should remain adapter-ready until the MVP is stable.

- Reclaim zkTLS proof adapter for external market-data provenance.
- Phala/TEE attestation adapter for private model execution.
- x402 micro-payment client for autonomous paid data access.
- Full Byreal/RealClaw SDK integration for live RFQ and protected routing.
- A2C/QTMRL training loop for long-running strategy weight optimization.

## Engineering Rule

Every new advanced feature must degrade gracefully into offline-demo mode. A
broken credential, missing proof provider, or unavailable venue must never break
the three-minute demo path.
