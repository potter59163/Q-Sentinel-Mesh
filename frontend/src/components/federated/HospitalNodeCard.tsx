"use client";

import type { FedRound } from "@/types/api";

const HOSPITAL_COLORS: Record<string, string> = {
  "Hospital A (Bangkok)": "var(--chart-hospital-a)",
  "Hospital B (Chiang Mai)": "var(--chart-hospital-b)",
  "Hospital C (Khon Kaen)": "var(--chart-hospital-c)",
};

const HOSPITAL_SHORT: Record<string, string> = {
  "Hospital A (Bangkok)": "A",
  "Hospital B (Chiang Mai)": "B",
  "Hospital C (Khon Kaen)": "C",
};

interface Props {
  name: string;
  rounds: FedRound[];
}

export default function HospitalNodeCard({ name, rounds }: Props) {
  const latest = rounds[rounds.length - 1];
  const hospitalData = latest?.hospitals[name];
  const color = HOSPITAL_COLORS[name] ?? "var(--accent)";
  const short = HOSPITAL_SHORT[name] ?? name.slice(0, 1);

  const auc = hospitalData ? (hospitalData.local_auc * 100).toFixed(1) : "—";
  const examples = hospitalData?.num_examples ?? 0;
  const pqc = hospitalData?.pqc_encrypted ?? false;
  const quantum = hospitalData?.quantum_layer ?? false;

  return (
    <div
      className="flex flex-col gap-4 rounded-[1.5rem] p-5"
      style={{
        background: "var(--surface)",
        border: "1.5px solid var(--border)",
        boxShadow: "0 16px 34px rgba(120, 88, 103, 0.08)",
      }}
    >
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-lg font-bold text-white" style={{ background: color }}>
          {short}
        </div>
        <div className="min-w-0">
          <div className="text-sm font-semibold" style={{ color: "var(--text-1)" }}>
            {name}
          </div>
          <div className="mt-1 flex flex-wrap gap-1.5">
            <span className="rounded-full px-2 py-0.5 text-xs" style={{ background: "var(--success-light)", color: "var(--success)" }}>
              ✅ ออนไลน์
            </span>
            {pqc ? (
              <span className="rounded-full px-2 py-0.5 text-xs" style={{ background: "var(--surface-info)", color: "var(--info)" }}>
                🔐 ML-KEM-512
              </span>
            ) : null}
            {quantum ? (
              <span className="rounded-full px-2 py-0.5 text-xs" style={{ background: "var(--accent-light)", color: "var(--accent)" }}>
                ✨ VQC
              </span>
            ) : null}
          </div>
        </div>
      </div>

      <div className="rounded-[1.25rem] py-4 text-center text-4xl font-bold font-mono" style={{ color, fontFamily: "var(--font-mono)" }}>
        {auc}%
      </div>
      <div className="text-center text-xs" style={{ color: "var(--text-3)" }}>
        Local AUC (รอบ {latest?.round ?? "—"})
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-[1rem] p-3 text-center" style={{ background: "var(--surface-2)", border: "1px solid var(--border)" }}>
          <div className="text-xs" style={{ color: "var(--text-3)" }}>
            เคสฝึก
          </div>
          <div className="text-lg font-bold font-mono" style={{ color: "var(--text-1)", fontFamily: "var(--font-mono)" }}>
            {examples}
          </div>
        </div>
        <div className="rounded-[1rem] p-3 text-center" style={{ background: "var(--surface-2)", border: "1px solid var(--border)" }}>
          <div className="text-xs" style={{ color: "var(--text-3)" }}>
            รอบ PQC
          </div>
          <div className="text-lg font-bold font-mono" style={{ color: "var(--text-1)", fontFamily: "var(--font-mono)" }}>
            {latest?.pqc_rounds ?? "—"}
          </div>
        </div>
      </div>
    </div>
  );
}
