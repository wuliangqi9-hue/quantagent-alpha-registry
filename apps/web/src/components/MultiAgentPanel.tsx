import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AGENT_COLORS } from "./AgentTerminal";
import type { MultiAgentContext, Selection, OproAdaptation } from "../types";

type AgentSlot = {
  key: string;
  label: string;
  color: string;
  content: string | undefined;
};

type Props = {
  multiAgent: MultiAgentContext | undefined;
  selection: Selection;
  isAnalyzing: boolean;
  oproAdaptation?: OproAdaptation | null;
};

export function MultiAgentPanel({
  multiAgent,
  selection,
  isAnalyzing,
  oproAdaptation,
}: Props) {
  const indicatorReport =
    multiAgent?.indicatorReport ??
    selection.multiAgentContext?.indicatorReport;
  const flowReport =
    multiAgent?.flowReport ?? selection.multiAgentContext?.flowReport;
  const memoryReport =
    multiAgent?.memoryReport ?? selection.memoryContextSummary;
  const reputationReport =
    multiAgent?.reputationReport ??
    selection.multiAgentContext?.reputationReport ??
    selection.reputationImpact;
  const riskReport =
    multiAgent?.riskReport ??
    selection.multiAgentContext?.riskReport ??
    (multiAgent?.riskCriticWarnings?.length
      ? multiAgent.riskCriticWarnings.join("\n")
      : selection.multiAgentContext?.riskCriticWarnings?.join("\n"));

  const [visibleSlots, setVisibleSlots] = useState<number>(0);

  const slots: AgentSlot[] = [
    { key: "indicator", label: "Indicator Agent", color: AGENT_COLORS.Indicator, content: indicatorReport },
    { key: "flow", label: "Flow Agent", color: AGENT_COLORS.Flow, content: flowReport },
    { key: "memory", label: "Memory Agent", color: AGENT_COLORS.Memory, content: memoryReport },
    { key: "reputation", label: "Reputation Agent", color: AGENT_COLORS.Reputation, content: reputationReport },
    ...(riskReport
      ? [{ key: "risk", label: "Risk Agent", color: AGENT_COLORS.Quantity, content: riskReport }]
      : []),
  ];

  // Slot-by-slot reveal on analysis start
  useEffect(() => {
    if (!isAnalyzing) {
      // Show all immediately when not analyzing
      setVisibleSlots(slots.length);
      return;
    }

    setVisibleSlots(0);
    if (slots.length === 0) return;

    let idx = 0;
    const timer = setInterval(() => {
      idx++;
      setVisibleSlots(idx);
      if (idx >= slots.length) clearInterval(timer);
    }, 600);

    return () => clearInterval(timer);
  }, [isAnalyzing, slots.length]);

  return (
    <section className="panel span-12">
      <span className="section-kicker">Collaborative reasoning</span>
      <div className="panel-heading-row">
        <h2>Multi-Agent Research Loop</h2>
        {isAnalyzing && (
          <motion.span
            className="terminal-badge"
            animate={{ opacity: [1, 0.4, 1] }}
            transition={{ duration: 1.2, repeat: Infinity }}
          >
            RUNNING
          </motion.span>
        )}
      </div>

      <div className="agent-report-grid">
        <AnimatePresence>
          {slots.map((slot, idx) => {
            if (idx >= visibleSlots) return null;
            return (
              <motion.div
                key={slot.key}
                className="agent-slot"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.35, ease: "easeOut" }}
                style={{ borderLeftColor: slot.color }}
              >
                <span className="agent-slot-label" style={{ color: slot.color }}>
                  {slot.label}
                </span>
                <p>
                  {slot.content ? (
                    <TypewriterText text={slot.content} enabled={isAnalyzing && idx === visibleSlots - 1} />
                  ) : (
                    <span className="note">Waiting for input…</span>
                  )}
                </p>
                {slot.key === "indicator" && selection.policy && (
                  <div className="metric">
                    <span>A2C Critic value</span>
                    <strong>{selection.policy.criticValue.toFixed(3)}</strong>
                  </div>
                )}
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>

      {/* ATLAS / OPRO adaptation highlight */}
      {oproAdaptation && (
        <motion.div
          className="atlas-box"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          <div className="atlas-header">
            <span className="atlas-title">ATLAS Adaptive-OPRO</span>
            <span className="atlas-iter">Iteration #{oproAdaptation.iteration}</span>
          </div>
          <div className="atlas-mutations">
            {oproAdaptation.mutations.map((m, i) => (
              <span key={i} className="atlas-mutation-tag">{m}</span>
            ))}
          </div>
          <div className="metric">
            <span>Performance Δ</span>
            <strong className={oproAdaptation.performanceDelta >= 0 ? "metric-positive" : "metric-negative"}>
              {oproAdaptation.performanceDelta > 0 ? "+" : ""}
              {oproAdaptation.performanceDelta.toFixed(4)}
            </strong>
          </div>
          <p className="note">{oproAdaptation.rationale}</p>
        </motion.div>
      )}
    </section>
  );
}

// Mini typewriter component
function TypewriterText({ text, enabled }: { text: string; enabled: boolean }) {
  const [displayed, setDisplayed] = useState(enabled ? "" : text);

  useEffect(() => {
    if (!enabled) {
      setDisplayed(text);
      return;
    }
    setDisplayed("");
    let idx = 0;
    const timer = setInterval(() => {
      idx++;
      setDisplayed(text.slice(0, idx));
      if (idx >= text.length) clearInterval(timer);
    }, 12);
    return () => clearInterval(timer);
  }, [text, enabled]);

  return <>{displayed || <span className="cursor-blink">▌</span>}</>;
}
