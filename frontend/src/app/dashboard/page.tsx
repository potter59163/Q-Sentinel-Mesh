"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import CTViewer from "@/components/diagnostic/CTViewer";
import ModelComparisonCard from "@/components/diagnostic/ModelComparisonCard";
import ProbabilityBars from "@/components/diagnostic/ProbabilityBars";
import { useDashboard } from "@/context/DashboardContext";
import { usePrediction } from "@/hooks/usePrediction";
import { useWindowedSlice } from "@/hooks/useWindowedSlice";
import api from "@/lib/api";
import type { HemorrhageThresholds, WindowPreset } from "@/types/api";

function SummaryCard({
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
    <article className="q-soft-panel q-summary-card rounded-[1.2rem] px-5 py-5">
      <div className="q-eyebrow mb-1">{label}</div>
      <div className="text-[1.7rem] font-bold leading-none" style={{ color: valueColor ?? "var(--text-1)", fontFamily: "var(--font-mono)" }}>
        {value}
      </div>
      <p className="mt-2.5 text-[0.79rem] leading-6" style={{ color: "var(--text-2)" }}>
        {note}
      </p>
    </article>
  );
}

function DiagnosticWorkspace() {
  const {
    modelType,
    threshold,
    autoTriage,
    ctMeta,
    hospital,
    incrementScans,
    setLastResult,
    setLastImageSrc,
    setLastHeatmapSrc,
  } = useDashboard();

  const [sliceIdx, setSliceIdx] = useState(0);
  const [window, setWindow] = useState<WindowPreset>("brain");
  const [heatmapOpacity, setHeatmapOpacity] = useState(0.6);
  const [thresholds, setThresholds] = useState<HemorrhageThresholds | null>(null);

  const { imageSrc, loading: sliceLoading, fetchSlice } = useWindowedSlice();
  const { result, loading: inferLoading, error: inferError, predict } = usePrediction();

  useEffect(() => {
    api.get("/api/thresholds").then((r) => setThresholds(r.data)).catch(() => {});
  }, []);

  useEffect(() => {
    if (ctMeta?.s3_key) fetchSlice(ctMeta.s3_key, sliceIdx, window);
  }, [ctMeta?.s3_key, sliceIdx, window, fetchSlice]);

  useEffect(() => {
    if (inferError) toast.error(inferError);
  }, [inferError]);

  async function handleRunAI() {
    if (!ctMeta?.s3_key) {
      toast.warning("Load a CT scan first.");
      return;
    }
    incrementScans();
    const res = await predict({
      s3_key: ctMeta.s3_key,
      slice_idx: sliceIdx,
      model_type: modelType,
      threshold,
      auto_triage: autoTriage,
    });
    if (res) {
      setSliceIdx(res.slice_used);
      setLastResult(res);
      setLastImageSrc(imageSrc ?? null);
      setLastHeatmapSrc(res.heatmap_b64 ?? null);
    }
  }

  const detected = result ? result.probabilities.any >= threshold : false;
  const modelLabel = modelType === "hybrid" ? "Q-Sentinel Hybrid" : "CNN Baseline";

  return (
    <>
      <div className="q-dashboard-stack">
      <section className="q-dashboard-intro">
        <div className="q-dashboard-intro-row">
          <div className="q-dashboard-intro-copy">
            <div className="q-eyebrow mb-1">Diagnostic Workspace</div>
            <div className="q-dashboard-intro-title">CT hemorrhage review</div>
            <p className="q-dashboard-intro-text">
              Inspect slices, trigger the active model, and review explanation overlays and subtype probabilities in one place.
            </p>
          </div>
          <div className="q-kicker-row">
            <span className="q-pill">{hospital}</span>
            <span className="q-pill q-pill-accent">{modelLabel}</span>
            <span className={`q-pill ${autoTriage ? "q-pill-success" : ""}`}>{autoTriage ? "Auto-triage" : "Current slice"}</span>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 2xl:grid-cols-3">
        <SummaryCard
          label="Case"
          value={ctMeta ? ctMeta.filename : "Waiting"}
          note={ctMeta ? `${ctMeta.slice_count} slices loaded and ready for review.` : "Load a demo case or upload a CT scan from the sidebar."}
          valueColor={ctMeta ? "var(--accent)" : "var(--text-2)"}
        />
        <SummaryCard
          label="Decision Threshold"
          value={threshold.toFixed(2)}
          note="Lower thresholds catch subtler findings but may increase false positives."
          valueColor="var(--accent)"
        />
        <SummaryCard
          label="Latest Result"
          value={result ? `${Math.round(result.confidence * 100)}%` : "-"}
          note={result ? `Top class: ${result.top_class}` : "Run AI analysis to populate the latest confidence score."}
          valueColor={result ? (detected ? "var(--accent)" : "var(--success)") : "var(--text-2)"}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
        <section className="q-card overflow-hidden">
          <div className="border-b px-6 py-5" style={{ borderColor: "var(--border)" }}>
            <div className="q-eyebrow mb-1">CT Viewer</div>
            <div className="text-base font-semibold" style={{ color: "var(--text-1)" }}>
              Slice inspection
            </div>
            <p className="mt-1 text-sm leading-6" style={{ color: "var(--text-2)" }}>
              Move through the study, switch window presets, and overlay the heatmap once the model has run.
            </p>
          </div>

          <div className="p-5 sm:p-6">
            <CTViewer
              imageSrc={imageSrc}
              heatmapSrc={result?.heatmap_b64 ?? null}
              sliceIdx={sliceIdx}
              sliceCount={ctMeta?.slice_count ?? 0}
              window={window}
              heatmapOpacity={heatmapOpacity}
              onSliceChange={setSliceIdx}
              onWindowChange={setWindow}
              loading={sliceLoading}
            />

            {result?.heatmap_b64 ? (
              <div className="mt-3 flex items-center gap-3">
                <span className="shrink-0 text-xs" style={{ color: "var(--text-3)" }}>
                  Heatmap opacity
                </span>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={Math.round(heatmapOpacity * 100)}
                  onChange={(e) => setHeatmapOpacity(Number(e.target.value) / 100)}
                  className="flex-1"
                  style={{ accentColor: "var(--accent)" }}
                />
                <span className="q-value shrink-0 text-xs" style={{ color: "var(--accent)" }}>
                  {Math.round(heatmapOpacity * 100)}%
                </span>
              </div>
            ) : null}
          </div>
        </section>

        <section className="q-card overflow-hidden">
          <div className="border-b px-6 py-5" style={{ borderColor: "var(--border)" }}>
            <div className="q-eyebrow mb-1">AI Analysis</div>
            <div className="text-base font-semibold" style={{ color: "var(--text-1)" }}>
              Detection summary
            </div>
            <p className="mt-1 text-sm leading-6" style={{ color: "var(--text-2)" }}>
              Run the active model and read the output, confidence, and subtype distribution from the same panel.
            </p>
          </div>

          <div className="flex flex-col gap-5 p-5 sm:p-6">
            <button
              onClick={handleRunAI}
              disabled={!ctMeta || inferLoading}
              className="q-btn-primary w-full py-3.5 text-sm font-bold"
              style={{
                cursor: !ctMeta || inferLoading ? "not-allowed" : "pointer",
                opacity: !ctMeta || inferLoading ? 0.55 : 1,
              }}
            >
              {inferLoading ? "Running analysis..." : "Run AI Analysis"}
            </button>

            {!ctMeta && !result ? (
              <div className="rounded-[1.25rem] border border-dashed px-6 py-12 text-center" style={{ background: "var(--surface-2)", borderColor: "var(--border-strong)" }}>
                <div className="text-sm font-semibold" style={{ color: "var(--text-2)" }}>
                  Load a CT scan to begin
                </div>
              </div>
            ) : null}

            {result ? (
              <div
                className="rounded-[1rem] border px-4 py-3"
                style={{
                  background: detected ? "var(--surface-3)" : "var(--surface-success)",
                  borderColor: detected ? "var(--accent-soft)" : "var(--success-soft)",
                }}
              >
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <div className="text-sm font-bold" style={{ color: detected ? "var(--accent)" : "var(--success)" }}>
                      {detected ? result.top_class.toUpperCase() : "No hemorrhage"}
                    </div>
                    <div className="mt-0.5 text-xs" style={{ color: "var(--text-2)" }}>
                      Confidence {Math.round(result.confidence * 100)}% - Slice {result.slice_used + 1}
                    </div>
                  </div>
                  <span className={`q-pill ${detected ? "q-pill-accent" : "q-pill-success"}`}>{detected ? "Detected" : "Clear"}</span>
                </div>
              </div>
            ) : null}

            {result ? (
              <div className="rounded-[1rem] border px-4 py-4" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
                <div className="q-eyebrow mb-3">Detection Probabilities</div>
                <ProbabilityBars probabilities={result.probabilities} thresholds={thresholds ?? undefined} />
              </div>
            ) : null}

            {result && modelType === "hybrid" && result.baseline_probs ? (
              <ModelComparisonCard baselineProbs={result.baseline_probs} hybridProbs={result.probabilities} quantumGain={result.quantum_gain} />
            ) : null}
          </div>
        </section>
      </div>
      </div>
    </>
  );
}

export default function DiagnosticPage() {
  return <DiagnosticWorkspace />;
}
