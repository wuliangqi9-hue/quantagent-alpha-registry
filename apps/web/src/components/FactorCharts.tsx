import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Factor } from "../types";

type Props = {
  factors: Factor[];
};

const chartGrid = "rgba(244, 241, 234, 0.14)";
const chartMuted = "#aaa59b";
const chartBlue = "#b9cde6";
const chartTeal = "#9dd8cd";
const tooltipStyle = {
  background: "rgba(18, 19, 22, 0.96)",
  border: "1px solid rgba(244, 241, 234, 0.14)",
  borderRadius: 8,
  boxShadow: "0 16px 36px rgba(0, 0, 0, 0.36)",
  color: "#f4f1ea",
} as const;

const shortFactorLabel = (label: string): string =>
  label
    .replace("Open Interest", "OI")
    .replace("Mantle Liquidity", "M. Liquidity")
    .replace("Mantle ", "M. ");

export function FactorCharts({ factors }: Props) {
  const chartData = factors
    .filter((f) => f.score != null)
    .map((f) => ({
      factor: shortFactorLabel(f.label),
      fullLabel: f.label,
      score: f.score as number,
      mantleNative: /mantle|gas|dex|liquidity|mnt|sequencer/i.test(`${f.id} ${f.label}`),
    }));

  return (
    <section className="panel span-5 factor-panel">
      <span className="section-kicker">Mantle-native factors</span>
      <h2>Factor Summary</h2>
      <ResponsiveContainer width="100%" height={280} className="radar-chart-frame">
        <RadarChart
          data={chartData}
          cx="50%"
          cy="52%"
          outerRadius="68%"
          margin={{ top: 18, right: 18, bottom: 18, left: 18 }}
        >
          <PolarGrid stroke={chartGrid} />
          <PolarAngleAxis dataKey="factor" tick={{ fill: chartMuted, fontSize: 11 }} />
          <Radar dataKey="score" stroke={chartTeal} fill={chartTeal} fillOpacity={0.18} />
          <Tooltip contentStyle={tooltipStyle} cursor={{ stroke: chartGrid }} />
        </RadarChart>
      </ResponsiveContainer>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={chartData} margin={{ top: 6, right: 10, bottom: 0, left: -10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={chartGrid} />
          <XAxis dataKey="factor" tick={{ fill: chartMuted, fontSize: 10 }} />
          <YAxis domain={[-3, 3]} tick={{ fill: chartMuted }} />
          <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "rgba(199, 215, 232, 0.06)" }} />
          <Bar dataKey="score" radius={[6, 6, 0, 0]}>
            {chartData.map((entry) => (
              <Cell key={entry.factor} fill={entry.mantleNative ? chartTeal : chartBlue} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </section>
  );
}
