import { useCallback, useState, type CSSProperties } from "react";
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
    alphaFormula?: string;
    formulaRationale?: string;
    riskProfileState?: string;
    reputationImpact?: string;
    reflection?: string;
    memoryContextSummary?: string;
    multiAgentContext?: MultiAgentContext;
    explanation: string;
  };
  contractAddress: string | null;
  explorerBase: string;
  proofMode: string;
  agent: AgentStatus;
  byreal: ByrealStatus;
  executionIntent: ExecutionIntent;
  memory?: MemoryContext;
  multiAgent?: MultiAgentContext;
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
  agentId?: number | null;
  registryLayer?: string;
  proofURI?: string | null;
  privateMempoolConfigured?: boolean;
};

type AgentStatus = {
  configured?: boolean;
  identityRegistered?: boolean;
  agentId?: number | null;
  contractAddress?: string | null;
  proofMode?: string;
  privateMempoolConfigured?: boolean;
  owner?: string;
  agentURI?: string;
  reputation?: {
    count: number;
    summaryValue: number;
    decimals: number;
    score: number;
  };
  message?: string;
  error?: string;
};

type ByrealStatus = {
  configured: boolean;
  mode: string;
  apiBase?: string | null;
  skills: string[];
  message: string;
};

type ExecutionIntent = {
  provider: string;
  mode: string;
  asset: string;
  action: string;
  sizeHint: string;
  strategyId: string;
  confidence: number;
  slippagePolicy: string;
  mevPolicy: string;
  notes: string[];
};

type Settlement = {
  signalHash: string;
  symbol: string;
  direction: string;
  entryPrice: number;
  exitPrice: number;
  pnlBps: number;
  confidence: number;
  score: number;
  settlementHash: string;
};

type MemoryContext = {
  summary?: {
    count: number;
    avgPnlBps: number;
    winRate: number;
    latestPnlBps: number | null;
    lastReflection: string;
    lastStrategyId?: string;
  };
  retrieved?: {
    strategyId: string;
    pnlBps: number;
    memoryScore: number;
    reflection: string;
  }[];
};

type MultiAgentContext = {
  indicatorReport?: string;
  flowReport?: string;
  memoryReport?: string;
  reputationReport?: string;
  riskCriticWarnings?: string[];
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
  const [settling, setSettling] = useState(false);
  const [data, setData] = useState<Analysis | null>(null);
  const [chain, setChain] = useState<ChainResult | null>(null);
  const [settlement, setSettlement] = useState<Settlement | null>(null);
  const [settlementChain, setSettlementChain] = useState<ChainResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

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
        body: JSON.stringify({
          useLastAnalysis: true,
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
      setSettlement(payload.settlement);
      setSettlementChain(payload.chain);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setSettling(false);
    }
  }, [data]);

  const factors =
    data?.factorSummary.factors
      .filter((f) => f.score != null)
      .map((f) => ({ factor: f.label, score: f.score as number })) ?? [];

  const prices = data?.selection.benchmarkChart.prices ?? [];
  const latestPrice = prices.length ? prices[prices.length - 1].close : null;
  const agentScore = Math.max(
    0,
    Math.min(
      100,
      data?.agent?.reputation
        ? 50 + data.agent.reputation.score * 5
        : data
          ? Math.round(data.selection.confidence * 100)
          : 0,
    ),
  );

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
          <button className="secondary" onClick={settleSignal} disabled={!data || settling}>
            {settling ? "Settling…" : "Settle Reputation"}
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
          <section className="panel span-12 agent-passport">
            <div className="agent-core">
              <div
                className="agent-orb"
                style={{ "--score-deg": `${agentScore * 3.6}deg` } as CSSProperties}
              >
                <span>{agentScore}</span>
              </div>
              <div>
                <h2>Agent Passport</h2>
                <p>
                  ERC-8004-inspired identity, validation request, and reputation feedback loop for the QuantAgent.
                </p>
              </div>
            </div>
            <div className="passport-grid">
              <div className="passport-item">
                <span>Identity</span>
                <strong>{data.agent.identityRegistered ? `Agent #${data.agent.agentId}` : data.agent.agentId ? `Agent #${data.agent.agentId} pending` : "Not registered"}</strong>
              </div>
              <div className="passport-item">
                <span>Validation layer</span>
                <strong>{chain?.registryLayer === "identity+validation" ? "Signal proof requested" : "Awaiting signal"}</strong>
              </div>
              <div className="passport-item">
                <span>Reputation</span>
                <strong>
                  {data.agent.reputation ? `${data.agent.reputation.count} feedback · ${data.agent.reputation.score.toFixed(4)}` : settlement ? `${settlement.score / 10000} simulated` : "No feedback yet"}
                </strong>
              </div>
              <div className="passport-item">
                <span>Byreal / RealClaw</span>
                <strong>{data.byreal.mode}</strong>
              </div>
              <div className="passport-item">
                <span>Execution intent</span>
                <strong>{data.executionIntent.action}</strong>
              </div>
              <div className="passport-item">
                <span>MEV posture</span>
                <strong>{chain?.privateMempoolConfigured || data.agent.privateMempoolConfigured ? "Private RPC ready" : "Public RPC / configure private"}</strong>
              </div>
              <div className="passport-item">
                <span>Memory</span>
                <strong>{data.memory?.summary ? `${data.memory.summary.count} records · ${data.memory.summary.avgPnlBps} bps avg` : "No memory yet"}</strong>
              </div>
              <div className="passport-item">
                <span>Risk profile</span>
                <strong>{data.selection.riskProfileState || "neutral"}</strong>
              </div>
              <div className="passport-item">
                <span>Alpha formula</span>
                <strong>{data.selection.alphaFormula || "Pending"}</strong>
              </div>
            </div>
          </section>

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
            {data.selection.alphaFormula && (
              <div className="formula-box">
                <span>AlphaGPT formula</span>
                <code>{data.selection.alphaFormula}</code>
                <p>{data.selection.formulaRationale}</p>
              </div>
            )}
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
            <h2>Reflection</h2>
            <p style={{ color: "var(--muted)", fontSize: "0.82rem" }}>
              {data.selection.reflection || "No previous settlement data"}
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

          <section className="panel span-12">
            <h2>Multi-Agent Research Loop</h2>
            <div className="agent-report-grid">
              <div>
                <span>Indicator agent</span>
                <p>{data.multiAgent?.indicatorReport || data.selection.multiAgentContext?.indicatorReport}</p>
              </div>
              <div>
                <span>Flow agent</span>
                <p>{data.multiAgent?.flowReport || data.selection.multiAgentContext?.flowReport}</p>
              </div>
              <div>
                <span>Memory agent</span>
                <p>{data.multiAgent?.memoryReport || data.selection.memoryContextSummary}</p>
              </div>
              <div>
                <span>Reputation agent</span>
                <p>{data.multiAgent?.reputationReport || data.selection.reputationImpact}</p>
              </div>
            </div>
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
            {chain?.registryLayer && (
              <div className="metric">
                <span>Registry path</span>
                <strong style={{ fontSize: "0.75rem" }}>{chain.registryLayer}</strong>
              </div>
            )}
            {chain?.proofURI && (
              <div className="metric">
                <span>Validation proof URI</span>
                <strong style={{ fontSize: "0.75rem" }}>{shortHash(chain.proofURI)}</strong>
              </div>
            )}
            {settlement && (
              <>
                <h2 style={{ marginTop: 16 }}>Reputation settlement</h2>
                <div className="metric">
                  <span>PnL bps</span>
                  <strong>{settlement.pnlBps.toFixed(2)}</strong>
                </div>
                <div className="metric">
                  <span>Feedback score</span>
                  <strong>{settlement.score}</strong>
                </div>
                <div className={`proof-state ${settlementChain?.recorded ? "recorded" : "demo"}`}>
                  {settlementChain?.recorded ? "Reputation written" : "Reputation demo"}
                </div>
              </>
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
              <p>Offline data mode is a fallback, but final live judging should use Mantle mainnet configuration.</p>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
