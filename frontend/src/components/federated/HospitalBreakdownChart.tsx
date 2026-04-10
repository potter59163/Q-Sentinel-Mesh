"use client";

import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { FedRound } from "@/types/api";

interface Props {
  rounds: FedRound[];
}

const HOSPITALS = [
  { key: "Hospital A (Bangkok)", color: "var(--chart-hospital-a)", short: "Hospital A" },
  { key: "Hospital B (Chiang Mai)", color: "var(--chart-hospital-b)", short: "Hospital B" },
  { key: "Hospital C (Khon Kaen)", color: "var(--chart-hospital-c)", short: "Hospital C" },
];

export default function HospitalBreakdownChart({ rounds }: Props) {
  const data = rounds.map((r) => {
    const row: Record<string, number | string> = { round: `R${r.round}` };
    for (const hospital of HOSPITALS) {
      const hdata = r.hospitals[hospital.key];
      row[hospital.short] = hdata ? +(hdata.local_auc * 100).toFixed(1) : 0;
    }
    return row;
  });

  return (
    <div className="rounded-[1.5rem] border p-5" style={{ height: 288, background: "var(--surface)", borderColor: "var(--border)" }}>
      <div className="mb-4">
        <div className="q-eyebrow">Per-Hospital Performance</div>
        <div className="mt-1 text-sm font-semibold" style={{ color: "var(--text-1)" }}>
          Local AUC progression across participating sites
        </div>
      </div>

      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(172, 137, 149, 0.22)" />
          <XAxis dataKey="round" tick={{ fontSize: 11, fill: "var(--text-3)" }} />
          <YAxis domain={[75, 100]} tick={{ fontSize: 11, fill: "var(--text-3)" }} tickFormatter={(v) => `${v}%`} />
          <Tooltip
            formatter={(value) => `${Number(value).toFixed(1)}%`}
            contentStyle={{ fontSize: 12, borderColor: "var(--border)", background: "var(--surface)", borderRadius: 14 }}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {HOSPITALS.map((hospital) => (
            <Line
              key={hospital.key}
              type="monotone"
              dataKey={hospital.short}
              stroke={hospital.color}
              strokeWidth={2.5}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
