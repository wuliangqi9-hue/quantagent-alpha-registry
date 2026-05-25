import type { DataMode } from "../types";
import type { WalletState } from "../hooks/useWallet";

const ASSETS = ["BTC", "ETH", "SOL"];

const shortAddr = (addr: string | null): string =>
  addr ? `${addr.slice(0, 6)}…${addr.slice(-4)}` : "Not connected";

type Props = {
  symbol: string;
  mode: DataMode;
  loading: boolean;
  recording: boolean;
  settling: boolean;
  hasData: boolean;
  wallet: WalletState;
  onSymbolChange: (s: string) => void;
  onModeChange: (m: DataMode) => void;
  onAnalyze: () => void;
  onRecord: () => void;
  onSettle: () => void;
  onConnectWallet: () => void;
  onSwitchChain: () => void;
};

export function HeaderPanel({
  symbol,
  mode,
  loading,
  recording,
  settling,
  hasData,
  wallet,
  onSymbolChange,
  onModeChange,
  onAnalyze,
  onRecord,
  onSettle,
  onConnectWallet,
  onSwitchChain,
}: Props) {
  const chainBadge = wallet.connected
    ? wallet.isMantle
      ? "mantle-badge"
      : "mantle-badge mantle-badge--warn"
    : "";

  return (
    <header className="header">
      <div className="title">
        <div className="eyebrow">Mantle Turing Test · Proof-aware trading</div>
        <h1>QuantAgent Alpha Registry</h1>
        <p>
          Factor research, route selection, proof bundles, and ERC-8004 reputation feedback
          presented as one calm, auditable decision workspace.
        </p>
      </div>
      <div className="controls">
        {/* Wallet section */}
        <div className="wallet-row">
          {!wallet.connected ? (
            <button className="wallet-btn" onClick={onConnectWallet}>
              Connect Wallet
            </button>
          ) : (
            <div className="wallet-info">
              <div className={`chain-indicator ${chainBadge}`}>
                {wallet.isMantle ? "Mantle Mainnet" : "Wrong Network"}
              </div>
              <div className="wallet-address">{shortAddr(wallet.address)}</div>
              <div className="wallet-balance">
                {wallet.balance} {wallet.isMantle ? "MNT" : "ETH"}
              </div>
              {!wallet.isMantle && (
                <button className="secondary switch-btn" onClick={onSwitchChain}>
                  Switch to Mantle
                </button>
              )}
            </div>
          )}
        </div>

        <div className="controls-row">
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
          <button className="secondary" onClick={onRecord} disabled={!hasData || recording || !wallet.connected}>
            {recording ? "Recording…" : "Record on Mantle"}
          </button>
          <button className="secondary" onClick={onSettle} disabled={!hasData || settling || !wallet.connected}>
            {settling ? "Settling…" : "Settle Reputation"}
          </button>
        </div>
      </div>
    </header>
  );
}
