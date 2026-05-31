import type { Analysis, ChainResult } from "../types";

export type ChainTone = "live" | "demo" | "failed" | "write-locked" | "pending";

export function chainProofTone(chain: ChainResult | null, hasContract: boolean): ChainTone {
  if (chain?.recorded) return "live";
  if (chain?.error || chain?.proofMode === "onchain-attempt-failed") return "failed";
  if (chain?.proofMode === "write-locked" || chain?.proofMode === "onchain-write-unavailable") {
    return "write-locked";
  }
  if (chain?.mock || chain?.proofMode === "demo-proof" || !hasContract) return "demo";
  return "pending";
}

export function chainProofLabel(chain: ChainResult | null, hasContract: boolean): string {
  const tone = chainProofTone(chain, hasContract);
  if (tone === "live") return "Recorded on Mantle";
  if (tone === "failed") return "On-chain attempt failed";
  if (tone === "demo") return "Demo-proof mode";
  if (tone === "write-locked") {
    return "On-chain writes locked";
  }
  return "Ready to record";
}

export function chainReputationTone(chain: ChainResult | null): ChainTone {
  if (chain?.recorded) return "live";
  if (chain?.error || chain?.proofMode === "onchain-attempt-failed") return "failed";
  if (chain?.proofMode === "write-locked" || chain?.proofMode === "onchain-write-unavailable") {
    return "write-locked";
  }
  if (chain?.mock || chain?.proofMode === "demo-proof") return "demo";
  return "pending";
}

export function chainReputationLabel(chain: ChainResult | null): string {
  const tone = chainReputationTone(chain);
  if (tone === "live") return "written";
  if (tone === "failed") return "failed";
  if (tone === "demo") return "demo";
  if (tone === "write-locked") {
    return "write-locked";
  }
  return "pending";
}

export function dataModeLabel(mode: Analysis["mode"]): string {
  if (mode === "offline-fallback") return "offline fallback";
  return mode;
}

export function isOfflineDataMode(mode: Analysis["mode"]): boolean {
  return mode === "offline-demo" || mode === "offline-fallback";
}
