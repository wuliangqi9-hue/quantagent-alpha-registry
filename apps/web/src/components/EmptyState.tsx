export function EmptyState() {
  return (
    <section className="panel span-12 empty">
      <div className="empty-hero">
        <div className="empty-state-illustration" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 18h16" />
            <path d="M7 14l3-3 3 2 4-6" />
            <path d="M17 7h3v3" />
          </svg>
        </div>
        <div>
          <span className="section-kicker">Quiet before signal</span>
          <h2 className="empty-state-title">No decision composed yet</h2>
          <p className="empty-state-desc">
            Choose an asset and run analysis. The desk will assemble research, risk, route, and proof into separate rooms
            so the story stays readable.
          </p>
        </div>
      </div>
      <div className="empty-grid">
        <div>
          <span>01</span>
          <h2>Research layer</h2>
          <p>Market texture, Mantle-native context, and factor pressure become the first signal surface.</p>
        </div>
        <div>
          <span>02</span>
          <h2>Policy layer</h2>
          <p>FinPos sizing and QTMRL scoring turn conviction into a bounded execution posture.</p>
        </div>
        <div>
          <span>03</span>
          <h2>Assurance layer</h2>
          <p>Proof envelopes, identity, and reputation feedback make the decision inspectable.</p>
        </div>
      </div>
    </section>
  );
}
