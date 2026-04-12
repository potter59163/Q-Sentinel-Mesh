"use client";

import { useState } from "react";
import { toast } from "sonner";
import api from "@/lib/api";
import type { FeedbackRequest, RadiologistVerdict } from "@/types/api";

const HEMORRHAGE_TYPES = [
  "epidural",
  "intraparenchymal",
  "intraventricular",
  "subarachnoid",
  "subdural",
  "any",
];

interface RadiologistReviewProps {
  sessionId: string;
  topClass: string;
  confidence: number;
  hospital: string;
  filename?: string;
  onVerdictSubmitted?: (verdict: RadiologistVerdict, correctedClass?: string) => void;
}

export default function RadiologistReview({
  sessionId,
  topClass,
  confidence,
  hospital,
  filename,
  onVerdictSubmitted,
}: RadiologistReviewProps) {
  const [verdict, setVerdict] = useState<RadiologistVerdict | null>(null);
  const [correctedClass, setCorrectedClass] = useState<string>(topClass);
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  async function handleSubmit(v: RadiologistVerdict) {
    setVerdict(v);
    setLoading(true);

    const body: FeedbackRequest = {
      session_id: sessionId,
      verdict: v,
      correction: v === "correct" ? correctedClass : undefined,
      hospital,
      top_class: topClass,
      confidence,
      filename,
    };

    try {
      await api.post<{ feedback_id: string; saved: boolean }>("/api/feedback", body);
      setSubmitted(true);
      toast.success("Radiologist feedback saved");
      onVerdictSubmitted?.(v, v === "correct" ? correctedClass : undefined);
    } catch {
      toast.error("Could not save feedback — please retry.");
      setVerdict(null);
    } finally {
      setLoading(false);
    }
  }

  if (submitted) {
    const labels: Record<RadiologistVerdict, { icon: string; text: string; color: string }> = {
      confirm: { icon: "✅", text: "AI result confirmed", color: "var(--success)" },
      reject: { icon: "❌", text: "AI result rejected", color: "var(--warning)" },
      correct: { icon: "✏️", text: `Corrected to: ${correctedClass}`, color: "var(--accent)" },
    };
    const meta = labels[verdict!];

    return (
      <div
        className="rounded-[1rem] border px-4 py-3 text-sm"
        style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}
      >
        <div className="q-eyebrow mb-2">Radiologist Review</div>
        <div className="flex items-center gap-2 font-semibold" style={{ color: meta.color }}>
          <span>{meta.icon}</span>
          <span>{meta.text}</span>
        </div>
        <div className="mt-1 text-xs" style={{ color: "var(--text-3)" }}>
          Feedback saved · contributes to federated model improvement
        </div>
      </div>
    );
  }

  return (
    <div
      className="rounded-[1rem] border px-4 py-4"
      style={{ background: "var(--surface-2)", borderColor: "var(--border-strong)" }}
    >
      <div className="q-eyebrow mb-1">Radiologist Review</div>
      <div className="mb-3 text-xs leading-5" style={{ color: "var(--text-2)" }}>
        Review the AI prediction and submit your verdict. Feedback is used to improve the federated model.
      </div>

      {/* AI summary */}
      <div
        className="mb-3 rounded-[0.75rem] border px-3 py-2 text-xs"
        style={{ background: "var(--surface)", borderColor: "var(--border)" }}
      >
        <span style={{ color: "var(--text-3)" }}>AI predicted: </span>
        <span className="font-semibold" style={{ color: "var(--accent)" }}>
          {topClass}
        </span>
        <span style={{ color: "var(--text-3)" }}> ({Math.round(confidence * 100)}% confidence)</span>
      </div>

      {/* Verdict buttons */}
      <div className="mb-3 grid grid-cols-3 gap-2">
        {(
          [
            { v: "confirm" as const, icon: "✅", label: "Confirm", color: "var(--success)" },
            { v: "reject" as const, icon: "❌", label: "Reject", color: "var(--warning)" },
            { v: "correct" as const, icon: "✏️", label: "Correct", color: "var(--accent)" },
          ] as const
        ).map(({ v, icon, label, color }) => (
          <button
            key={v}
            type="button"
            disabled={loading}
            onClick={() => {
              if (v === "correct") {
                setVerdict("correct");
              } else {
                handleSubmit(v);
              }
            }}
            className="flex flex-col items-center gap-1 rounded-[0.75rem] border py-2.5 text-xs font-semibold transition-all"
            style={{
              background: verdict === v ? `color-mix(in srgb, ${color} 12%, var(--surface))` : "var(--surface)",
              borderColor: verdict === v ? color : "var(--border)",
              color: verdict === v ? color : "var(--text-2)",
              opacity: loading ? 0.6 : 1,
            }}
          >
            <span className="text-base">{icon}</span>
            {label}
          </button>
        ))}
      </div>

      {/* Correction picker */}
      {verdict === "correct" && (
        <div className="flex flex-col gap-2">
          <select
            value={correctedClass}
            onChange={(e) => setCorrectedClass(e.target.value)}
            className="q-select text-xs"
            style={{ borderRadius: "0.75rem", padding: "0.5rem 0.75rem" }}
          >
            {HEMORRHAGE_TYPES.map((t) => (
              <option key={t} value={t}>
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </option>
            ))}
            <option value="no_hemorrhage">No hemorrhage</option>
          </select>
          <button
            type="button"
            disabled={loading}
            onClick={() => handleSubmit("correct")}
            className="q-btn-primary w-full py-2 text-xs font-bold"
            style={{ opacity: loading ? 0.6 : 1 }}
          >
            {loading ? "Saving..." : "Submit Correction"}
          </button>
        </div>
      )}
    </div>
  );
}
