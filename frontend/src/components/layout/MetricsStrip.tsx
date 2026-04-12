"use client";

import { useDashboard } from "@/context/DashboardContext";

function MetricCard({
  label,
  value,
  note,
  valueColor,
}: {
  label: string;
  value: string;
  note: string;
  valueColor?: string;
}) {
  return (
    <article className="q-soft-panel px-4 py-4 sm:px-5">
      <div className="q-eyebrow mb-1">{label}</div>
      <div
        className="text-[1.65rem] font-bold leading-none"
        style={{
          color: valueColor ?? "var(--text-1)",
          fontFamily: "var(--font-mono-stack)",
        }}
      >
        {value}
      </div>
      <p className="mt-2 flex items-center gap-1 text-xs leading-5" style={{ color: "var(--text-2)" }}>
        <span style={{ color: valueColor ?? "var(--text-3)" }}>↑</span>
        {note}
      </p>
    </article>
  );
}

export default function MetricsStrip() {
  const { scansAnalyzed } = useDashboard();

  return (
    <section className="q-metric-grid">
      <MetricCard
        label="โหนดที่ใช้งาน"
        value="3"
        note="Federated network ออนไลน์"
        valueColor="var(--text-1)"
      />
      <MetricCard
        label="Global AUC"
        value="87.6%"
        note="ผลล่าสุดของโมเดลรวม"
        valueColor="var(--accent)"
      />
      <MetricCard
        label="เคสที่วิเคราะห์"
        value={String(scansAnalyzed)}
        note="ในรอบการใช้งานนี้"
      />
    </section>
  );
}
