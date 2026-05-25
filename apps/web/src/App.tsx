import {
  AgentPassport,
  AgentTerminal,
  DecisionSummary,
  EmptyState,
  ExecutionPanel,
  FactorCharts,
  FootnotePanel,
  HeaderPanel,
  JudgingEvidence,
  MantleProofPanel,
  MultiAgentPanel,
  PriceChart,
  RegimeStrategy,
  RiskBenchmark,
  SkeletonGrid,
  StatusBar,
} from "./components";
import { useAnalysis } from "./hooks/useAnalysis";
import { useWallet } from "./hooks/useWallet";
import { Toaster } from "sonner";

export default function App() {
  const wallet = useWallet();
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

  return (
    <div className="app">
      <Toaster
        position="top-right"
        richColors
        closeButton
        toastOptions={{
          duration: 4200,
          style: {
            background: "rgba(9, 13, 24, 0.96)",
            border: "1px solid rgba(132, 247, 255, 0.18)",
            color: "#f5f7fb",
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
        <div className="grid">
          <DecisionSummary
            data={data}
            chain={chain}
            settlement={settlement}
            latestPrice={latestPrice}
          />

          <JudgingEvidence
            data={data}
            chain={chain}
            settlement={settlement}
          />

          <RegimeStrategy selection={data.selection} />

          <ExecutionPanel data={data} />

          <MantleProofPanel
            data={data}
            chain={chain}
            settlement={settlement}
            settlementChain={settlementChain}
            walletConnected={wallet.connected}
            signMessage={wallet.signMessage}
          />

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

          <FactorCharts factors={data.factorSummary.factors} />

          <RiskBenchmark selection={data.selection} settlement={settlement} />

          <PriceChart chart={data.selection.benchmarkChart} />

          <FootnotePanel />
        </div>
      )}
    </div>
  );
}
