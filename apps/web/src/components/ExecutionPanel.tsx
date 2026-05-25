import type { Analysis } from "../types";

type Props = {
  data: Analysis;
};

export function ExecutionPanel({ data }: Props) {
  const intent = data.executionIntent;
  const position = data.selection.positionPlan;
  const route = intent?.routeDecision;
  const quote = intent?.quote;
  const selectedRoute = route?.selectedRoute || intent?.routeType || "simulation";
  const venue = route?.venue || quote?.venue || "simulation";
  const slippage = route?.expectedSlippageBps ?? quote?.expectedSlippageBps ?? intent?.expectedSlippageBps ?? 0;
  const action = intent?.action || data.selection.signalDirection;

  return (
    <section className="panel span-4 execution-panel">
      <span className="section-kicker">Route abstraction</span>
      <h2>Execution & Position</h2>
      <div className="execution-route">
        <div className="route-step done">
          <span>01</span>
          <strong>Quote</strong>
          <small>{venue}</small>
        </div>
        <div className="route-step done">
          <span>02</span>
          <strong>{selectedRoute}</strong>
          <small>{slippage} bps expected</small>
        </div>
        <div className={`route-step ${intent?.mevProtectionRequired ? "warn" : "done"}`}>
          <span>03</span>
          <strong>MEV check</strong>
          <small>{intent?.mevProtectionRequired ? "Protection required" : "Protection preferred"}</small>
        </div>
      </div>
      <div className="metric">
        <span>Target exposure</span>
        <strong>{position ? `${position.targetExposurePct.toFixed(2)}%` : "N/A"}</strong>
      </div>
      <div className="metric">
        <span>Order type</span>
        <strong>{position?.orderType || intent?.orderType || action || "observe"}</strong>
      </div>
      <div className="metric">
        <span>Route type</span>
        <strong>{selectedRoute}</strong>
      </div>
      <div className="metric">
        <span>Venue</span>
        <strong>{venue}</strong>
      </div>
      <div className="metric">
        <span>Expected slippage</span>
        <strong>{slippage} bps</strong>
      </div>
      <div className="metric">
        <span>Max slippage</span>
        <strong>{intent?.slippageGuard?.maxSlippageBps ?? position?.maxSlippageBps ?? 0} bps</strong>
      </div>
      <div className="metric">
        <span>MEV protection</span>
        <strong>{intent?.mevProtectionRequired ? "Required" : "Preferred"}</strong>
      </div>
      <div className="metric">
        <span>RealClaw max lev.</span>
        <strong>{intent?.realClawMacro?.maxLeverage ?? 0}x</strong>
      </div>
      <div className="metric">
        <span>Execution mode</span>
        <strong>{route?.executionMode || intent?.executionMode || intent?.mode || "simulation"}</strong>
      </div>
      <div className="metric">
        <span>Quote expiry</span>
        <strong>{route?.quoteExpiryUnix || intent?.quoteExpiry || "N/A"}</strong>
      </div>
      {(route?.routeRationale || intent?.routeRationale) && (
        <p className="note">{route?.routeRationale || intent?.routeRationale}</p>
      )}
      {position && <p className="note">{position.positionRationale}</p>}
      <h2 className="subhead">x402</h2>
      <p className="note">
        {(intent?.x402 as { approved?: boolean; mode?: string } | undefined)?.approved
          ? `Micropayment approved via ${(intent?.x402 as { mode?: string }).mode}`
          : "Micropayment held or simulated until alpha value and credentials justify payment."}
      </p>
      {(intent?.x402 as { paymentAudit?: { reason?: string; expectedAlphaUsd?: number; totalCostUsd?: number } } | undefined)?.paymentAudit && (
        <p className="note">
          {(intent?.x402 as { paymentAudit: { reason?: string; expectedAlphaUsd?: number; totalCostUsd?: number } }).paymentAudit.reason}
        </p>
      )}
    </section>
  );
}
