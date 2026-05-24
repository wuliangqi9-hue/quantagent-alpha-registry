import { useCallback, useState } from "react";
import type { Analysis, ChainResult, DataMode, Settlement } from "../types";

const API_BASE = import.meta.env.VITE_API_URL || "/api";

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

  const analyze = useCallback(async () => {
    setLoading(true);
    setError(null);
    setChain(null);
    setSettlement(null);
    setSettlementChain(null);
    try {
      const res = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol, mode }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Analyze failed (${res.status})`);
      }
      setData(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [symbol, mode]);

  const recordSignal = useCallback(async () => {
    if (!data) return;
    setRecording(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/record-signal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ useLastAnalysis: true }),
      });
      if (!res.ok) throw new Error(`Record failed (${res.status})`);
      const payload = await res.json();
      setChain(payload.chain);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setRecording(false);
    }
  }, [data]);

  const settleSignal = useCallback(async () => {
    if (!data) return;
    setSettling(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/settle`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ useLastAnalysis: true }),
      });
      if (!res.ok) throw new Error(`Settle failed (${res.status})`);
      const payload = await res.json();
      const s = payload.settlement || {};
      // 将后端可能返回的嵌套字段映射到 Settlement 类型
      setSettlement({
        ...s,
        finposRewards: s.finposRewards ?? s.finpos_rewards ?? undefined,
        compositeScore: s.compositeScore ?? s.composite_score ?? undefined,
        teeAttestation: s.teeAttestation ?? s.tee_attestation ?? undefined,
        zktlsProof: s.zktlsProof ?? s.zktls_proof ?? undefined,
        oproAdaptation: s.oproAdaptation ?? s.opro_adaptation ?? undefined,
      });
      setSettlementChain(payload.chain);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
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
  };
}