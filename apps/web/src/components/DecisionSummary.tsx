import type { Analysis, ChainResult, Settlement } from "../types";

type Props = {
  data: Analysis;
  chain: ChainResult | null;
  settlement: Settlement | null;
  latestPrice: number | null;
};

const formatPct = (value: number | undefined): string =>
  value == null ? "N/A" : `${value.toFixed(2)}%`;

const formatBps = (value: number | undefined): string => {
  if (value == null) return "N/A";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)} bps`;
};

const proofState = (data: Analysis, chain: ChainResult | null): string => {
  if (chain?.recorded) return "Mantle recorded";
  if (chain?.error) return "Record failed";
  if (!data.contractAddress || chain?.mock || data.proofMode === "demo-proof") return "Demo proof";
  return "Ready";
};

export function DecisionSummary({ data, chain, settlement, latestPrice }: Props) {
  const selection = data.selection;
  const position = selection.positionPlan;
  const intent = data.executionIntent;
  const route = intent?.routeDecision;
  const routeType = route?.selectedRoute || intent?.routeType || "simulation";
  const proof = proofState(data, chain);
  const signal = selection.signalDirection.toUpperCase();
  const pnlClass = settlement?.pnlBps == null ? "" : settlement.pnlBps >= 0 ? "positive" : "negative";

  return (
    <section className="decision-summary span-12" aria-label="Decision summary">
      <div className="decision-lead">
        <span className="section-kicker">Live decision chain</span>
        <h2>{data.symbol} · {signal}</h2>
        <p>{selection.explanation}</p>
      </div>
      <div className="summary-metrics">
        <div className="summary-cell primary">
          <span>Confidence</span>
          <strong>{(selection.confidence * 100).toFixed(0)}%</strong>
          <div className="meter">
            <i style={{ width: `${Math.max(4, Math.round(selection.confidence * 100))}%` }} />
          </div>
        </div>
        <div className="summary-cell">
          <span>Target exposure</span>
          <strong>{formatPct(position?.targetExposurePct)}</strong>
          <small>{position?.orderType || intent?.action || selection.signalDirection}</small>
        </div>
        <div className="summary-cell">
          <span>Route</span>
          <strong>{routeType}</strong>
          <small>{route?.venue || intent?.quote?.venue || intent?.provider || "legacy selector"}</small>
        </div>
        <div className="summary-cell">
          <span>Proof</span>
          <strong>{proof}</strong>
          <small>{data.proofBundle?.proofBundleHash ? "Bundle anchored" : data.proofMode}</small>
        </div>
        <div className="summary-cell">
          <span>Latest close</span>
          <strong>{latestPrice == null ? "N/A" : latestPrice.toLocaleString()}</strong>
          <small>{data.mode}</small>
        </div>
        <div className={`summary-cell ${pnlClass}`}>
          <span>Settlement PnL</span>
          <strong>{formatBps(settlement?.pnlBps)}</strong>
          <small>{settlement ? "Reputation feedback ready" : "Awaiting settle"}</small>
        </div>
      </div>
      <div className="decision-pipeline" aria-label="Decision pipeline">
        <span>Market state</span>
        <span>Policy decision</span>
        <span>Execution route</span>
        <span>Proof bundle</span>
      </div>
    </section>
  );
}
