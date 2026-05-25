import { Suspense, lazy, useMemo, useState } from "react";
import {
  AgentPassport,
  AgentTerminal,
  DecisionSummary,
  EmptyState,
  ExecutionPanel,
  FootnotePanel,
  HeaderPanel,
  JudgingEvidence,
  MantleProofPanel,
  MultiAgentPanel,
  RegimeStrategy,
  RiskBenchmark,
  SkeletonGrid,
  SkeletonPanel,
  StatusBar,
} from "./components";
import { useAnalysis } from "./hooks/useAnalysis";
import { useWallet } from "./hooks/useWallet";
import { Toaster } from "sonner";

type WorkspaceView = "overview" | "strategy" | "proof" | "agent" | "evidence";

const FactorCharts = lazy(() =>
  import("./components/FactorCharts").then((module) => ({ default: module.FactorCharts })),
);
const PriceChart = lazy(() =>
  import("./components/PriceChart").then((module) => ({ default: module.PriceChart })),
);

const VIEWS: { id: WorkspaceView; label: string; desc: string }[] = [
  { id: "overview", label: "Command", desc: "Signal, route, proof posture" },
  { id: "strategy", label: "Research", desc: "Factors, regime, benchmark" },
  { id: "proof", label: "Assurance", desc: "Mantle, zkTLS, reputation" },
  { id: "agent", label: "Cognition", desc: "Identity, memory, reasoning" },
  { id: "evidence", label: "Jury", desc: "Claims mapped to scoring" },
];

export default function App() {
  const wallet = useWallet();
  const [view, setView] = useState<WorkspaceView>("overview");
  const {
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
    analyze,
    recordSignal,
    settleSignal,
    terminalMessages,
    isAnalyzing,
    lastOpro,
  } = useAnalysis();

  const prices = data?.selection.benchmarkChart.prices ?? [];
  const latestPrice = prices.length ? prices[prices.length - 1].close : null;
  const activeView = useMemo(
    () => VIEWS.find((item) => item.id === view) ?? VIEWS[0],
    [view],
  );

  return (
    <div className="app">
      <Toaster
        position="top-right"
        closeButton
        className="app-toaster"
        toastOptions={{
          duration: 4200,
          style: {
            background: "rgba(18, 19, 22, 0.96)",
            border: "1px solid rgba(244, 241, 234, 0.14)",
            color: "#f4f1ea",
            boxShadow: "0 18px 48px rgba(0, 0, 0, 0.38)",
          },
        }}
      />
      <HeaderPanel
        symbol={symbol}
        mode={mode}
        loading={loading}
        recording={recording}
        settling={settling}
        hasData={Boolean(data)}
        onSymbolChange={setSymbol}
        onModeChange={setMode}
        onAnalyze={analyze}
        onRecord={recordSignal}
        onSettle={settleSignal}
        wallet={wallet}
        onConnectWallet={wallet.connect}
        onSwitchChain={wallet.switchToMantle}
      />

      {data && <StatusBar data={data} chain={chain} latestPrice={latestPrice} />}

      {error && <div className="error">{error}</div>}

      {!data && !loading && <EmptyState />}

      {loading && <SkeletonGrid />}

      {data && !loading && (
        <>
          <nav className="workspace-tabs" aria-label="Workspace sections">
            {VIEWS.map((item) => (
              <button
                key={item.id}
                className={view === item.id ? "active" : ""}
                aria-current={view === item.id ? "page" : undefined}
                onClick={() => setView(item.id)}
                type="button"
              >
                <span>{item.label}</span>
                <small>{item.desc}</small>
              </button>
            ))}
          </nav>

          <div className="workspace-header">
            <div>
              <span className="section-kicker">Current room</span>
              <h2>{activeView.label}</h2>
            </div>
            <p>{activeView.desc}</p>
          </div>

          <div className={`grid workspace-grid workspace-${view}`}>
            {view === "overview" && (
              <>
                <DecisionSummary
                  data={data}
                  chain={chain}
                  settlement={settlement}
                  latestPrice={latestPrice}
                />
                <ExecutionPanel data={data} />
                <RegimeStrategy selection={data.selection} />
                <MantleProofPanel
                  data={data}
                  chain={chain}
                  settlement={settlement}
                  settlementChain={settlementChain}
                  walletConnected={wallet.connected}
                  signMessage={wallet.signMessage}
                />
              </>
            )}

            {view === "strategy" && (
              <>
                <RegimeStrategy selection={data.selection} />
                <Suspense fallback={<SkeletonPanel variant="full" className="span-5 factor-panel" />}>
                  <FactorCharts factors={data.factorSummary.factors} />
                </Suspense>
                <RiskBenchmark selection={data.selection} settlement={settlement} />
                <Suspense fallback={<SkeletonPanel variant="wide" className="span-8 price-panel" />}>
                  <PriceChart chart={data.selection.benchmarkChart} />
                </Suspense>
              </>
            )}

            {view === "proof" && (
              <>
                <MantleProofPanel
                  data={data}
                  chain={chain}
                  settlement={settlement}
                  settlementChain={settlementChain}
                  walletConnected={wallet.connected}
                  signMessage={wallet.signMessage}
                />
                <ExecutionPanel data={data} />
                <AgentPassport data={data} chain={chain} settlement={settlement} />
              </>
            )}

            {view === "agent" && (
              <>
                <AgentPassport data={data} chain={chain} settlement={settlement} />
                <AgentTerminal
                  messages={terminalMessages}
                  isActive={isAnalyzing}
                />
                <MultiAgentPanel
                  multiAgent={data.multiAgent}
                  selection={data.selection}
                  isAnalyzing={isAnalyzing || loading}
                  oproAdaptation={lastOpro}
                />
              </>
            )}

            {view === "evidence" && (
              <>
                <JudgingEvidence
                  data={data}
                  chain={chain}
                  settlement={settlement}
                />
                <FootnotePanel />
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
}
