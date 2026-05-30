import { useEffect, useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";

type TerminalMessage = {
  id: number;
  agent: string;
  text: string;
  time: string;
};

type Props = {
  messages: TerminalMessage[];
  isActive: boolean;
};

const AGENT_COLORS: Record<string, string> = {
  Indicator: "#c7d7e8",
  Flow: "#dbc58b",
  Memory: "#c8b8d8",
  Reputation: "#b7d7b8",
  Direction: "#e0d4a8",
  Quantity: "#9dd8cd",
  Orchestrator: "#b9cde6",
  ATLAS: "#df9a9a",
};

export function AgentTerminal({ messages, isActive }: Props) {
  const [visibleMessages, setVisibleMessages] = useState<TerminalMessage[]>([]);
  const [typingText, setTypingText] = useState("");
  const [typingAgent, setTypingAgent] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;

    const sleep = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms));

    async function revealMessages() {
      if (messages.length === 0) {
        setVisibleMessages([]);
        setTypingText("");
        setTypingAgent("");
        return;
      }

      const revealDelay = isActive ? 220 : 90;
      const charDelay = isActive ? 12 : 4;
      setVisibleMessages([]);
      setTypingText("");
      setTypingAgent("");

      for (const msg of messages) {
        if (cancelled) return;
        setTypingAgent(msg.agent);
        setTypingText("");

        for (let i = 0; i < msg.text.length; i += 1) {
          if (cancelled) return;
          setTypingText(msg.text.slice(0, i + 1));
          await sleep(charDelay);
        }

        if (cancelled) return;
        setVisibleMessages((prev) => [...prev, msg]);
        setTypingText("");
        setTypingAgent("");
        await sleep(revealDelay);
      }
    }

    revealMessages();

    return () => {
      cancelled = true;
      setTypingText("");
      setTypingAgent("");
    };
  }, [messages, isActive]);

  // Auto-scroll
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [visibleMessages, typingText]);

  if (messages.length === 0) {
    return (
      <section className="panel span-12">
        <span className="section-kicker">AI cortex</span>
        <h2>Agent Terminal</h2>
        <div className="terminal-empty">
          <div className="terminal-prompt">
            <span className="prompt-sign">{">"}</span>
            <span className="prompt-cursor" />
          </div>
          <p className="note">Run an analysis to watch agent reasoning flow.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="panel span-12 terminal-panel">
      <span className="section-kicker">AI cortex</span>
      <h2>
        Agent Terminal
        {isActive && (
          <motion.span
            className="terminal-badge"
            animate={{ opacity: [1, 0.4, 1] }}
            transition={{ duration: 1.2, repeat: Infinity }}
          >
            LIVE
          </motion.span>
        )}
      </h2>

      <div className="terminal-body" ref={containerRef}>
        <AnimatePresence>
          {visibleMessages.map((msg) => (
            <motion.div
              key={msg.id}
              className="terminal-line"
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2 }}
            >
              <span className="terminal-time">{msg.time}</span>
              <span
                className="terminal-agent"
                style={{ color: AGENT_COLORS[msg.agent] || "#b0bec5" }}
              >
                [{msg.agent}]
              </span>
              <span className="terminal-text">{msg.text}</span>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Typing indicator */}
        {typingText && (
          <motion.div
            className="terminal-line terminal-typing"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <span className="terminal-time">--:--:--</span>
            <span
              className="terminal-agent"
              style={{ color: AGENT_COLORS[typingAgent] || "#b0bec5" }}
            >
              [{typingAgent}]
            </span>
            <span className="terminal-text">
              {typingText}
              <motion.span
                className="cursor-blink"
                animate={{ opacity: [1, 0] }}
                transition={{ duration: 0.5, repeat: Infinity }}
              >
                ▌
              </motion.span>
            </span>
          </motion.div>
        )}
      </div>
    </section>
  );
}

export { AGENT_COLORS };
