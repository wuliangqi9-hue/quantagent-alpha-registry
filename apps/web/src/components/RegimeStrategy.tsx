import type { Selection } from "../types";

type Props = {
  selection: Selection;
};

export function RegimeStrategy({ selection }: Props) {
  return (
    <section className="panel span-4">
      <h2>Regime & Strategy</h2>
      <div className="strategy-hero">
        <span>{selection.signalDirection}</span>
        <strong>{selection.strategyName}</strong>
      </div>
      <div className="metric">
        <span>Market regime</span>
        <strong>{selection.marketRegime}</strong>
      </div>
      <div className="metric">
        <span>Selected strategy</span>
        <strong>{selection.strategyName}</strong>
      </div>
      <div className="metric">
        <span>Signal</span>
        <strong>{selection.signalDirection}</strong>
      </div>
      <div className="metric">
        <span>Confidence</span>
        <strong>{(selection.confidence * 100).toFixed(0)}%</strong>
      </div>
      <p style={{ color: "var(--muted)", fontSize: "0.9rem" }}>{selection.explanation}</p>
      {selection.alphaFormula && (
        <div className="formula-box">
          <span>AlphaGPT formula</span>
          <code>{selection.alphaFormula}</code>
          <p>{selection.formulaRationale}</p>
        </div>
      )}
      <h2>Key drivers</h2>
      <ul className="drivers">
        {selection.topDrivers.map((d) => (
          <li key={d}>{d}</li>
        ))}
      </ul>
    </section>
  );
}