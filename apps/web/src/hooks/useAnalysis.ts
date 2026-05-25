import { useCallback, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import type { Analysis, ChainResult, DataMode, OproAdaptation, Settlement } from "../types";

const API_BASE = import.meta.env.VITE_API_URL || "/api";

export type TerminalMessage = {
  id: number;
  agent: string;
  text: string;
  time: string;
};

function timeStamp() {
  return new Date().toLocaleTimeString("en-US", { hour12: false });
}

function buildTerminalMessages(analysis: Analysis | null): TerminalMessage[] {
  if (!analysis) return [];
  const msgs: TerminalMessage[] = [];
  let id = 0;
  const s = analysis.selection;

  if (s.multiAgentContext?.indicatorReport) {
    msgs.push({ id: id++, agent: "Indicator", text: s.multiAgentContext.indicatorReport, time: timeStamp() });
  }
  if (s.multiAgentContext?.flowReport) {
    msgs.push({ id: id++, agent: "Flow", text: s.multiAgentContext.flowReport, time: timeStamp() });
  }
  if (s.memoryContextSummary) {
    msgs.push({ id: id++, agent: "Memory", text: s.memoryContextSummary, time: timeStamp() });
  }
  if (s.multiAgentContext?.reputationReport || s.reputationImpact) {
    msgs.push({ id: id++, agent: "Reputation", text: s.multiAgentContext?.reputationReport ?? s.reputationImpact ?? "", time: timeStamp() });
  }
  if (s.multiAgentContext?.riskReport) {
    msgs.push({ id: id++, agent: "Risk", text: s.multiAgentContext.riskReport, time: timeStamp() });
  }
  if (s.directionDecision?.reasoning) {
    msgs.push({ id: id++, agent: "Direction", text: s.directionDecision.reasoning, time: timeStamp() });
  }
  if (s.positionPlan?.positionRationale) {
    msgs.push({ id: id++, agent: "Quantity", text: s.positionPlan.positionRationale, time: timeStamp() });
  }
  if (s.policy?.rationale) {
    msgs.push({ id: id++, agent: "Orchestrator", text: s.policy.rationale, time: timeStamp() });
  }

  return msgs;
}

async function parseApiError(res: Response, fallback: string): Promise<string> {
  const body = await res.json().catch(() => null);
  if (body && typeof body.detail === "string") return body.detail;
  if (body && typeof body.error === "string") return body.error;
  return `${fallback} (${res.status})`;
}

export function useAnalysis() {
  const [symbol, setSymbol] = useState("BTC");
  const [mode, setMode] = useState<DataMode>("auto");
  const [loading, setLoading] = useState(false);
  const [recording, setRecording] = useState(false);
  const [settling, setSettling] = useState(false);
  const [data, setData] = useState<Analysis | null>(null);
  const [chain, setChain] = useState<ChainResult | null>(null);
  const [settlement, setSettlement] = useState<Settlement | null>(null);
  const [settlementChain, setSettlementChain] = useState<ChainResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  // 存储最近一次 settle 返回的 oproAdaptation
  const [lastOpro, setLastOpro] = useState<OproAdaptation | null>(null);
  // 是否处于分析"进行中"状态（打字机/终端动画播放期间）
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const terminalMessages = useMemo(() => buildTerminalMessages(data), [data]);

  const analyze = useCallback(async () => {
    setLoading(true);
    setIsAnalyzing(true);
    setError(null);
    setChain(null);
    setSettlement(null);
    setSettlementChain(null);
    setLastOpro(null);
    const toastId = toast.loading(`Analyzing ${symbol} with QuantAgent agents...`);
    try {
      const res = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol, mode }),
      });
      if (!res.ok) {
        throw new Error(await parseApiError(res, "Analyze failed"));
      }
      const payload = await res.json();
      setData(payload);
      toast.success("Factor graph, FinPos policy, and proof bundle generated.", { id: toastId });
      setIsAnalyzing(false);
    } catch (e) {
      const message = e instanceof Error ? e.message : "Unknown error";
      setError(message);
      toast.error(message, { id: toastId });
      setIsAnalyzing(false);
    } finally {
      setLoading(false);
    }
  }, [symbol, mode]);

  const recordSignal = useCallback(async () => {
    if (!data) return;
    setRecording(true);
    setError(null);
    const toastId = toast.loading("Submitting canonical signal hash to Mantle...");
    try {
      const res = await fetch(`${API_BASE}/record-signal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ useLastAnalysis: true }),
      });
      if (!res.ok) throw new Error(await parseApiError(res, "Record failed"));
      const payload = await res.json();
      setChain(payload.chain);
      if (payload.chain?.recorded) {
        toast.success("Signal recorded on Mantle. Explorer link is ready.", { id: toastId });
      } else {
        toast.info(payload.chain?.message || "Signal prepared in proof-safe demo mode.", { id: toastId });
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : "Unknown error";
      setError(message);
      toast.error(message, { id: toastId });
    } finally {
      setRecording(false);
    }
  }, [data]);

  const settleSignal = useCallback(async () => {
    if (!data) return;
    setSettling(true);
    setError(null);
    const toastId = toast.loading("Settling PnL and reputation feedback...");
    try {
      const res = await fetch(`${API_BASE}/settle`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ useLastAnalysis: true }),
      });
      if (!res.ok) throw new Error(await parseApiError(res, "Settle failed"));
      const payload = await res.json();
      const s = payload.settlement || {};
      // 将后端可能返回的嵌套字段映射到 Settlement 类型
      const oproAdaptation = (s.oproAdaptation ?? s.opro_adaptation ?? null) as OproAdaptation | null;
      setSettlement({
        ...s,
        finposRewards: s.finposRewards ?? s.finpos_rewards ?? undefined,
        compositeScore: s.compositeScore ?? s.composite_score ?? undefined,
        teeAttestation: s.teeAttestation ?? s.tee_attestation ?? undefined,
        zktlsProof: s.zktlsProof ?? s.zktls_proof ?? undefined,
        oproAdaptation,
      });
      if (oproAdaptation) {
        setLastOpro(oproAdaptation);
        toast.warning("ATLAS-OPRO adapted the next strategy prompt.", { duration: 5200 });
      }
      setSettlementChain(payload.chain);
      if (payload.chain?.recorded) {
        toast.success("Reputation feedback settled on Mantle.", { id: toastId });
      } else {
        toast.info("Settlement computed; on-chain reputation is waiting for live registry config.", { id: toastId });
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : "Unknown error";
      setError(message);
      toast.error(message, { id: toastId });
    } finally {
      setSettling(false);
    }
  }, [data]);

  return {
    symbol,
    setSymbol,
    mode,
    setMode,
    loading,
    recording,
    settling,
    data,
    chain,
    settlement,
    settlementChain,
    error,
    setError,
    analyze,
    recordSignal,
    settleSignal,
    terminalMessages,
    isAnalyzing,
    lastOpro,
  };
}
