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

export function PriceChart({ chart }: Props) {
  return (
    <section className="panel span-8">
      <h2>Benchmark chart (workflow evidence)</h2>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chart.prices}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="timestamp" hide />
          <YAxis tick={{ fill: "#9fb0d0" }} domain={["auto", "auto"]} />
          <Tooltip />
          <Line type="monotone" dataKey="close" stroke="#60a5fa" dot={false} strokeWidth={2} />
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