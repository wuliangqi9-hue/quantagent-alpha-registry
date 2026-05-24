// QuantAgent Alpha Registry — 前端类型定义

export type Factor = {
  id: string;
  label: string;
  score: number | null;
  missing: boolean;
  explanation: string;
};

export type BenchmarkSummary = {
  regimeSharpe: number;
  winRate: number;
  maxDrawdownPct: number;
  note: string;
};

export type BenchmarkChart = {
  prices: { timestamp: string; close: number }[];
  markers: { timestamp: string; price: number; side: string }[];
  caveats: string[];
};

export type MultiAgentContext = {
  indicatorReport?: string;
  flowReport?: string;
  memoryReport?: string;
  reputationReport?: string;
  riskCriticWarnings?: string[];
};

export type MemoryContext = {
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

export type Selection = {
  marketRegime: string;
  strategyId: string;
  strategyName: string;
  strategyDescription: string;
  signalDirection: string;
  confidence: number;
  topDrivers: string[];
  riskWarnings: string[];
  benchmarkSummary: BenchmarkSummary;
  benchmarkChart: BenchmarkChart;
  alphaFormula?: string;
  formulaRationale?: string;
  riskProfileState?: string;
  reputationImpact?: string;
  reflection?: string;
  memoryContextSummary?: string;
  multiAgentContext?: MultiAgentContext;
  explanation: string;
};

export type AgentStatus = {
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

export type ByrealStatus = {
  configured: boolean;
  mode: string;
  apiBase?: string | null;
  skills: string[];
  message: string;
};

export type ExecutionIntent = {
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

export type Analysis = {
  symbol: string;
  mode: string;
  signalHash: string;
  modelVersion: string;
  reportSchema: string;
  factorSummary: { factors: Factor[] };
  selection: Selection;
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

export type ChainResult = {
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

export type Settlement = {
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

export type DataMode = "auto" | "live" | "offline-demo";