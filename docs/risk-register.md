# Risk Register

This document lists the main risks that could derail the hackathon submission
and the planned mitigation for each.

## R1: Scope Explosion

Risk:

Trying to build live trading, ERC-8004, zk proofs, wallet automation, streaming
data, and a polished dashboard at the same time.

Mitigation:

Freeze the MVP around factor engine, strategy selector, dashboard, and signal
recording contract. Treat everything else as optional.

## R2: External API Failure

Risk:

Live market or chain data APIs fail, rate-limit, or respond slowly during the
demo.

Mitigation:

Keep curated snapshots in `data/sample/`. Add an explicit offline-demo mode.

## R3: Weak On-chain Story

Risk:

The project looks like a normal off-chain trading dashboard with a cosmetic
blockchain transaction.

Mitigation:

Make the signal hash and explorer link central in the UI. Explain that the
on-chain record creates an auditable decision trail.

## R4: Overclaiming Alpha

Risk:

Judges distrust the project because it appears to promise profit from small
backtests.

Mitigation:

Frame results as workflow evidence, not profit proof. Highlight caveats around
sample size, slippage, and changing market regimes.

## R5: Heavy Backend Deployment

Risk:

Complex services make deployment fragile.

Mitigation:

Use one API service first. Add queues, workers, or analytical storage only after
the end-to-end path is stable.

## R6: Frontend Underwhelms

Risk:

The technical work is real but judges cannot understand it quickly.

Mitigation:

Build the dashboard around visual proof: factor chart, benchmark chart, selected
strategy, risk panel, and explorer link.

## R7: Contract Complexity

Risk:

Trying to custody funds or execute trades on-chain introduces security and
testing burden.

Mitigation:

The MVP contract records decisions only. No custody, no automated vault, no
trade execution until the proof path works.

