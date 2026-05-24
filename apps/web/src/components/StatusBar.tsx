import type { Analysis, ChainResult } from "../types";

const proofLabel = (chain: ChainResult | null, hasContract: boolean) => {
  if (chain?.recorded) return "Recorded on Mantle";
  if (chain?.error) return "On-chain attempt failed";
  if (chain?.mock || chain?.proofMode === "demo-proof" || !hasContract) return "Demo-proof mode";
  return "Ready to record";
};

type Props = {
  data: Analysis;
  chain: ChainResult | null;
  latestPrice: number | null;
};

export function StatusBar({ data, chain, latestPrice }: Props) {
  return (
    <div className="status-row">
      <span className={`badge ${data.mode === "live" ? "live" : "offline"}`}>
        Data mode: {data.mode}
      </span>
      <span className={`badge ${chain?.recorded ? "live" : "offline"}`}>
        Proof: {proofLabel(chain, Boolean(data.contractAddress))}
      </span>
      <span className="badge">Asset: {data.symbol}</span>
      {latestPrice != null && (
        <span className="badge">Latest close: {latestPrice.toLocaleString()}</span>
      )}
    </div>
  );
}