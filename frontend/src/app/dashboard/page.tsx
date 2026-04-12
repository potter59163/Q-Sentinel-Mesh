"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import CTViewer from "@/components/diagnostic/CTViewer";
import ModelComparisonCard from "@/components/diagnostic/ModelComparisonCard";
import ProbabilityBars from "@/components/diagnostic/ProbabilityBars";
import RadiologistReview from "@/components/diagnostic/RadiologistReview";
import { useDashboard } from "@/context/DashboardContext";
import { usePrediction } from "@/hooks/usePrediction";
import { useWindowedSlice } from "@/hooks/useWindowedSlice";
import api, { withRetry } from "@/lib/api";
import { formatHemorrhageLabel } from "@/lib/hemorrhageLabels";
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
    setLastSessionId,
    setLastVerdict,
    setLastCorrectedClass,
  } = useDashboard();

  const [sliceOverrides, setSliceOverrides] = useState<Record<string, number>>({});
  const [sessionId, setSessionId] = useState<string | null>(null);
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
    setLastSessionId(null);
    setLastVerdict(null);
    setLastCorrectedClass(null);
  }, [ctMeta?.s3_key, modelType, reset, setLastHeatmapSrc, setLastImageSrc, setLastResult, setLastSessionId, setLastVerdict, setLastCorrectedClass]);

  useEffect(() => {
    if (result) {
      setLastResult(result);
      setLastHeatmapSrc(result.heatmap_b64 ?? null);
    }
  }, [result, setLastHeatmapSrc, setLastResult]);

  useEffect(() => {
    if (result && imageSrc) {
      setLastImageSrc(imageSrc);
    }
  }, [imageSrc, result, setLastImageSrc]);

  useEffect(() => {
    if (inferError) toast.error(inferError);
  }, [inferError]);

  async function handleRunAI() {
    if (!ctMeta?.s3_key) {
      toast.warning("กรุณาโหลด CT scan ก่อน");
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
      const sid = crypto.randomUUID();
      setSessionId(sid);
      setLastSessionId(sid);
      setLastVerdict(null);
      setLastCorrectedClass(null);
    }
  }

  const detected = result ? result.probabilities.any >= threshold : false;
  const modelLabel = modelType === "hybrid" ? "Q-Sentinel Hybrid" : "CNN Baseline";
  const statusMeta = result
    ? [
        modelType === "hybrid" ? "โมเดล Hybrid" : "โมเดล Baseline",
        "อุปกรณ์: CPU",
        autoTriage ? "โหมด: Auto-triage" : "โหมด: เลือกสไลซ์เอง",
        `Threshold ${threshold.toFixed(2)}`,
        lastLatencyMs !== null ? `Latency ${lastLatencyMs} ms` : "Latency -",
        lastRequestId ? `Request ${lastRequestId}` : "Request -",
      ]
    : [];

  return (
    <div className="q-dashboard-stack">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 2xl:grid-cols-3">
        <SummaryCard
          label="เคส"
          value={ctMeta ? ctMeta.filename : "รอข้อมูล"}
          note={ctMeta ? `${ctMeta.slice_count} สไลซ์พร้อมใช้งาน` : "เลือกเคสตัวอย่างหรืออัปโหลด CT scan จากแถบด้านข้าง"}
          valueColor={ctMeta ? "var(--accent)" : "var(--text-2)"}
        />
        <SummaryCard
          label="เกณฑ์ตัดสิน"
          value={threshold.toFixed(2)}
          note="ยิ่ง threshold ต่ำ ระบบจะจับรอยโรคละเอียดขึ้น แต่โอกาส false positive ก็อาจเพิ่มขึ้น"
          valueColor="var(--accent)"
        />
        <SummaryCard
          label="ผลล่าสุด"
          value={result ? `${Math.round(result.confidence * 100)}%` : "-"}
          note={result ? `คลาสเด่น: ${formatHemorrhageLabel(result.top_class)}` : "รัน AI เพื่อแสดงคะแนนความมั่นใจล่าสุด"}
          valueColor={result ? (detected ? "var(--accent)" : "var(--success)") : "var(--text-2)"}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
        <section className="q-card overflow-hidden">
          <div className="border-b px-6 py-5" style={{ borderColor: "var(--border)" }}>
            <div className="q-eyebrow mb-1">ภาพ CT</div>
            <div className="text-base font-semibold" style={{ color: "var(--text-1)" }}>
              ดูสไลซ์
            </div>
            <p className="mt-1 text-sm leading-6" style={{ color: "var(--text-2)" }}>
              เลื่อนดูสไลซ์ เปลี่ยน window preset และเปิด heatmap ทับภาพหลังจาก AI วิเคราะห์เสร็จ
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
                  ความทึบของ heatmap
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
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="q-eyebrow mb-1">AI Analysis</div>
                <div className="text-base font-semibold" style={{ color: "var(--text-1)" }}>
                  สรุปผลการตรวจจับ
                </div>
              </div>
              <div className="flex flex-wrap justify-end gap-1.5 pt-0.5">
                <span className="q-pill">{hospital}</span>
                <span className="q-pill q-pill-accent">{modelLabel}</span>
                <span className={`q-pill ${autoTriage ? "q-pill-success" : ""}`}>{autoTriage ? "Auto-triage" : "สไลซ์ปัจจุบัน"}</span>
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-5 p-5 sm:p-6">
            <div title={!ctMeta ? "กรุณาโหลด CT scan จากแถบด้านข้าง ก่อน" : undefined}>
              <button
                onClick={handleRunAI}
                disabled={!ctMeta || inferLoading}
                className="q-btn-primary w-full py-3.5 text-sm font-bold"
                style={{
                  cursor: !ctMeta || inferLoading ? "not-allowed" : "pointer",
                  opacity: !ctMeta || inferLoading ? 0.45 : 1,
                }}
              >
                {inferLoading ? "กำลังรันวิเคราะห์..." : "รัน AI วิเคราะห์"}
              </button>
              {!ctMeta && !inferLoading && (
                <p className="mt-1.5 text-center text-[0.72rem]" style={{ color: "var(--text-3)" }}>
                  โหลด CT scan จากแถบด้านข้าง เพื่อเปิดใช้งาน
                </p>
              )}
            </div>

            {inferLoading ? (
              <div
                className="rounded-[1.1rem] border px-4 py-4"
                style={{ background: "var(--surface-2)", borderColor: "var(--border-strong)" }}
              >
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold" style={{ color: "var(--text-1)" }}>
                      กำลังรัน AI Analysis
                    </div>
                    <div className="mt-1 text-xs" style={{ color: "var(--text-2)" }}>
                      กำลังเตรียม volume ประเมินสไลซ์ และสร้าง heatmap
                    </div>
                  </div>
                  <span className="q-pill q-pill-accent">กำลังทำงาน</span>
                </div>
                <div className="mt-4 h-1.5 w-full overflow-hidden rounded-full" style={{ background: "rgba(194,91,134,0.12)" }}>
                  <div className="q-progress-indeterminate h-full rounded-full" style={{ background: "var(--accent)" }} />
                </div>
                <div className="mt-3 grid gap-1 text-[11px]" style={{ color: "var(--text-3)" }}>
                  <span>1. โหลด volume และ window preset</span>
                  <span>2. รัน inference บนสไลซ์ปัจจุบัน</span>
                  <span>3. สร้าง heatmap overlay</span>
                </div>
              </div>
            ) : null}

            {inferError ? (
              <div
                className="rounded-[1rem] border px-4 py-3"
                style={{ background: "var(--surface-warning)", borderColor: "var(--warning-soft)" }}
              >
                <div className="text-sm font-semibold" style={{ color: "var(--warning)" }}>
                  การวิเคราะห์ไม่สำเร็จ
                </div>
                <div className="mt-1 text-xs leading-5" style={{ color: "var(--text-2)" }}>
                  {inferError}
                </div>
              </div>
            ) : null}

            {!ctMeta && !result ? (
              <div className="rounded-[1.25rem] border border-dashed px-6 py-14 text-center" style={{ background: "var(--surface-2)", borderColor: "var(--border-strong)" }}>
                <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full text-3xl" style={{ background: "var(--surface-3)" }}>
                  🫁
                </div>
                <div className="text-sm font-semibold" style={{ color: "var(--text-1)" }}>
                  ยังไม่มีข้อมูล CT
                </div>
                <p className="mt-1 text-xs leading-5" style={{ color: "var(--text-3)" }}>
                  เลือกเคสตัวอย่าง (P049–P099) หรืออัปโหลดไฟล์ NIfTI / DICOM จากแถบด้านข้าง
                </p>
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
                  AI Heatmap พร้อมใช้งาน
                </div>
                <p className="mt-1 text-xs leading-6" style={{ color: "var(--text-2)" }}>
                  กดรัน AI วิเคราะห์ เพื่อประเมินเลือดออกและสร้าง heatmap อธิบายผล
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
                      {detected ? formatHemorrhageLabel(result.top_class) : "ไม่พบเลือดออก"}
                    </div>
                    <div className="mt-0.5 text-xs" style={{ color: "var(--text-2)" }}>
                      ความมั่นใจ {Math.round(result.confidence * 100)}% · สไลซ์ {result.slice_used + 1}
                    </div>
                  </div>
                  <span className={`q-pill ${detected ? "q-pill-accent" : "q-pill-success"}`}>{detected ? "พบเลือดออก" : "ไม่พบเลือดออก"}</span>
                </div>
              </div>
            ) : null}

            {result ? (
              <div className="rounded-[1rem] border px-4 py-4" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
                <div className="q-eyebrow mb-3">ความน่าจะเป็นของการตรวจจับ</div>
                <ProbabilityBars probabilities={result.probabilities} thresholds={thresholds ?? undefined} />
              </div>
            ) : null}

            {result && sessionId ? (
              <RadiologistReview
                sessionId={sessionId}
                topClass={result.top_class}
                confidence={result.confidence}
                hospital={hospital}
                filename={ctMeta?.filename}
                onVerdictSubmitted={(v, corrected) => {
                  setLastVerdict(v);
                  setLastCorrectedClass(corrected ?? null);
                }}
              />
            ) : null}

            {result ? (
              <div
                className="rounded-[1rem] border px-4 py-3"
                style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}
              >
                <div className="q-eyebrow mb-2">สถานะการรัน</div>
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
  );
}

export default function DiagnosticPage() {
  return <DiagnosticWorkspace />;
}
