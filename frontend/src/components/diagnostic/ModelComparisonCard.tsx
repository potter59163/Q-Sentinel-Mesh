"use client";

import type { HemorrhageProbabilities } from "@/types/api";

interface Props {
  baselineProbs: HemorrhageProbabilities;
  hybridProbs: HemorrhageProbabilities;
  quantumGain?: number;
}

export default function ModelComparisonCard({ baselineProbs, hybridProbs, quantumGain }: Props) {
  const baselineAny = Math.round((baselineProbs.any ?? 0) * 100);
  const hybridAny = Math.round((hybridProbs.any ?? 0) * 100);
  const gain = quantumGain ?? hybridAny - baselineAny;
  const leader = hybridAny >= baselineAny ? "✨ Hybrid เด่นกว่า" : "🧪 Baseline เด่นกว่า";

  return (
    <div className="rounded-[1.5rem] p-5" style={{ background: "var(--surface)", border: "1.5px solid var(--border)" }}>
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <div className="q-eyebrow">เปรียบเทียบโมเดล</div>
          <div className="mt-1 text-sm font-semibold" style={{ color: "var(--text-1)" }}>
            เทียบความมั่นใจของ hybrid และ baseline ในเคสปัจจุบัน
          </div>
        </div>
        <span className="q-pill q-pill-accent">{leader}</span>
      </div>

      <div className="grid gap-3 text-center md:grid-cols-3">
        <div className="rounded-[1.2rem] p-4" style={{ background: "var(--surface-2)", border: "1px solid var(--border)" }}>
          <div className="text-[11px] uppercase tracking-[0.18em]" style={{ color: "var(--text-3)" }}>
            CNN Baseline
          </div>
          <div className="mt-2 text-3xl font-bold font-mono" style={{ color: "var(--text-2)", fontFamily: "var(--font-mono)" }}>
            {baselineAny}%
          </div>
          <div className="mt-2 text-xs" style={{ color: "var(--text-3)" }}>
            ความมั่นใจอ้างอิง
          </div>
        </div>

        <div className="rounded-[1.2rem] p-4" style={{ background: "var(--accent-light)", border: "1px solid var(--accent-soft)" }}>
          <div className="text-[11px] uppercase tracking-[0.18em]" style={{ color: "var(--accent)" }}>
            Q-Sentinel Hybrid
          </div>
          <div className="mt-2 text-3xl font-bold font-mono" style={{ color: "var(--accent)", fontFamily: "var(--font-mono)" }}>
            {hybridAny}%
          </div>
          <div className="mt-2 text-xs" style={{ color: "var(--text-2)" }}>
            โมเดลหลักที่กำลังใช้งาน
          </div>
        </div>

        <div className="rounded-[1.2rem] p-4" style={{ background: "var(--success-light)", border: "1px solid var(--success-soft)" }}>
          <div className="text-[11px] uppercase tracking-[0.18em]" style={{ color: "var(--success)" }}>
            Quantum Gain
          </div>
          <div className="mt-2 text-3xl font-bold font-mono" style={{ color: "var(--success)", fontFamily: "var(--font-mono)" }}>
            {gain >= 0 ? "+" : ""}
            {gain.toFixed(1)}%
          </div>
          <div className="mt-2 text-xs" style={{ color: "var(--text-2)" }}>
            ต่างจาก baseline
          </div>
        </div>
      </div>
    </div>
  );
}
