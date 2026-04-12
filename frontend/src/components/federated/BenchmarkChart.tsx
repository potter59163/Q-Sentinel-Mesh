"use client";

import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { BenchmarkData } from "@/types/api";

interface Props {
  data: BenchmarkData;
}

export default function BenchmarkChart({ data }: Props) {
  const chartData = data.nodes.map((n, i) => ({
    nodes: `${n} Node${n > 1 ? "s" : ""}`,
    baseline: parseFloat((data.baseline_auc[i] * 100).toFixed(2)),
    qsentinel: parseFloat((data.qsentinel_auc[i] * 100).toFixed(2)),
  }));

  return (
    <div className="rounded-[1.5rem] p-5" style={{ background: "var(--surface)", border: "1.5px solid var(--border)" }}>
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <div className="q-eyebrow">Benchmark</div>
          <div className="mt-1 text-sm font-semibold" style={{ color: "var(--text-1)" }}>
            เทียบผลตามจำนวนโหนดที่เข้าร่วม
          </div>
          <div className="mt-0.5 text-xs" style={{ color: "var(--text-3)" }}>
            การเปลี่ยนแปลงของ AUC ระหว่าง baseline และ hybrid stack
          </div>
        </div>
        <div
          className="rounded-full px-3 py-1 text-xs font-mono"
          style={{ background: "var(--accent-light)", color: "var(--accent)", fontFamily: "var(--font-mono)" }}
        >
          {(data.metadata.fed_final_auc * 100).toFixed(1)}% peak AUC
        </div>
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <ComposedChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(172, 137, 149, 0.22)" />
          <XAxis dataKey="nodes" tick={{ fontSize: 12, fill: "var(--text-3)" }} />
          <YAxis domain={[82, 97]} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 12, fill: "var(--text-3)" }} />
          <Tooltip
            formatter={(value, name) => [`${value}%`, name]}
            contentStyle={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: 14,
              fontSize: 12,
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Area type="monotone" dataKey="qsentinel" fill="var(--accent)" fillOpacity={0.08} stroke="none" />
          <Line
            type="monotone"
            dataKey="baseline"
            name="CNN Baseline"
            stroke="var(--chart-baseline)"
            strokeWidth={2}
            strokeDasharray="5 5"
            dot={{ fill: "var(--chart-baseline)", r: 5 }}
          />
          <Line
            type="monotone"
            dataKey="qsentinel"
            name="Q-Sentinel Hybrid"
            stroke="var(--accent)"
            strokeWidth={2.5}
            dot={{ fill: "var(--accent)", r: 6, strokeWidth: 2, stroke: "white" }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
