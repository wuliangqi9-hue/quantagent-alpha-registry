import {
  Bar,
  BarChart,
  CartesianGrid,
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

const chartGrid = "#d8d8de";
const chartMuted = "#6e6e73";
const chartBlue = "#0071e3";
const chartTeal = "#007d72";
const tooltipStyle = {
  background: "rgba(255, 255, 255, 0.96)",
  border: "1px solid rgba(0, 0, 0, 0.08)",
  borderRadius: 8,
  boxShadow: "0 12px 28px rgba(0, 0, 0, 0.08)",
  color: "#1d1d1f",
} as const;

export function FactorCharts({ factors }: Props) {
  const chartData = factors
    .filter((f) => f.score != null)
    .map((f) => ({ factor: f.label, score: f.score as number }));

  return (
    <section className="panel span-5">
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
          <Bar dataKey="score" fill={chartBlue} radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </section>
  );
}
