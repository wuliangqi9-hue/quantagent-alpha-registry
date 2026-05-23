import { useCallback, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const API_BASE = import.meta.env.VITE_API_URL || "/api";
const ASSETS = ["BTC", "ETH", "SOL"];

type Factor = {
  id: string;
  label: string;
  score: number | null;
  missing: boolean;
  explanation: string;
};

type Analysis = {
  symbol: string;
  mode: string;
  signalHash: string;
  modelVersion: string;
  reportSchema: string;
  factorSummary: { factors: Factor[] };
  selection: {
    marketRegime: string;
    strategyId: string;
    strategyName: string;
    strategyDescription: string;
    signalDirection: string;
    confidence: number;
    topDrivers: string[];
    riskWarnings: string[];
    benchmarkSummary: {
      regimeSharpe: number;
      winRate: number;
      maxDrawdownPct: number;
      note: string;
    };
    benchmarkChart: {
      prices: { timestamp: string; close: number }[];
      markers: { timestamp: string; price: number; side: string }[];
      caveats: string[];
    };
    explanation: string;
  };
  contractAddress: string | null;
  explorerBase: string;
  proofMode: string;
  decisionReport: Record<string, unknown>;
};

type ChainResult = {
  recorded?: boolean;
  mock?: boolean;
  proofMode?: string;
  txHash?: string | null;
  explorerUrl?: string | null;
  message?: string;
  error?: string;
};

const shortHash = (value: string | null | undefined) =>
  value ? `${value.slice(0, 10)}…${value.slice(-8)}` : "Not configured";

const proofLabel = (chain: ChainResult | null, hasContract: boolean) => {
  if (chain?.recorded) return "Recorded on Mantle";
  if (chain?.error) return "On-chain attempt failed";
  if (chain?.mock || chain?.proofMode === "demo-proof" || !hasContract) return "Demo-proof mode";
  return "Ready to record";
};

export default function App() {
  const [symbol, setSymbol] = useState("BTC");
  const [mode, setMode] = useState<"auto" | "live" | "offline-demo">("auto");
  const [loading, setLoading] = useState(false);
  const [recording, setRecording] = useState(false);
  const [data, setData] = useState<Analysis | null>(null);
  const [chain, setChain] = useState<ChainResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const analyze = useCallback(async () => {
    setLoading(true);
    setError(null);
    setChain(null);
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
        body: JSON.stringify({
          useLastAnalysis: false,
          signalHash: data.signalHash,
          symbol: data.symbol,
          strategyId: data.selection.strategyId,
          modelVersion: data.modelVersion,
          mode: data.mode,
        }),
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

  const factors =
    data?.factorSummary.factors
      .filter((f) => f.score != null)
      .map((f) => ({ factor: f.label, score: f.score as number })) ?? [];

  const prices = data?.selection.benchmarkChart.prices ?? [];
  const latestPrice = prices.length ? prices[prices.length - 1].close : null;

  const copyReport = useCallback(async () => {
    if (!data) return;
    await navigator.clipboard.writeText(JSON.stringify(data.decisionReport, null, 2));
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }, [data]);

  return (
    <div className="app">
      <header className="header">
        <div className="title">
          <div className="eyebrow">AI Trading & Strategy · AI Alpha & Data · Mantle Proof Layer</div>
          <h1>QuantAgent Alpha Registry</h1>
          <p>
            Explainable crypto factor research, strategy selection, and Mantle decision proofs.
            Transparent research-to-execution workflow, not a profit guarantee.
          </p>
        </div>
        <div className="controls">
          <select value={symbol} onChange={(e) => setSymbol(e.target.value)}>
            {ASSETS.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
          <select value={mode} onChange={(e) => setMode(e.target.value as typeof mode)}>
            <option value="auto">Auto (live → fallback)</option>
            <option value="live">Live</option>
            <option value="offline-demo">Offline demo</option>
          </select>
          <button onClick={analyze} disabled={loading}>
            {loading ? "Analyzing…" : "Analyze"}
          </button>
          <button className="secondary" onClick={recordSignal} disabled={!data || recording}>
            {recording ? "Recording…" : "Record on Mantle"}
          </button>
        </div>
      </header>

      {data && (
        <div className="status-row">
          <span className={`badge ${data.mode === "live" ? "live" : "offline"}`}>
            Data mode: {data.mode}
          </span>
          <span className={`badge ${chain?.recorded ? "live" : "offline"}`}>
            Proof: {proofLabel(chain, Boolean(data.contractAddress))}
          </span>
          <span className="badge">Asset: {data.symbol}</span>
          {latestPrice != null && <span className="badge">Latest close: {latestPrice.toLocaleString()}</span>}
        </div>
      )}

      {error && <div className="error">{error}</div>}

      {!data && !loading && (
        <div className="panel empty">
          <div className="empty-grid">
            <div>
              <h2>Judge demo path</h2>
              <p>Select an asset, run Analyze, inspect the factor-backed strategy decision, then record the signal proof.</p>
            </div>
            <div>
              <h2>Why it matters</h2>
              <p>QuantAgent makes AI trading decisions inspectable: factors off-chain, proof and accountability on Mantle.</p>
            </div>
          </div>
        </div>
      )}

      {data && (
        <div className="grid">
          <section className="panel span-5">
            <h2>Factor Summary</h2>
            <ResponsiveContainer width="100%" height={280}>
              <RadarChart data={factors}>
                <PolarGrid stroke="#334155" />
                <PolarAngleAxis dataKey="factor" tick={{ fill: "#9fb0d0", fontSize: 11 }} />
                <Radar dataKey="score" stroke="#5eead4" fill="#5eead4" fillOpacity={0.35} />
                <Tooltip />
              </RadarChart>
            </ResponsiveContainer>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={factors}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="factor" tick={{ fill: "#9fb0d0", fontSize: 10 }} />
                <YAxis domain={[-3, 3]} tick={{ fill: "#9fb0d0" }} />
                <Tooltip />
                <Bar dataKey="score" fill="#60a5fa" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </section>

          <section className="panel span-4">
            <h2>Regime & Strategy</h2>
            <div className="strategy-hero">
              <span>{data.selection.signalDirection}</span>
              <strong>{data.selection.strategyName}</strong>
            </div>
            <div className="metric">
              <span>Market regime</span>
              <strong>{data.selection.marketRegime}</strong>
            </div>
            <div className="metric">
              <span>Selected strategy</span>
              <strong>{data.selection.strategyName}</strong>
            </div>
            <div className="metric">
              <span>Signal</span>
              <strong>{data.selection.signalDirection}</strong>
            </div>
            <div className="metric">
              <span>Confidence</span>
              <strong>{(data.selection.confidence * 100).toFixed(0)}%</strong>
            </div>
            <p style={{ color: "var(--muted)", fontSize: "0.9rem" }}>{data.selection.explanation}</p>
            <h2>Key drivers</h2>
            <ul className="drivers">
              {data.selection.topDrivers.map((d) => (
                <li key={d}>{d}</li>
              ))}
            </ul>
          </section>

          <section className="panel span-3">
            <h2>Risk</h2>
            <ul className="warnings">
              {data.selection.riskWarnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
            <h2>Benchmark evidence</h2>
            <div className="metric">
              <span>Regime Sharpe</span>
              <strong>{data.selection.benchmarkSummary.regimeSharpe.toFixed(2)}</strong>
            </div>
            <div className="metric">
              <span>Win rate</span>
              <strong>{(data.selection.benchmarkSummary.winRate * 100).toFixed(0)}%</strong>
            </div>
            <div className="metric">
              <span>Max drawdown</span>
              <strong>{data.selection.benchmarkSummary.maxDrawdownPct}%</strong>
            </div>
            <p style={{ color: "var(--muted)", fontSize: "0.8rem" }}>
              {data.selection.benchmarkSummary.note}
            </p>
          </section>

          <section className="panel span-8">
            <h2>Benchmark chart (workflow evidence)</h2>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={prices}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="timestamp" hide />
                <YAxis tick={{ fill: "#9fb0d0" }} domain={["auto", "auto"]} />
                <Tooltip />
                <Line type="monotone" dataKey="close" stroke="#60a5fa" dot={false} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
            <ul className="drivers">
              {data.selection.benchmarkChart.caveats.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          </section>

          <section className="panel span-4">
            <h2>Mantle proof</h2>
            <div className={`proof-state ${chain?.recorded ? "recorded" : "demo"}`}>
              {proofLabel(chain, Boolean(data.contractAddress))}
            </div>
            <div className="metric">
              <span>Signal hash</span>
            </div>
            <div className="hash">{data.signalHash}</div>
            <div className="metric" style={{ marginTop: 12 }}>
              <span>Model version</span>
              <strong style={{ fontSize: "0.75rem" }}>{data.modelVersion}</strong>
            </div>
            <div className="metric">
              <span>Report schema</span>
              <strong style={{ fontSize: "0.75rem" }}>{data.reportSchema}</strong>
            </div>
            <div className="metric">
              <span>API proof mode</span>
              <strong style={{ fontSize: "0.75rem" }}>{data.proofMode}</strong>
            </div>
            {data.contractAddress && (
              <div className="metric">
                <span>Contract</span>
                <strong style={{ fontSize: "0.75rem" }}>{shortHash(data.contractAddress)}</strong>
              </div>
            )}
            {!data.contractAddress && (
              <p className="note">
                Contract not configured. The UI remains demo-safe; set a deployed SignalRegistry address for final submission.
              </p>
            )}
            {chain?.txHash && chain.explorerUrl && (
              <p style={{ marginTop: 12 }}>
                <a href={chain.explorerUrl} target="_blank" rel="noreferrer" style={{ color: "var(--accent)" }}>
                  View on Mantle Explorer
                </a>
              </p>
            )}
            {chain?.message && (
              <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>{chain.message}</p>
            )}
            {chain?.error && <p className="error">{chain.error}</p>}
            <button className="secondary full-width" onClick={copyReport}>
              {copied ? "Decision report copied" : "Copy decision report JSON"}
            </button>
            <p className="note">
              The signal hash is computed from this canonical decision report.
            </p>
          </section>

          <section className="panel span-12 footnote-panel">
            <h2>Submission posture</h2>
            <div className="posture-grid">
              <p>Public demo URL required. Localhost is development-only and must not be submitted.</p>
              <p>Backtests are workflow evidence. The project does not claim guaranteed returns.</p>
              <p>Offline data mode is an intentional fallback for reliable judge demos.</p>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
