import type { MultiAgentContext, Selection } from "../types";

type Props = {
  multiAgent: MultiAgentContext | undefined;
  selection: Selection;
};

export function MultiAgentPanel({ multiAgent, selection }: Props) {
  const indicatorReport = multiAgent?.indicatorReport ?? selection.multiAgentContext?.indicatorReport;
  const flowReport = multiAgent?.flowReport ?? selection.multiAgentContext?.flowReport;
  const memoryReport = multiAgent?.memoryReport ?? selection.memoryContextSummary;
  const reputationReport =
    multiAgent?.reputationReport ?? selection.multiAgentContext?.reputationReport ?? selection.reputationImpact;

  return (
    <section className="panel span-12">
      <h2>Multi-Agent Research Loop</h2>
      <div className="agent-report-grid">
        <div>
          <span>Indicator agent</span>
          <p>{indicatorReport}</p>
        </div>
        <div>
          <span>Flow agent</span>
          <p>{flowReport}</p>
        </div>
        <div>
          <span>Memory agent</span>
          <p>{memoryReport}</p>
        </div>
        <div>
          <span>Reputation agent</span>
          <p>{reputationReport}</p>
        </div>
      </div>
    </section>
  );
}