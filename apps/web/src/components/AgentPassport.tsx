import type { CSSProperties } from "react";
import type { Analysis, ChainResult, Settlement } from "../types";

type Props = {
  data: Analysis;
  chain: ChainResult | null;
  settlement: Settlement | null;
};

export function AgentPassport({ data, chain, settlement }: Props) {
  const identity = (data.erc8004Status as { identity?: { agentRegistry?: string; mode?: string; agentURI?: string } } | undefined)?.identity;
  const reputation = (data.erc8004Status as { reputation?: { count?: number; score?: number | null } } | undefined)?.reputation;
  const validation = (data.erc8004Status as { validation?: { validationRegistry?: string; status?: string } } | undefined)?.validation;
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
            ERC-8004-compatible identity, validation request, and reputation feedback loop for the QuantAgent.
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
          <span>Agent registry</span>
          <strong>{identity?.agentRegistry || "eip155 registry pending"}</strong>
        </div>
        <div className="passport-item">
          <span>ERC-8004 mode</span>
          <strong>{identity?.mode || data.agent.proofMode || "fallback-demo"}</strong>
        </div>
        <div className="passport-item">
          <span>Agent URI</span>
          <strong>{identity?.agentURI || data.agent.agentURI || "Pending card URI"}</strong>
        </div>
        <div className="passport-item">
          <span>Validation layer</span>
          <strong>
            {chain?.registryLayer === "identity+validation"
              ? "Signal proof requested"
              : validation?.status || "Awaiting signal"}
          </strong>
        </div>
        <div className="passport-item">
          <span>Validation registry</span>
          <strong>{validation?.validationRegistry || "Not configured"}</strong>
        </div>
        <div className="passport-item">
          <span>Reputation</span>
          <strong>
            {data.agent.reputation
              ? `${data.agent.reputation.count} feedback · ${data.agent.reputation.score.toFixed(4)}`
              : reputation?.count
                ? `${reputation.count} feedback · ${reputation.score ?? "pending"}`
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
