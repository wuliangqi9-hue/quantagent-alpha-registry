import type { CSSProperties } from "react";
import type { Analysis, ChainResult, Settlement } from "../types";

type Props = {
  data: Analysis;
  chain: ChainResult | null;
  settlement: Settlement | null;
};

export function AgentPassport({ data, chain, settlement }: Props) {
  const agentScore = Math.max(
    0,
    Math.min(
      100,
      data?.agent?.reputation
        ? 50 + data.agent.reputation.score * 5
        : data
          ? Math.round(data.selection.confidence * 100)
          : 0,
    ),
  );

  return (
    <section className="panel span-12 agent-passport">
      <div className="agent-core">
        <div
          className="agent-orb"
          style={{ "--score-deg": `${agentScore * 3.6}deg` } as CSSProperties}
        >
          <span>{agentScore}</span>
        </div>
        <div>
          <h2>Agent Passport</h2>
          <p>
            ERC-8004-inspired identity, validation request, and reputation feedback loop for the QuantAgent.
          </p>
        </div>
      </div>
      <div className="passport-grid">
        <div className="passport-item">
          <span>Identity</span>
          <strong>
            {data.agent.identityRegistered
              ? `Agent #${data.agent.agentId}`
              : data.agent.agentId
                ? `Agent #${data.agent.agentId} pending`
                : "Not registered"}
          </strong>
        </div>
        <div className="passport-item">
          <span>Validation layer</span>
          <strong>
            {chain?.registryLayer === "identity+validation"
              ? "Signal proof requested"
              : "Awaiting signal"}
          </strong>
        </div>
        <div className="passport-item">
          <span>Reputation</span>
          <strong>
            {data.agent.reputation
              ? `${data.agent.reputation.count} feedback · ${data.agent.reputation.score.toFixed(4)}`
              : settlement
                ? `${settlement.score / 10000} simulated`
                : "No feedback yet"}
          </strong>
        </div>
        <div className="passport-item">
          <span>Byreal / RealClaw</span>
          <strong>{data.byreal.mode}</strong>
        </div>
        <div className="passport-item">
          <span>Execution intent</span>
          <strong>{data.executionIntent.action}</strong>
        </div>
        <div className="passport-item">
          <span>MEV posture</span>
          <strong>
            {chain?.privateMempoolConfigured || data.agent.privateMempoolConfigured
              ? "Private RPC ready"
              : "Public RPC / configure private"}
          </strong>
        </div>
        <div className="passport-item">
          <span>Memory</span>
          <strong>
            {data.memory?.summary
              ? `${data.memory.summary.count} records · ${data.memory.summary.avgPnlBps} bps avg`
              : "No memory yet"}
          </strong>
        </div>
        <div className="passport-item">
          <span>Risk profile</span>
          <strong>{data.selection.riskProfileState || "neutral"}</strong>
        </div>
        <div className="passport-item">
          <span>Alpha formula</span>
          <strong>{data.selection.alphaFormula || "Pending"}</strong>
        </div>
      </div>
    </section>
  );
}