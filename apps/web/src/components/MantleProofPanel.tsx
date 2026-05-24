import { useCallback, useState } from "react";
import type { Analysis, ChainResult, FinposRewards, OproAdaptation, Settlement, TeeAttestation, ZktlsProof } from "../types";

const shortHash = (value: string | null | undefined): string =>
  value ? `${value.slice(0, 10)}…${value.slice(-8)}` : "Not configured";

const proofLabel = (chain: ChainResult | null, hasContract: boolean): string => {
  if (chain?.recorded) return "Recorded on Mantle";
  if (chain?.error) return "On-chain attempt failed";
  if (chain?.mock || chain?.proofMode === "demo-proof" || !hasContract) return "Demo-proof mode";
  return "Ready to record";
};

const FinposRewardRow = ({ rewards }: { rewards?: FinposRewards }) => {
  if (!rewards) return null;
  return (
    <>
      <h2 style={{ marginTop: 16 }}>FinPos Multi‑timescale Rewards</h2>
      <div className="metric">
        <span>Immediate PnL (bps)</span>
        <strong>{rewards.immediatePnlBps.toFixed(2)}</strong>
      </div>
      <div className="metric">
        <span>Direction correct</span>
        <strong style={{ color: rewards.directionCorrect ? "var(--accent)" : "var(--danger)" }}>
          {rewards.directionCorrect ? "✓" : "✗"}
        </strong>
      </div>
      <div className="metric">
        <span>Short‑window PnL ({rewards.shortWindow.windowSize})</span>
        <strong>{rewards.shortWindow.pnlBps.toFixed(2)}</strong>
      </div>
      <div className="metric">
        <span>Short‑window Sharpe</span>
        <strong>{rewards.shortWindow.sharpe.toFixed(3)}</strong>
      </div>
      <div className="metric">
        <span>Medium‑window PnL ({rewards.mediumWindow.windowSize})</span>
        <strong>{rewards.mediumWindow.pnlBps.toFixed(2)}</strong>
      </div>
      <div className="metric">
        <span>Exposure penalty (bps)</span>
        <strong>{rewards.exposurePenaltyBps.toFixed(2)}</strong>
      </div>
      <div className="metric">
        <span>Composite score</span>
        <strong>{rewards.compositeScore.toFixed(4)}</strong>
      </div>
    </>
  );
};

const TeeAttestationRow = ({ tee }: { tee?: TeeAttestation }) => {
  if (!tee) return null;
  return (
    <>
      <h2 style={{ marginTop: 16 }}>TEE Attestation</h2>
      <div className={`proof-state ${tee.verified ? "recorded" : "demo"}`}>
        {tee.verified ? "Attestation verified" : "Attestation pending"}
      </div>
      <div className="metric">
        <span>Platform</span>
        <strong>{tee.enclavePlatform}</strong>
      </div>
      <div className="hash">{shortHash(tee.attestationHash)}</div>
      <div className="metric">
        <span>Code measurement</span>
        <strong style={{ fontSize: "0.65rem" }}>{shortHash(tee.codeMeasurement)}</strong>
      </div>
    </>
  );
};

const ZktlsProofRow = ({ proof }: { proof?: ZktlsProof }) => {
  if (!proof) return null;
  return (
    <>
      <h2 style={{ marginTop: 16 }}>zkTLS Data Provenance</h2>
      <div className={`proof-state ${proof.verified ? "recorded" : "demo"}`}>
        {proof.verified ? "Zero‑knowledge proof verified" : "ZK proof pending"}
      </div>
      <div className="metric">
        <span>Provider</span>
        <strong>{proof.provider}</strong>
      </div>
      <div className="metric">
        <span>Endpoint</span>
        <strong style={{ fontSize: "0.75rem" }}>{proof.endpoint}</strong>
      </div>
      <div className="hash">{shortHash(proof.proofHash)}</div>
    </>
  );
};

const OproAdaptationRow = ({ opro }: { opro?: OproAdaptation }) => {
  if (!opro) return null;
  return (
    <>
      <h2 style={{ marginTop: 16 }}>ATLAS Adaptive‑OPRO</h2>
      <div className="metric">
        <span>Iteration</span>
        <strong>#{opro.iteration}</strong>
      </div>
      <div className="metric">
        <span>Mutations applied</span>
        <strong>{opro.mutations.length}</strong>
      </div>
      <div className="metric">
        <span>Performance delta</span>
        <strong style={{ color: opro.performanceDelta >= 0 ? "var(--accent)" : "var(--danger)" }}>
          {opro.performanceDelta > 0 ? "+" : ""}{opro.performanceDelta.toFixed(4)}
        </strong>
      </div>
      <p className="note">{opro.rationale}</p>
    </>
  );
};

type Props = {
  data: Analysis;
  chain: ChainResult | null;
  settlement: Settlement | null;
  settlementChain: ChainResult | null;
};

export function MantleProofPanel({ data, chain, settlement, settlementChain }: Props) {
  const [copied, setCopied] = useState(false);
  const [copiedBundle, setCopiedBundle] = useState(false);

  const copyReport = useCallback(async () => {
    if (!data) return;
    await navigator.clipboard.writeText(JSON.stringify(data.decisionReport, null, 2));
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }, [data]);

  const copyProofBundle = useCallback(async () => {
    const bundle = settlement?.proofBundle || data.proofBundle;
    if (!bundle) return;
    await navigator.clipboard.writeText(JSON.stringify(bundle, null, 2));
    setCopiedBundle(true);
    window.setTimeout(() => setCopiedBundle(false), 1600);
  }, [data.proofBundle, settlement?.proofBundle]);

  return (
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
      {(settlement?.proofBundleHash || data.proofBundle?.proofBundleHash) && (
        <>
          <div className="metric">
            <span>Proof bundle hash</span>
          </div>
          <div className="hash">{settlement?.proofBundleHash || data.proofBundle?.proofBundleHash}</div>
        </>
      )}
      {data.dataProof && (
        <>
          <div className="metric">
            <span>zkTLS provider</span>
            <strong style={{ fontSize: "0.75rem" }}>{data.dataProof.provider}</strong>
          </div>
          <div className="metric">
            <span>Data proof hash</span>
            <strong style={{ fontSize: "0.75rem" }}>{shortHash(data.dataProof.proofHash)}</strong>
          </div>
        </>
      )}
      {data.contractAddress && (
        <div className="metric">
          <span>SignalRegistry</span>
          <strong style={{ fontSize: "0.75rem" }}>{shortHash(data.contractAddress)}</strong>
        </div>
      )}
      {!data.contractAddress && (
        <p className="note">
          SignalRegistry not configured. The UI remains demo-safe; set SIGNAL_REGISTRY_ADDRESS
          for final submission.
        </p>
      )}
      {data.signalRegistry && data.signalRegistry !== data.contractAddress && (
        <div className="metric">
          <span>SignalRegistry (config)</span>
          <strong style={{ fontSize: "0.75rem" }}>{shortHash(data.signalRegistry)}</strong>
        </div>
      )}
      {data.quantAgentExecutor && (
        <div className="metric">
          <span>QuantAgentExecutor</span>
          <strong style={{ fontSize: "0.75rem" }}>{shortHash(data.quantAgentExecutor)}</strong>
        </div>
      )}
      {data.erc8004 && (
        <>
          <div className="metric" style={{ marginTop: 8 }}>
            <span>ERC-8004 IdentityRegistry</span>
            <strong style={{ fontSize: "0.75rem" }}>{shortHash(data.erc8004.identityRegistry)}</strong>
          </div>
          <div className="metric">
            <span>ERC-8004 ReputationRegistry</span>
            <strong style={{ fontSize: "0.75rem" }}>{shortHash(data.erc8004.reputationRegistry)}</strong>
          </div>
        </>
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
          <div className="metric">
            <span>Rolling PnL</span>
            <strong>{(settlement.rollingPnlBps ?? settlement.pnlBps).toFixed(2)}</strong>
          </div>
          <div className="metric">
            <span>Loss streak</span>
            <strong>{settlement.consecutiveLosses ?? 0}</strong>
          </div>
          {settlement.compositeScore != null && (
            <div className="metric">
              <span>FinPos composite</span>
              <strong>{settlement.compositeScore.toFixed(4)}</strong>
            </div>
          )}
          <FinposRewardRow rewards={settlement.finposRewards} />
          <TeeAttestationRow tee={settlement.teeAttestation} />
          <ZktlsProofRow proof={settlement.zktlsProof} />
          <OproAdaptationRow opro={settlement.oproAdaptation} />
          <div className={`proof-state ${settlementChain?.recorded ? "recorded" : "demo"}`}>
            {settlementChain?.recorded ? "Reputation written" : "Reputation demo"}
          </div>
        </>
      )}
      {chain?.error && <p className="error">{chain.error}</p>}
      <button className="secondary full-width" onClick={copyReport}>
        {copied ? "Decision report copied" : "Copy decision report JSON"}
      </button>
      {(settlement?.proofBundle || data.proofBundle) && (
        <button className="secondary full-width" onClick={copyProofBundle}>
          {copiedBundle ? "Proof bundle copied" : "Copy proof bundle JSON"}
        </button>
      )}
      <p className="note">
        The signal hash is computed from this canonical decision report.
      </p>
    </section>
  );
}
