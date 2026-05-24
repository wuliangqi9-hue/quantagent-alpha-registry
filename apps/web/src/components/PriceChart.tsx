import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { BenchmarkChart } from "../types";

type Props = {
  chart: BenchmarkChart;
};

const chartGrid = "#d8d8de";
const chartMuted = "#6e6e73";
const chartBlue = "#0071e3";
const tooltipStyle = {
  background: "rgba(255, 255, 255, 0.96)",
  border: "1px solid rgba(0, 0, 0, 0.08)",
  borderRadius: 8,
  boxShadow: "0 12px 28px rgba(0, 0, 0, 0.08)",
  color: "#1d1d1f",
} as const;

export function PriceChart({ chart }: Props) {
  return (
    <section className="panel span-8">
      <h2>Benchmark Chart</h2>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chart.prices}>
          <CartesianGrid strokeDasharray="3 3" stroke={chartGrid} />
          <XAxis dataKey="timestamp" hide />
          <YAxis tick={{ fill: chartMuted }} domain={["auto", "auto"]} />
          <Tooltip contentStyle={tooltipStyle} cursor={{ stroke: chartGrid }} />
          <Line type="monotone" dataKey="close" stroke={chartBlue} dot={false} strokeWidth={2.25} />
        </LineChart>
      </ResponsiveContainer>
      <ul className="drivers">
        {chart.caveats.map((c) => (
          <li key={c}>{c}</li>
        ))}
      </ul>
    </section>
  );
}
