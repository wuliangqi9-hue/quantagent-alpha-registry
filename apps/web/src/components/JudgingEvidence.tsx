import type { Analysis, ChainResult, Settlement } from "../types";

type Props = {
  data: Analysis;
  chain: ChainResult | null;
  settlement: Settlement | null;
};

type Tone = "live" | "demo" | "warn";

type EvidenceItem = {
  label: string;
  weight?: string;
  status: string;
  tone: Tone;
  detail: string;
  evidence: string;
};

const shortHash = (value: string | null | undefined): string =>
  value ? `${value.slice(0, 8)}...${value.slice(-6)}` : "pending";

const statusTone = (isLive: boolean, isReady = true): Tone => {
  if (isLive) return "live";
  return isReady ? "demo" : "warn";
};

const readX402 = (data: Analysis) =>
  data.executionIntent?.x402 as
    | {
        approved?: boolean;
        mode?: string;
        paymentAudit?: {
          reason?: string;
          expectedAlphaUsd?: number;
          totalCostUsd?: number;
        };
      }
    | undefined;

export function JudgingEvidence({ data, chain, settlement }: Props) {
  const selection = data.selection;
  const policy = selection.policy;
  const route = data.executionIntent?.routeDecision;
  const x402 = readX402(data);
  const hasMantleContract = Boolean(data.contractAddress || data.signalRegistry);
  const ercIdentity = Boolean(data.agent?.identityRegistered || data.agent?.agentId);
  const dataProof = data.dataProof;
  const tee = settlement?.teeAttestation || data.proofBundle?.teeAttestation;
  const zktls = settlement?.zktlsProof || data.proofBundle?.zktlsProof;
  const proofHash = settlement?.proofBundleHash || data.proofBundle?.proofBundleHash;

  const pillars: EvidenceItem[] = [
    {
      label: "Technical Depth",
      weight: "30%",
      status: data.proofBundle ? "Evidence-ready" : "Assembled",
      tone: statusTone(Boolean(data.proofBundle)),
      detail: "AI policy, route abstraction, proof bundle, and reputation feedback are connected in one flow.",
      evidence: `policy ${policy?.policyScore?.toFixed(3) ?? "fallback"} · proof ${shortHash(proofHash)}`,
    },
    {
      label: "Innovation",
      weight: "25%",
      status: "Agentic stack",
      tone: "live",
      detail: "FinPos, QTMRL scoring, zkTLS, TEE, ERC-8004, Byreal routing, and x402 are surfaced as one agent system.",
      evidence: `critic ${policy?.criticValue?.toFixed(3) ?? "N/A"} · route ${route?.selectedRoute || data.executionIntent.routeType}`,
    },
    {
      label: "Mantle Ecosystem",
      weight: "25%",
      status: chain?.recorded ? "Recorded" : hasMantleContract ? "Configured" : "Demo-safe",
      tone: statusTone(Boolean(chain?.recorded || hasMantleContract), true),
      detail: "Signal registry fallback, ERC-8004 registries, and explorer links are ready for Mantle deployment evidence.",
      evidence: data.erc8004?.identityRegistry
        ? `ERC-8004 ${shortHash(data.erc8004.identityRegistry)}`
        : "registry pending",
    },
    {
      label: "Product Integrity",
      weight: "20%",
      status: "Runnable demo",
      tone: "live",
      detail: "Public UI, deterministic offline fallback, schema-stable API, and copyable proof reports support judging.",
      evidence: `${data.symbol} ${selection.signalDirection.toUpperCase()} · ${data.mode}`,
    },
  ];

  const innovations: EvidenceItem[] = [
    {
      label: "FinPos + QTMRL",
      status: policy && selection.positionPlan ? "Active" : "Fallback",
      tone: statusTone(Boolean(policy && selection.positionPlan)),
      detail: "Position-aware direction and risk sizing with policy score, critic value, and reward features.",
      evidence: `exposure ${selection.positionPlan?.targetExposurePct?.toFixed(1) ?? "N/A"}% · score ${policy?.policyScore?.toFixed(3) ?? "N/A"}`,
    },
    {
      label: "Byreal / RealClaw",
      status: data.byreal?.configured ? "Live adapter" : "Simulation",
      tone: statusTone(Boolean(data.byreal?.configured)),
      detail: "Unified quote, route, execute, receipt interface for RFQ, protected CLMM, and simulation modes.",
      evidence: `${route?.venue || data.executionIntent.quote?.venue || "simulation"} · ${route?.expectedSlippageBps ?? data.executionIntent.expectedSlippageBps ?? 0} bps`,
    },
    {
      label: "zkTLS Provenance",
      status: dataProof?.verified || zktls?.verified ? "Verified" : dataProof ? "Envelope" : "Pending",
      tone: statusTone(Boolean(dataProof?.verified || zktls?.verified), Boolean(dataProof || zktls)),
      detail: "Reclaim-compatible proof envelope binds external market data to the decision report.",
      evidence: shortHash(dataProof?.proofHash || zktls?.proofHash),
    },
    {
      label: "TEE Attestation",
      status: tee?.verified ? "Verified" : tee ? "Prepared" : "Settle-ready",
      tone: statusTone(Boolean(tee?.verified), true),
      detail: "Phala-ready attestation object links model output to code measurement and validation anchoring.",
      evidence: tee?.enclavePlatform || "phala-network envelope",
    },
    {
      label: "ERC-8004",
      status: ercIdentity ? "Identity present" : "Compatible",
      tone: statusTone(ercIdentity, true),
      detail: "Agent card, identity, reputation, and validation paths are exposed as a judge-readable passport.",
      evidence: data.agent?.agentId ? `agent #${data.agent.agentId}` : shortHash(data.agentCard?.cardHash),
    },
    {
      label: "x402 Economy",
      status: x402?.approved ? "Payment approved" : "Policy gated",
      tone: statusTone(Boolean(x402?.approved), true),
      detail: "Autonomous data purchase policy compares expected alpha against data, gas, and safety costs.",
      evidence: x402?.paymentAudit?.reason || x402?.mode || "simulated buyer policy",
    },
  ];

  const tracks: EvidenceItem[] = [
    {
      label: "Alpha & Data",
      status: "Primary",
      tone: "live",
      detail: "AI-driven trading strategy with factor evidence, benchmark chart, and recordable chain proof.",
      evidence: `Sharpe ${selection.benchmarkSummary.regimeSharpe.toFixed(2)} · win ${(selection.benchmarkSummary.winRate * 100).toFixed(0)}%`,
    },
    {
      label: "Agentic Economy",
      status: "Primary",
      tone: data.byreal?.configured ? "live" : "demo",
      detail: "Byreal route abstraction, RealClaw capability surface, and x402 buyer policy show agent autonomy.",
      evidence: data.byreal?.mode || "simulation",
    },
    {
      label: "Best UI/UX",
      status: "Candidate",
      tone: "live",
      detail: "New-user friendly proof, route, risk, and reputation views reduce the Web3 inspection burden.",
      evidence: "one-screen evidence map",
    },
    {
      label: "20 Deployment Award",
      status: hasMantleContract ? "Eligible path" : "Needs contract",
      tone: hasMantleContract ? "live" : "warn",
      detail: "Requires verified Mantle contract, public demo URL, demo video, and deployed address in submission.",
      evidence: hasMantleContract ? shortHash(data.contractAddress || data.signalRegistry) : "configure Mantle address",
    },
  ];

  return (
    <section className="judge-evidence span-12" aria-label="Hackathon judging evidence">
      <div className="section-head section-head--inline">
        <span className="section-kicker">Submission narrative</span>
        <h2>Evidence, without the noise</h2>
        <p>
          A compact translation layer between what the product does and how the jury scores it.
          Each claim points back to a visible route, proof, or agent-state surface.
        </p>
      </div>

      <div className="score-grid evidence-strip">
        {pillars.map((item) => (
          <article className="evidence-card" key={item.label}>
            <div className="card-topline">
              <span>{item.label}</span>
              <strong>{item.weight}</strong>
            </div>
            <div className={`status-pill ${item.tone}`}>{item.status}</div>
            <p>{item.detail}</p>
            <code>{item.evidence}</code>
          </article>
        ))}
      </div>

      <details className="evidence-details">
        <summary>Open innovation and track mapping</summary>
        <div className="innovation-grid">
        {innovations.map((item) => (
          <article className="innovation-card" key={item.label}>
            <div>
              <span className="mini-label">{item.label}</span>
              <div className={`status-pill ${item.tone}`}>{item.status}</div>
            </div>
            <p>{item.detail}</p>
            <code>{item.evidence}</code>
          </article>
        ))}
        </div>

        <div className="track-grid">
        {tracks.map((item) => (
          <article className="track-card" key={item.label}>
            <div className="card-topline">
              <span>{item.label}</span>
              <div className={`status-pill ${item.tone}`}>{item.status}</div>
            </div>
            <p>{item.detail}</p>
            <code>{item.evidence}</code>
          </article>
        ))}
        </div>
      </details>
    </section>
  );
}
