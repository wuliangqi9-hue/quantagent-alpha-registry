import type { Selection, Settlement } from "../types";

type Props = {
  selection: Selection;
  settlement?: Settlement | null;
};

const formatBps = (bps: number): string => {
  const pct = (bps / 100).toFixed(2);
  return bps >= 0 ? `+${pct}%` : `${pct}%`;
};

const scoreColor = (score: number): string => {
  if (score >= 0.6) return "var(--green, #22c55e)";
  if (score >= 0.3) return "var(--amber, #f59e0b)";
  return "var(--red, #ef4444)";
};

export function RiskBenchmark({ selection, settlement }: Props) {
  const finpos = settlement?.finposRewards;

  return (
    <section className="panel span-3">
      <h2>Risk</h2>
      <ul className="warnings">
        {selection.riskWarnings.map((w) => (
          <li key={w}>{w}</li>
        ))}
      </ul>
      <h2>Benchmark evidence</h2>
      <div className="metric">
        <span>Regime Sharpe</span>
        <strong>{selection.benchmarkSummary.regimeSharpe.toFixed(2)}</strong>
      </div>
      <div className="metric">
        <span>Win rate</span>
        <strong>{(selection.benchmarkSummary.winRate * 100).toFixed(0)}%</strong>
      </div>
      <div className="metric">
        <span>Max drawdown</span>
        <strong>{selection.benchmarkSummary.maxDrawdownPct}%</strong>
      </div>
      <p style={{ color: "var(--muted)", fontSize: "0.8rem" }}>
        {selection.benchmarkSummary.note}
      </p>

      {/* ── FinPos Multi-Timescale Rewards ── */}
      {finpos && (
        <>
          <h2>FinPos Multi-Timescale</h2>
          <div className="metric">
            <span>Immediate PnL</span>
            <strong style={{ color: finpos.immediatePnlBps >= 0 ? "var(--green, #22c55e)" : "var(--red, #ef4444)" }}>
              {formatBps(finpos.immediatePnlBps)}
            </strong>
          </div>
          <div className="metric">
            <span>Direction Correct</span>
            <strong>{finpos.directionCorrect ? "✓" : "✗"}</strong>
          </div>

          {/* Short Window */}
          <div style={{
            marginTop: 8,
            padding: "6px 10px",
            background: "var(--surface2, #1a1a2e)",
            borderRadius: 6,
            fontSize: "0.78rem",
          }}>
            <div style={{ fontWeight: 600, marginBottom: 4, color: "var(--fg, #e0e0e0)" }}>
              Short Window ({finpos.shortWindow.windowSize}d)
            </div>
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
              <span>PnL: <strong>{formatBps(finpos.shortWindow.pnlBps)}</strong></span>
              <span>Sharpe: <strong>{finpos.shortWindow.sharpe.toFixed(2)}</strong></span>
              <span>Win: <strong>{(finpos.shortWindow.winRate * 100).toFixed(0)}%</strong></span>
            </div>
          </div>

          {/* Medium Window */}
          <div style={{
            marginTop: 6,
            padding: "6px 10px",
            background: "var(--surface2, #1a1a2e)",
            borderRadius: 6,
            fontSize: "0.78rem",
          }}>
            <div style={{ fontWeight: 600, marginBottom: 4, color: "var(--fg, #e0e0e0)" }}>
              Medium Window ({finpos.mediumWindow.windowSize}d)
            </div>
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
              <span>PnL: <strong>{formatBps(finpos.mediumWindow.pnlBps)}</strong></span>
              <span>Sharpe: <strong>{finpos.mediumWindow.sharpe.toFixed(2)}</strong></span>
              <span>Win: <strong>{(finpos.mediumWindow.winRate * 100).toFixed(0)}%</strong></span>
            </div>
          </div>

          {/* Exposure Penalty */}
          <div className="metric" style={{ marginTop: 8 }}>
            <span>Exposure Penalty</span>
            <strong style={{ color: "var(--amber, #f59e0b)" }}>
              {finpos.exposurePenaltyBps.toFixed(1)} bps
            </strong>
          </div>

          {/* Composite Score */}
          <div style={{
            marginTop: 8,
            padding: "8px 12px",
            background: "var(--surface1, #16213e)",
            borderRadius: 6,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}>
            <span style={{ fontWeight: 600, color: "var(--fg, #e0e0e0)" }}>
              FinPos Composite Score
            </span>
            <strong style={{
              fontSize: "1.2rem",
              color: scoreColor(finpos.compositeScore),
            }}>
              {finpos.compositeScore.toFixed(3)}
            </strong>
          </div>
        </>
      )}

      <h2>Reflection</h2>
      <p style={{ color: "var(--muted)", fontSize: "0.82rem" }}>
        {selection.reflection || "No previous settlement data"}
      </p>
    </section>
  );
}
