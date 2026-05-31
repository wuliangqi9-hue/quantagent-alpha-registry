import type { Analysis, ChainResult } from "../types";
import { chainProofLabel, chainProofTone, dataModeLabel, isOfflineDataMode } from "../utils/chainStatus";

type Props = {
  data: Analysis;
  chain: ChainResult | null;
  latestPrice: number | null;
};

export function StatusBar({ data, chain, latestPrice }: Props) {
  const dataTone = isOfflineDataMode(data.mode) ? "offline" : "live";
  const chainTone = chainProofTone(chain, Boolean(data.contractAddress));

  return (
    <div className="status-row">
      <span className={`badge ${dataTone}`}>
        {dataModeLabel(data.mode)}
      </span>
      <span className={`badge ${chainTone}`}>
        {chainProofLabel(chain, Boolean(data.contractAddress))}
      </span>
      <span className="badge">{data.symbol}</span>
      {latestPrice != null && (
        <span className="badge">{latestPrice.toLocaleString()}</span>
      )}
    </div>
  );
}
