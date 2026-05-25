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
          <span className="section-kicker">Decision runway</span>
          <h2 className="empty-state-title">Waiting for First Decision</h2>
          <p className="empty-state-desc">
            The workspace is ready to populate market factors, policy sizing, execution route, and proof evidence.
          </p>
        </div>
      </div>
      <div className="empty-grid">
        <div>
          <span>01</span>
          <h2>Factor Graph</h2>
          <p>Momentum, volatility, liquidity, gas, and Mantle-native context feed the first signal.</p>
        </div>
        <div>
          <span>02</span>
          <h2>Position Policy</h2>
          <p>FinPos risk sizing and QTMRL scoring compress the signal into an execution posture.</p>
        </div>
        <div>
          <span>03</span>
          <h2>Proof Bundle</h2>
          <p>zkTLS, TEE, ERC-8004, and reputation feedback become judge-readable evidence.</p>
        </div>
      </div>
    </section>
  );
}
