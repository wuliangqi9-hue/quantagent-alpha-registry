import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
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
      <h2 className="panel-subtitle">FinPos Multi-timescale Rewards</h2>
      <div className="metric">
        <span>Immediate PnL (bps)</span>
        <strong>{rewards.immediatePnlBps.toFixed(2)}</strong>
      </div>
      <div className="metric">
        <span>Direction correct</span>
        <strong className={rewards.directionCorrect ? "metric-positive" : "metric-negative"}>
          {rewards.directionCorrect ? "yes" : "no"}
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
      <h2 className="panel-subtitle">TEE Attestation</h2>
      <div className={`proof-state ${tee.verified ? "recorded" : "demo"}`}>
        {tee.verified ? (
          <motion.span
            animate={{ opacity: [1, 0.5, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            Attestation verified
          </motion.span>
        ) : (
          "Attestation pending"
        )}
      </div>
      <div className="metric">
        <span>Platform</span>
        <strong>{tee.enclavePlatform}</strong>
      </div>
      <div className="hash">{shortHash(tee.attestationHash)}</div>
      <div className="metric">
        <span>Code measurement</span>
        <strong className="metric-small">{shortHash(tee.codeMeasurement)}</strong>
      </div>
    </>
  );
};

const ZktlsProofRow = ({ proof }: { proof?: ZktlsProof }) => {
  if (!proof) return null;
  return (
    <>
      <h2 className="panel-subtitle">zkTLS Data Provenance</h2>
      <div className={`proof-state ${proof.verified ? "recorded" : "demo"}`}>
        {proof.verified ? (
          <motion.span
            animate={{ opacity: [1, 0.5, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            Zero-knowledge proof verified
          </motion.span>
        ) : (
          "ZK proof pending"
        )}
      </div>
      <div className="metric">
        <span>Provider</span>
        <strong>{proof.provider}</strong>
      </div>
      <div className="metric">
        <span>Endpoint</span>
        <strong className="metric-small">{proof.endpoint}</strong>
      </div>
      <div className="hash">{shortHash(proof.proofHash)}</div>
    </>
  );
};

const OproAdaptationRow = ({ opro }: { opro?: OproAdaptation }) => {
  if (!opro) return null;
  return (
    <>
      <h2 className="panel-subtitle">ATLAS Adaptive-OPRO</h2>
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
        <strong className={opro.performanceDelta >= 0 ? "metric-positive" : "metric-negative"}>
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
  walletConnected: boolean;
  signMessage: (msg: string) => Promise<string | null>;
};

export function MantleProofPanel({
  data,
  chain,
  settlement,
  settlementChain,
  walletConnected,
  signMessage,
}: Props) {
  const [copied, setCopied] = useState(false);
  const [copiedBundle, setCopiedBundle] = useState(false);
  const [signing, setSigning] = useState(false);
  const [signature, setSignature] = useState<string | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  // Pulse glow when any proof becomes verified
  const showPulse = Boolean(
    chain?.recorded ||
    settlementChain?.recorded ||
    data.dataProof?.verified ||
    settlement?.teeAttestation?.verified
  );

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

  const handleSign = useCallback(async () => {
    if (!walletConnected || !signMessage) return;
    setSigning(true);
    const msg = `QuantAgent Attestation\nSignal: ${data.signalHash}\nModel: ${data.modelVersion}\nSchema: ${data.reportSchema}`;
    const sig = await signMessage(msg);
    setSignature(sig);
    setSigning(false);
  }, [walletConnected, signMessage, data.signalHash, data.modelVersion, data.reportSchema]);

  const explorerUrl = chain?.txHash
    ? `${data.explorerBase || "https://explorer.mantle.xyz"}/tx/${chain.txHash}`
    : settlementChain?.txHash
      ? `${data.explorerBase || "https://explorer.mantle.xyz"}/tx/${settlementChain.txHash}`
      : null;

  return (
    <section className="panel span-4 proof-panel" ref={panelRef}>
      <span className="section-kicker">Audit trail</span>
      <h2>Mantle proof</h2>

      {/* Pulse glow overlay */}
      <AnimatePresence>
        {showPulse && (
          <motion.div
            className="proof-glow"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: [0.15, 0.05, 0.15], scale: [1, 1.02, 1] }}
            transition={{ duration: 2.5, repeat: Infinity }}
          />
        )}
      </AnimatePresence>

      <motion.div
        className={`proof-state ${chain?.recorded ? "recorded" : "demo"}`}
        animate={chain?.recorded ? { scale: [1, 1.02, 1] } : {}}
        transition={{ duration: 3, repeat: Infinity }}
      >
        {proofLabel(chain, Boolean(data.contractAddress))}
      </motion.div>

      <div className="proof-timeline">
        <div className={`proof-step ${data.signalHash ? "recorded" : "demo"}`}>
          <span>Signal</span>
          <strong>{shortHash(data.signalHash)}</strong>
        </div>
        <div className={`proof-step ${data.dataProof?.verified ? "recorded" : "demo"}`}>
          <span>zkTLS</span>
          <strong>{data.dataProof?.provider || "deterministic"}</strong>
        </div>
        <div className={`proof-step ${settlement?.teeAttestation?.verified ? "recorded" : "demo"}`}>
          <span>TEE</span>
          <strong>{settlement?.teeAttestation?.enclavePlatform || "pending"}</strong>
        </div>
        <div className={`proof-step ${settlementChain?.recorded ? "recorded" : "demo"}`}>
          <span>Reputation</span>
          <strong>{settlementChain?.recorded ? "written" : "simulated"}</strong>
        </div>
      </div>

      <div className="metric">
        <span>Signal hash</span>
      </div>
      <div className="hash">{data.signalHash}</div>

      <div className="metric metric-spaced">
        <span>Model version</span>
        <strong className="metric-small">{data.modelVersion || "unknown"}</strong>
      </div>
      <div className="metric">
        <span>Report schema</span>
        <strong className="metric-small">{data.reportSchema || "legacy-report"}</strong>
      </div>
      <div className="metric">
        <span>API proof mode</span>
        <strong className="metric-small">{data.proofMode || "demo-proof"}</strong>
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
            <strong className="metric-small">{data.dataProof.provider}</strong>
          </div>
          <div className="metric">
            <span>Data proof hash</span>
            <strong className="metric-small">{shortHash(data.dataProof.proofHash)}</strong>
          </div>
        </>
      )}
      {data.contractAddress && (
        <div className="metric">
          <span>SignalRegistry</span>
          <strong className="metric-small">{shortHash(data.contractAddress)}</strong>
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
          <strong className="metric-small">{shortHash(data.signalRegistry)}</strong>
        </div>
      )}
      {data.quantAgentExecutor && (
        <div className="metric">
          <span>QuantAgentExecutor</span>
          <strong className="metric-small">{shortHash(data.quantAgentExecutor)}</strong>
        </div>
      )}
      {data.erc8004 && (
        <>
          <div className="metric metric-spaced">
            <span>ERC-8004 IdentityRegistry</span>
            <strong className="metric-small">{shortHash(data.erc8004.identityRegistry)}</strong>
          </div>
          <div className="metric">
            <span>ERC-8004 ReputationRegistry</span>
            <strong className="metric-small">{shortHash(data.erc8004.reputationRegistry)}</strong>
          </div>
        </>
      )}

      {/* Explorer links */}
      {explorerUrl && (
        <p className="explorer-link">
          <a href={explorerUrl} target="_blank" rel="noreferrer">
            View on Mantle Explorer
          </a>
        </p>
      )}
      {chain?.txHash && !explorerUrl && (
        <p className="tx-note">
          TX: {shortHash(chain.txHash)}
        </p>
      )}

      {chain?.message && (
        <p className="note">{chain.message}</p>
      )}
      {chain?.registryLayer && (
        <div className="metric">
          <span>Registry path</span>
          <strong className="metric-small">{chain.registryLayer}</strong>
        </div>
      )}
      {chain?.proofURI && (
        <div className="metric">
          <span>Validation proof URI</span>
          <strong className="metric-small">{shortHash(chain.proofURI)}</strong>
        </div>
      )}

      {settlement && (
        <>
          <h2 className="panel-subtitle">Reputation settlement</h2>
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

      {/* Signature section */}
      <div className="proof-actions">
        <button
          className="secondary full-width"
          onClick={handleSign}
          disabled={!walletConnected || signing}
        >
          {signing ? "Signing…" : signature ? "Re-sign attestation" : "Sign attestation"}
        </button>
        {signature && (
          <div className="hash signature-hash">
            Sig: {shortHash(signature)}
          </div>
        )}
      </div>

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
