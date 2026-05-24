import type { DataMode } from "../types";

const ASSETS = ["BTC", "ETH", "SOL"];

type Props = {
  symbol: string;
  mode: DataMode;
  loading: boolean;
  recording: boolean;
  settling: boolean;
  hasData: boolean;
  onSymbolChange: (s: string) => void;
  onModeChange: (m: DataMode) => void;
  onAnalyze: () => void;
  onRecord: () => void;
  onSettle: () => void;
};

export function HeaderPanel({
  symbol,
  mode,
  loading,
  recording,
  settling,
  hasData,
  onSymbolChange,
  onModeChange,
  onAnalyze,
  onRecord,
  onSettle,
}: Props) {
  return (
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
        <select value={symbol} onChange={(e) => onSymbolChange(e.target.value)}>
          {ASSETS.map((a) => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>
        <select value={mode} onChange={(e) => onModeChange(e.target.value as DataMode)}>
          <option value="auto">Auto (live → fallback)</option>
          <option value="live">Live</option>
          <option value="offline-demo">Offline demo</option>
        </select>
        <button onClick={onAnalyze} disabled={loading}>
          {loading ? "Analyzing…" : "Analyze"}
        </button>
        <button className="secondary" onClick={onRecord} disabled={!hasData || recording}>
          {recording ? "Recording…" : "Record on Mantle"}
        </button>
        <button className="secondary" onClick={onSettle} disabled={!hasData || settling}>
          {settling ? "Settling…" : "Settle Reputation"}
        </button>
      </div>
    </header>
  );
}