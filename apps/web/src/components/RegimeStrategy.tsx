import type { Selection } from "../types";

type Props = {
  selection: Selection;
};

export function RegimeStrategy({ selection }: Props) {
  const exposure = selection.positionPlan?.targetExposurePct;
  const direction = selection.signalDirection.toUpperCase();

  return (
    <section className="panel span-4">
      <span className="section-kicker">Policy decision</span>
      <h2>Regime & Strategy</h2>
      <div className="strategy-hero">
        <div>
          <span>{selection.marketRegime}</span>
          <strong>{direction}</strong>
        </div>
        <div className="signal-chip">{exposure == null ? "Observe" : `${exposure.toFixed(1)}%`}</div>
      </div>
      <p className="panel-copy">{selection.strategyName}</p>
      <div className="metric">
        <span>Order intent</span>
        <strong>{selection.positionPlan?.orderType || direction}</strong>
      </div>
      <div className="metric">
        <span>Confidence</span>
        <strong>{(selection.confidence * 100).toFixed(0)}%</strong>
      </div>
      {selection.policy && (
        <>
          <div className="metric">
            <span>Policy score</span>
            <strong>{selection.policy.policyScore.toFixed(3)}</strong>
          </div>
          <div className="metric">
            <span>Critic value</span>
            <strong>{selection.policy.criticValue.toFixed(3)}</strong>
          </div>
          <p className="note">{selection.policy.rationale}</p>
        </>
      )}
      <p className="note">{selection.explanation}</p>
      {selection.alphaFormula && (
        <div className="formula-box">
          <span>Alpha formula</span>
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
