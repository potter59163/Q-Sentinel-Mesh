"use client";

import type { HemorrhageProbabilities, HemorrhageThresholds } from "@/types/api";
import { HEMORRHAGE_LABELS } from "@/lib/hemorrhageLabels";

const COLORS: Record<string, string> = {
  epidural: "#d66d86",
  intraparenchymal: "#c7516c",
  intraventricular: "#dd8a63",
  subarachnoid: "#d7a05f",
  subdural: "#a46aa6",
  any: "#c25b86",
};

interface Props {
  probabilities: HemorrhageProbabilities;
  thresholds?: HemorrhageThresholds;
}

export default function ProbabilityBars({ probabilities, thresholds }: Props) {
  const subtypes = ["any", "epidural", "subdural", "subarachnoid", "intraparenchymal", "intraventricular"] as const;

  return (
    <div className="space-y-3.5">
      {subtypes.map((key) => {
        const prob = probabilities[key] ?? 0;
        const threshold = thresholds?.[key] ?? 0.5;
        const positive = prob >= threshold;
        const percent = Math.round(prob * 100);
        const color = COLORS[key];

        return (
          <div
            key={key}
            className="grid grid-cols-[minmax(0,120px)_minmax(0,1fr)_52px] items-center gap-3 rounded-[1.1rem] border px-3 py-3 sm:grid-cols-[minmax(0,160px)_minmax(0,1fr)_64px]"
            style={{
              background: positive ? `${color}0d` : "rgba(255,255,255,0.58)",
              borderColor: positive ? `${color}33` : "var(--border)",
            }}
          >
            <div className="min-w-0">
              <div className="truncate text-xs font-semibold uppercase tracking-[0.08em]" style={{ color: positive ? color : "var(--text-2)" }}>
                {HEMORRHAGE_LABELS[key]}
              </div>
              <div className="mt-0.5 text-[11px]" style={{ color: "var(--text-3)" }}>
                เกณฑ์ {Math.round(threshold * 100)}%
              </div>
            </div>

            <div>
              <div className="relative h-3.5 overflow-hidden rounded-full" style={{ background: "var(--surface-2)", border: "1px solid var(--border)" }}>
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${percent}%`,
                    background: `linear-gradient(90deg, ${color}, ${color}cc)`,
                    opacity: positive ? 1 : 0.56,
                  }}
                />
                {thresholds ? (
                  <div
                    className="absolute bottom-0 top-0 w-[2px]"
                    style={{ left: `${Math.round(threshold * 100)}%`, background: "rgba(65,43,52,0.35)" }}
                  />
                ) : null}
              </div>
              <div className="mt-1 flex justify-end">
                <span
                  className="rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
                  style={{
                    background: positive ? `${color}20` : "var(--surface-2)",
                    border: `1px solid ${positive ? `${color}40` : "var(--border)"}`,
                    color: positive ? color : "var(--text-3)",
                  }}
                >
                  {positive ? "เกินเกณฑ์" : "ต่ำกว่าเกณฑ์"}
                </span>
              </div>
            </div>

            <div className="text-right text-sm font-bold" style={{ color: positive ? color : "var(--text-3)", fontFamily: "var(--font-mono)" }}>
              {percent}%
            </div>
          </div>
        );
      })}
    </div>
  );
}
