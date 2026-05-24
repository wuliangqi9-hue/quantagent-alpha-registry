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
  const agent = data.agent ?? {};

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
          <span className="section-kicker">ERC-8004 compatible</span>
          <h2>Agent Passport</h2>
          <p>
            Identity, validation, and reputation stitched into a judge-readable agent profile.
          </p>
        </div>
      </div>
      <div className="passport-sections">
        <div className="passport-group">
          <h3>Identity</h3>
          <dl>
            <div>
              <dt>Agent</dt>
              <dd>
                {agent.identityRegistered
                  ? `#${agent.agentId}`
                  : agent.agentId
                    ? `#${agent.agentId} pending`
                    : "Not registered"}
              </dd>
            </div>
            <div>
              <dt>Registry</dt>
              <dd>{identity?.agentRegistry || "eip155 registry pending"}</dd>
            </div>
            <div>
              <dt>Agent URI</dt>
              <dd>{identity?.agentURI || agent.agentURI || "Pending card URI"}</dd>
            </div>
          </dl>
        </div>
        <div className="passport-group">
          <h3>Trust</h3>
          <dl>
            <div>
              <dt>Mode</dt>
              <dd>{identity?.mode || agent.proofMode || data.proofMode || "fallback-demo"}</dd>
            </div>
            <div>
              <dt>Validation</dt>
              <dd>
                {chain?.registryLayer === "identity+validation"
                  ? "Signal proof requested"
                  : validation?.status || "Awaiting signal"}
              </dd>
            </div>
            <div>
              <dt>Reputation</dt>
              <dd>
                {agent.reputation
                  ? `${agent.reputation.count} feedback · ${agent.reputation.score.toFixed(4)}`
                  : reputation?.count
                    ? `${reputation.count} feedback · ${reputation.score ?? "pending"}`
                  : settlement
                    ? `${settlement.score / 10000} simulated`
                    : "No feedback yet"}
              </dd>
            </div>
          </dl>
        </div>
        <div className="passport-group">
          <h3>Operations</h3>
          <dl>
            <div>
              <dt>Byreal</dt>
              <dd>{data.byreal?.mode || "simulation"}</dd>
            </div>
            <div>
              <dt>MEV</dt>
              <dd>
                {chain?.privateMempoolConfigured || agent.privateMempoolConfigured
                  ? "Private RPC ready"
                  : "Public RPC / configure private"}
              </dd>
            </div>
            <div>
              <dt>Memory</dt>
              <dd>
                {data.memory?.summary
                  ? `${data.memory.summary.count} records · ${data.memory.summary.avgPnlBps} bps avg`
                  : "No memory yet"}
              </dd>
            </div>
          </dl>
        </div>
      </div>
    </section>
  );
}
