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

const chartGrid = "rgba(132, 247, 255, 0.16)";
const chartMuted = "#a2adbd";
const chartBlue = "#22d3ee";
const chartTeal = "#2dd4bf";
const chartViolet = "#a78bfa";
const tooltipStyle = {
  background: "rgba(8, 12, 22, 0.96)",
  border: "1px solid rgba(132, 247, 255, 0.18)",
  borderRadius: 8,
  boxShadow: "0 16px 36px rgba(0, 0, 0, 0.36)",
  color: "#f5f7fb",
} as const;

export function FactorCharts({ factors }: Props) {
  const chartData = factors
    .filter((f) => f.score != null)
    .map((f) => ({
      factor: f.label,
      score: f.score as number,
      mantleNative: /mantle|gas|dex|liquidity|mnt|sequencer/i.test(`${f.id} ${f.label}`),
    }));

  return (
    <section className="panel span-5">
      <span className="section-kicker">Mantle-native factors</span>
      <h2>Factor Summary</h2>
      <ResponsiveContainer width="100%" height={280}>
        <RadarChart data={chartData}>
          <PolarGrid stroke={chartGrid} />
          <PolarAngleAxis dataKey="factor" tick={{ fill: chartMuted, fontSize: 11 }} />
          <Radar dataKey="score" stroke={chartTeal} fill={chartTeal} fillOpacity={0.18} />
          <Tooltip contentStyle={tooltipStyle} cursor={{ stroke: chartGrid }} />
        </RadarChart>
      </ResponsiveContainer>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke={chartGrid} />
          <XAxis dataKey="factor" tick={{ fill: chartMuted, fontSize: 10 }} />
          <YAxis domain={[-3, 3]} tick={{ fill: chartMuted }} />
          <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "rgba(0, 113, 227, 0.06)" }} />
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
