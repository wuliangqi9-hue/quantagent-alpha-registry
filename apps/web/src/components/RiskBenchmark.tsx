import type { Selection } from "../types";

type Props = {
  selection: Selection;
};

export function RiskBenchmark({ selection }: Props) {
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
      <h2>Reflection</h2>
      <p style={{ color: "var(--muted)", fontSize: "0.82rem" }}>
        {selection.reflection || "No previous settlement data"}
      </p>
    </section>
  );
}