import { useMemo } from "react";
import { motion } from "framer-motion";
import type { Selection } from "../types";

type Props = {
  selection: Selection;
};

function ConfRing({
  value,
  size = 72,
  stroke = 6,
}: {
  value: number;
  size?: number;
  stroke?: number;
}) {
  const r = (size - stroke) / 2;
  const circumference = 2 * Math.PI * r;
  const offset = circumference * (1 - value);
  const color = value >= 0.7 ? "#00e676" : value >= 0.4 ? "#ffd740" : "#ff5252";

  return (
    <div className="conf-ring-container" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* Background ring */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth={stroke}
        />
        {/* Foreground ring */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.2, ease: "easeOut" }}
          style={{ transform: "rotate(-90deg)", transformOrigin: "center" }}
        />
        {/* Inner pulsing dot */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={3}
          fill={color}
          animate={{ opacity: [0.6, 1, 0.6] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
      </svg>
      <div className="conf-ring-value" style={{ color }}>
        {(value * 100).toFixed(0)}%
      </div>
    </div>
  );
}

function RadarScan() {
  return (
    <div className="radar-container">
      <svg viewBox="0 0 120 120" className="radar-svg">
        {/* Concentric rings */}
        <circle cx="60" cy="60" r="50" fill="none" stroke="rgba(0,229,255,0.1)" strokeWidth="1" />
        <circle cx="60" cy="60" r="35" fill="none" stroke="rgba(0,229,255,0.08)" strokeWidth="0.8" />
        <circle cx="60" cy="60" r="20" fill="none" stroke="rgba(0,229,255,0.06)" strokeWidth="0.6" />
        {/* Crosshairs */}
        <line x1="60" y1="10" x2="60" y2="110" stroke="rgba(0,229,255,0.12)" strokeWidth="0.5" />
        <line x1="10" y1="60" x2="110" y2="60" stroke="rgba(0,229,255,0.12)" strokeWidth="0.5" />
        {/* Sweep line */}
        <motion.line
          x1="60"
          y1="60"
          x2="110"
          y2="60"
          stroke="rgba(0,229,255,0.4)"
          strokeWidth="1.5"
          animate={{ rotate: [0, 360] }}
          transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
          style={{ transformOrigin: "60px 60px" }}
        />
        {/* Dots on radar */}
        <motion.circle
          cx="85"
          cy="40"
          r="2.5"
          fill="#00e5ff"
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{ duration: 1.8, repeat: Infinity, delay: 0 }}
        />
        <motion.circle
          cx="35"
          cy="75"
          r="2"
          fill="#ff9100"
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{ duration: 2.2, repeat: Infinity, delay: 0.5 }}
        />
        <motion.circle
          cx="70"
          cy="80"
          r="3"
          fill="#e040fb"
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{ duration: 2.5, repeat: Infinity, delay: 1 }}
        />
      </svg>
    </div>
  );
}

function SignalBar({ value, label }: { value: number; label: string }) {
  const bars = 5;
  const level = Math.min(Math.ceil(value * bars), bars);
  const color = value >= 0.7 ? "var(--accent)" : value >= 0.4 ? "#ffd740" : "var(--danger)";

  return (
    <div className="signal-bar-row">
      <span className="signal-bar-label">{label}</span>
      <div className="signal-bar-track">
        {Array.from({ length: bars }).map((_, i) => (
          <motion.div
            key={i}
            className="signal-bar-segment"
            initial={{ height: 2 }}
            animate={{ height: i < level ? 8 + i * 4 : 2 }}
            transition={{ duration: 0.5, delay: i * 0.1 }}
            style={{
              backgroundColor: i < level ? color : "rgba(255,255,255,0.08)",
            }}
          />
        ))}
      </div>
    </div>
  );
}

export function RegimeStrategy({ selection }: Props) {
  const drivers = selection.topDrivers || [];
  const warnings = selection.riskWarnings || [];
  const policy = selection.policy;
  const direction = selection.directionDecision;
  const directionValue = direction?.direction.toLowerCase();
  const position = selection.positionPlan;

  return (
    <section className="panel span-6">
      <span className="section-kicker">Strategy</span>
      <h2>Market Regime & Route</h2>

      <div className="regime-layout">
        {/* Left: confidence ring + radar */}
        <div className="regime-visual">
          <ConfRing value={selection.confidence} />
          <div style={{ marginTop: 8, textAlign: "center" }}>
            <span className="note">Confidence</span>
          </div>
          <RadarScan />
        </div>

        {/* Right: regime info */}
        <div className="regime-detail">
          <div className="metric">
            <span>Market regime</span>
            <strong>{selection.marketRegime}</strong>
          </div>
          <div className="metric">
            <span>Strategy</span>
            <strong>{selection.strategyName}</strong>
          </div>

          {direction && (
            <div className="metric">
              <span>Direction (FinPos)</span>
              <strong
                style={{
                  color:
                    directionValue === "long"
                      ? "var(--accent)"
                      : directionValue === "short"
                        ? "var(--danger)"
                        : "var(--muted)",
                }}
              >
                {direction.direction}
              </strong>
            </div>
          )}

          {position && (
            <>
              <div className="metric">
                <span>Target exposure</span>
                <strong>{position.targetExposurePct.toFixed(1)}%</strong>
              </div>
              <div className="metric">
                <span>Order type</span>
                <strong>{position.orderType}</strong>
              </div>
              <div className="metric">
                <span>Amount policy</span>
                <strong>{position.amountPolicy}</strong>
              </div>
              <div className="metric">
                <span>Stop loss / TP</span>
                <strong>
                  {position.stopLossBps} / {position.takeProfitBps} bps
                </strong>
              </div>
              <p className="note">{position.positionRationale}</p>
            </>
          )}

          {policy && (
            <>
              <SignalBar value={policy.policyScore} label="Policy Score" />
              <SignalBar value={policy.policyConfidence} label="Policy Conf" />
              <div className="hash">
                Critic: {policy.criticValue.toFixed(3)}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Drivers & Warnings */}
      {drivers.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <h3 style={{ fontSize: "0.85rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--muted)" }}>
            Top Drivers
          </h3>
          <div className="tag-list">
            {drivers.map((d, i) => (
              <motion.span
                key={d}
                className="tag"
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.1 }}
              >
                {d}
              </motion.span>
            ))}
          </div>
        </div>
      )}

      {warnings.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <h3 style={{ fontSize: "0.85rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--danger)" }}>
            Risk Warnings
          </h3>
          <ul className="warning-list">
            {warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <div style={{ marginTop: 12 }}>
        <p className="note">{selection.explanation}</p>
      </div>
    </section>
  );
}
