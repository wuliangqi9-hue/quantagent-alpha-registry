export function EmptyState() {
  return (
    <section className="panel span-12">
      <div className="empty-state-illustration" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" />
          <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
      </div>
      <h2 className="empty-state-title">Analysis Ready</h2>
      <p className="empty-state-desc">Select an asset and click Analyze to run a clean factor-backed pipeline with proof, execution, and reputation views prepared.</p>
      <div className="empty-grid">
        <div>
          <h2>Decision Ready</h2>
          <p>Choose an asset and run a clean factor-backed analysis with proof, execution, and reputation views prepared.</p>
        </div>
        <div>
          <h2>Auditable by Design</h2>
          <p>Every signal is shaped for inspection: off-chain reasoning, deterministic proof envelopes, and Mantle accountability.</p>
        </div>
      </div>
    </section>
  );
}