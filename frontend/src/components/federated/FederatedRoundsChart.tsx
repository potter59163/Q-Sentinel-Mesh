"use client";

import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { FedRound } from "@/types/api";

interface Props {
  rounds: FedRound[];
}

export default function FederatedRoundsChart({ rounds }: Props) {
  const chartData = rounds.map((r) => ({
    round: `R${r.round}`,
    auc: parseFloat((r.global_auc * 100).toFixed(2)),
    loss: parseFloat(r.global_loss.toFixed(4)),
  }));

  return (
    <div className="rounded-[1.5rem] p-5" style={{ background: "var(--surface)", border: "1.5px solid var(--border)" }}>
      <div className="mb-4">
        <div className="q-eyebrow">Training Trace</div>
        <div className="mt-1 text-sm font-semibold" style={{ color: "var(--text-1)" }}>
          Global AUC and loss throughout aggregation rounds
        </div>
        <div className="mt-1 text-xs" style={{ color: "var(--text-3)" }}>
          Use this view to confirm that the global model improves as hospitals contribute updates.
        </div>
      </div>

      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(172, 137, 149, 0.22)" />
          <XAxis dataKey="round" tick={{ fontSize: 12, fill: "var(--text-3)" }} />
          <YAxis yAxisId="auc" orientation="left" domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11, fill: "var(--text-3)" }} />
          <YAxis yAxisId="loss" orientation="right" tick={{ fontSize: 11, fill: "var(--text-3)" }} />
          <Tooltip
            contentStyle={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: 14,
              fontSize: 12,
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar yAxisId="loss" dataKey="loss" name="Loss" fill="var(--accent-soft)" radius={[8, 8, 0, 0]} opacity={0.72} />
          <Line
            yAxisId="auc"
            type="monotone"
            dataKey="auc"
            name="Global AUC"
            stroke="var(--accent)"
            strokeWidth={2.5}
            dot={{ fill: "var(--accent)", r: 5 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
