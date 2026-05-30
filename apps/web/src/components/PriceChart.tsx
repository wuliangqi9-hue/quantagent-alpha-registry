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

const chartGrid = "rgba(244, 241, 234, 0.14)";
const chartMuted = "#aaa59b";
const chartBlue = "#c7d7e8";
const tooltipStyle = {
  background: "rgba(18, 19, 22, 0.96)",
  border: "1px solid rgba(244, 241, 234, 0.14)",
  borderRadius: 8,
  boxShadow: "0 16px 36px rgba(0, 0, 0, 0.36)",
  color: "#f4f1ea",
} as const;

export function PriceChart({ chart }: Props) {
  return (
    <section className="panel span-8 price-panel">
      <span className="section-kicker">Market tape</span>
      <h2>Benchmark Curve</h2>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chart.prices} margin={{ top: 10, right: 12, bottom: 0, left: 6 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={chartGrid} />
          <XAxis dataKey="timestamp" hide />
          <YAxis width={54} tick={{ fill: chartMuted, fontSize: 11 }} domain={["auto", "auto"]} />
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
