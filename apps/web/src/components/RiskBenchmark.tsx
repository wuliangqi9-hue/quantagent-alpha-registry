import type { Selection, Settlement } from "../types";

type Props = {
  selection: Selection;
  settlement?: Settlement | null;
};

const formatBps = (bps: number): string => {
  const pct = (bps / 100).toFixed(2);
  return bps >= 0 ? `+${pct}%` : `${pct}%`;
};

const scoreTone = (score: number): string => {
  if (score >= 0.6) return "metric-positive";
  if (score >= 0.3) return "metric-caution";
  return "metric-negative";
};

export function RiskBenchmark({ selection, settlement }: Props) {
  const finpos = settlement?.finposRewards;

  return (
    <section className="panel span-3 risk-panel">
      <span className="section-kicker">Risk desk</span>
      <h2>Risk</h2>
      <div className="warning-stack">
        {selection.riskWarnings.map((w) => (
          <div className="warning-item" key={w}>{w}</div>
        ))}
      </div>
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
      <p className="note">{selection.benchmarkSummary.note}</p>

      {/* ── FinPos Multi-Timescale Rewards ── */}
      {finpos && (
        <>
          <h2>FinPos Multi-Timescale</h2>
          <div className="metric">
            <span>Immediate PnL</span>
            <strong className={finpos.immediatePnlBps >= 0 ? "metric-positive" : "metric-negative"}>
              {formatBps(finpos.immediatePnlBps)}
            </strong>
          </div>
          <div className="metric">
            <span>Direction Correct</span>
            <strong className={finpos.directionCorrect ? "metric-positive" : "metric-negative"}>
              {finpos.directionCorrect ? "yes" : "no"}
            </strong>
          </div>

          {/* Short Window */}
          <div className="reward-window">
            <div>
              Short Window ({finpos.shortWindow.windowSize}d)
            </div>
            <div>
              <span>PnL: <strong>{formatBps(finpos.shortWindow.pnlBps)}</strong></span>
              <span>Sharpe: <strong>{finpos.shortWindow.sharpe.toFixed(2)}</strong></span>
              <span>Win: <strong>{(finpos.shortWindow.winRate * 100).toFixed(0)}%</strong></span>
            </div>
          </div>

          {/* Medium Window */}
          <div className="reward-window">
            <div>
              Medium Window ({finpos.mediumWindow.windowSize}d)
            </div>
            <div>
              <span>PnL: <strong>{formatBps(finpos.mediumWindow.pnlBps)}</strong></span>
              <span>Sharpe: <strong>{finpos.mediumWindow.sharpe.toFixed(2)}</strong></span>
              <span>Win: <strong>{(finpos.mediumWindow.winRate * 100).toFixed(0)}%</strong></span>
            </div>
          </div>

          {/* Exposure Penalty */}
          <div className="metric metric-spaced">
            <span>Exposure Penalty</span>
            <strong className="metric-caution">
              {finpos.exposurePenaltyBps.toFixed(1)} bps
            </strong>
          </div>

          {/* Composite Score */}
          <div className="score-tile">
            <span>
              FinPos Composite Score
            </span>
            <strong className={scoreTone(finpos.compositeScore)}>
              {finpos.compositeScore.toFixed(3)}
            </strong>
          </div>
        </>
      )}

      <h2>Reflection</h2>
      <p className="note">
        {selection.reflection || "No previous settlement data"}
      </p>
    </section>
  );
}
