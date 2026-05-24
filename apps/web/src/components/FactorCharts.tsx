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

export function FactorCharts({ factors }: Props) {
  const chartData = factors
    .filter((f) => f.score != null)
    .map((f) => ({ factor: f.label, score: f.score as number }));

  return (
    <section className="panel span-5">
      <h2>Factor Summary</h2>
      <ResponsiveContainer width="100%" height={280}>
        <RadarChart data={chartData}>
          <PolarGrid stroke="#334155" />
          <PolarAngleAxis dataKey="factor" tick={{ fill: "#9fb0d0", fontSize: 11 }} />
          <Radar dataKey="score" stroke="#5eead4" fill="#5eead4" fillOpacity={0.35} />
          <Tooltip />
        </RadarChart>
      </ResponsiveContainer>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="factor" tick={{ fill: "#9fb0d0", fontSize: 10 }} />
          <YAxis domain={[-3, 3]} tick={{ fill: "#9fb0d0" }} />
          <Tooltip />
          <Bar dataKey="score" fill="#60a5fa" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </section>
  );
}