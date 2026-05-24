import {
  AgentPassport,
  EmptyState,
  ExecutionPanel,
  FactorCharts,
  FootnotePanel,
  HeaderPanel,
  MantleProofPanel,
  MultiAgentPanel,
  PriceChart,
  RegimeStrategy,
  RiskBenchmark,
  StatusBar,
} from "./components";
import { useAnalysis } from "./hooks/useAnalysis";

export default function App() {
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
  } = useAnalysis();

  const prices = data?.selection.benchmarkChart.prices ?? [];
  const latestPrice = prices.length ? prices[prices.length - 1].close : null;

  return (
    <div className="app">
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
      />

      {data && <StatusBar data={data} chain={chain} latestPrice={latestPrice} />}

      {error && <div className="error">{error}</div>}

      {!data && !loading && <EmptyState />}

      {data && (
        <div className="grid">
          <AgentPassport data={data} chain={chain} settlement={settlement} />

          <FactorCharts factors={data.factorSummary.factors} />

          <RegimeStrategy selection={data.selection} />

          <ExecutionPanel data={data} />

          <RiskBenchmark selection={data.selection} settlement={settlement} />

          <PriceChart chart={data.selection.benchmarkChart} />

          <MultiAgentPanel
            multiAgent={data.multiAgent}
            selection={data.selection}
          />

          <MantleProofPanel
            data={data}
            chain={chain}
            settlement={settlement}
            settlementChain={settlementChain}
          />

          <FootnotePanel />
        </div>
      )}
    </div>
  );
}
