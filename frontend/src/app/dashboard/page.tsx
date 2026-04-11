"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import CTViewer from "@/components/diagnostic/CTViewer";
import ModelComparisonCard from "@/components/diagnostic/ModelComparisonCard";
import ProbabilityBars from "@/components/diagnostic/ProbabilityBars";
import { useDashboard } from "@/context/DashboardContext";
import { usePrediction } from "@/hooks/usePrediction";
import { useWindowedSlice } from "@/hooks/useWindowedSlice";
import api, { withRetry } from "@/lib/api";
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

  const [sliceOverrides, setSliceOverrides] = useState<Record<string, number>>({});
  const [window, setWindow] = useState<WindowPreset>("brain");
  const [heatmapOpacity, setHeatmapOpacity] = useState(0.6);
  const [thresholds, setThresholds] = useState<HemorrhageThresholds | null>(null);

  const { imageSrc, loading: sliceLoading, error: sliceError, fetchSlice } = useWindowedSlice();
  const { result, loading: inferLoading, error: inferError, predict, reset, lastLatencyMs, lastRequestId } = usePrediction();
  const ctKey = ctMeta?.s3_key ?? "";
  const computedSliceIdx = ctMeta?.slice_count ? Math.floor((ctMeta.slice_count - 1) / 2) : 0;
  const sliceIdx = ctKey && sliceOverrides[ctKey] !== undefined ? sliceOverrides[ctKey] : computedSliceIdx;
  const setSliceIdx = (idx: number) => {
    const key = ctKey || "none";
    setSliceOverrides((prev) => ({ ...prev, [key]: idx }));
  };

  useEffect(() => {
    withRetry(() => api.get("/api/thresholds"), 2, 500)
      .then((r) => setThresholds(r.data))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (ctMeta?.s3_key) fetchSlice(ctMeta.s3_key, sliceIdx, window);
  }, [ctMeta?.s3_key, sliceIdx, window, fetchSlice]);

  useEffect(() => {
    reset();
    setLastResult(null);
    setLastImageSrc(null);
    setLastHeatmapSrc(null);
  }, [ctMeta?.s3_key, modelType, reset, setLastHeatmapSrc, setLastImageSrc, setLastResult]);

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
  const statusMeta = result
    ? [
        modelType === "hybrid" ? "Hybrid model" : "Baseline model",
        "Device: CPU",
        autoTriage ? "Auto-triage" : "Manual slice",
        `Threshold ${threshold.toFixed(2)}`,
        lastLatencyMs !== null ? `Latency ${lastLatencyMs} ms` : "Latency —",
        lastRequestId ? `Request ${lastRequestId}` : "Request —",
      ]
    : [];

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

            {sliceError ? (
              <div
                className="mt-3 rounded-[1rem] border px-4 py-3 text-xs"
                style={{ background: "var(--surface-warning)", borderColor: "var(--warning-soft)", color: "var(--warning)" }}
              >
                {sliceError}
              </div>
            ) : null}

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

            {inferLoading ? (
              <div
                className="rounded-[1.1rem] border px-4 py-4"
                style={{ background: "var(--surface-2)", borderColor: "var(--border-strong)" }}
              >
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold" style={{ color: "var(--text-1)" }}>
                      Running AI Analysis
                    </div>
                    <div className="mt-1 text-xs" style={{ color: "var(--text-2)" }}>
                      Preparing volume, evaluating slices, and generating the heatmap.
                    </div>
                  </div>
                  <span className="q-pill q-pill-accent">Live</span>
                </div>
                <div className="mt-4 h-2 w-full overflow-hidden rounded-full" style={{ background: "rgba(194,91,134,0.12)" }}>
                  <div className="h-full w-2/3 animate-pulse rounded-full" style={{ background: "var(--accent)" }} />
                </div>
                <div className="mt-3 grid gap-1 text-[11px]" style={{ color: "var(--text-3)" }}>
                  <span>1. Load volume and window preset</span>
                  <span>2. Run model inference on active slice</span>
                  <span>3. Compose heatmap overlay</span>
                </div>
              </div>
            ) : null}

            {inferError ? (
              <div
                className="rounded-[1rem] border px-4 py-3"
                style={{ background: "var(--surface-warning)", borderColor: "var(--warning-soft)" }}
              >
                <div className="text-sm font-semibold" style={{ color: "var(--warning)" }}>
                  Analysis failed
                </div>
                <div className="mt-1 text-xs leading-5" style={{ color: "var(--text-2)" }}>
                  {inferError}
                </div>
              </div>
            ) : null}

            {!ctMeta && !result ? (
              <div className="rounded-[1.25rem] border border-dashed px-6 py-12 text-center" style={{ background: "var(--surface-2)", borderColor: "var(--border-strong)" }}>
                <div className="text-sm font-semibold" style={{ color: "var(--text-2)" }}>
                  Load a CT scan to begin
                </div>
              </div>
            ) : null}

            {ctMeta && !result ? (
              <div
                className="rounded-[1.25rem] border border-dashed px-6 py-10 text-center"
                style={{ background: "var(--surface-2)", borderColor: "var(--border-strong)" }}
              >
                <div
                  className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full"
                  style={{ background: "var(--surface-3)", color: "var(--accent)" }}
                >
                  <svg width="28" height="28" viewBox="0 0 24 24" aria-hidden="true">
                    <path
                      d="M9.6 5.2a3.6 3.6 0 0 0-3.2 3.6v1.1a3.2 3.2 0 0 0 0 6.4h.6v.9a2.4 2.4 0 0 0 2.4 2.4h3.1v-3.2a2.8 2.8 0 0 1 2.8-2.8h2.8V9.8A4.6 4.6 0 0 0 13.3 5h-3.7Z"
                      fill="currentColor"
                      opacity="0.28"
                    />
                    <path
                      d="M10 5.1a3.9 3.9 0 0 0-3.5 3.8v1.2a3.4 3.4 0 0 0 0 6.8h.6v.8a2.6 2.6 0 0 0 2.6 2.6H13"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.3"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    <path
                      d="M13 20v-3a3.2 3.2 0 0 1 3.2-3.2h2.8V9.8A4.8 4.8 0 0 0 14.2 5H12"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.3"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
                <div className="text-sm font-semibold" style={{ color: "var(--text-1)" }}>
                  AI Heatmap Ready
                </div>
                <p className="mt-1 text-xs leading-6" style={{ color: "var(--text-2)" }}>
                  Click Run AI Analysis to detect hemorrhage and generate the explainability map.
                </p>
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

            {result ? (
              <div
                className="rounded-[1rem] border px-4 py-3"
                style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}
              >
                <div className="q-eyebrow mb-2">Run Status</div>
                <div className="grid gap-1 text-[11px]" style={{ color: "var(--text-2)" }}>
                  {statusMeta.map((line) => (
                    <div key={line}>{line}</div>
                  ))}
                </div>
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
