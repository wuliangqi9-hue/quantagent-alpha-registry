export function FootnotePanel() {
  return (
    <section className="panel span-12 footnote-panel">
      <h2>Submission posture</h2>
      <div className="posture-grid">
        <p>Public demo URL required. Localhost is development-only and must not be submitted.</p>
        <p>Backtests are workflow evidence. The project does not claim guaranteed returns.</p>
        <p>Offline data mode is a fallback, but final live judging should use Mantle mainnet configuration.</p>
      </div>
    </section>
  );
}