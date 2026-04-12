"use client";

import { useCallback, useEffect, useState, type CSSProperties } from "react";
import { useDropzone } from "react-dropzone";
import { toast } from "sonner";
import api, { getApiErrorMessage, withRetry } from "@/lib/api";
import type { HL7ExportRequest, HL7ExportResponse } from "@/types/api";
import { useDashboard } from "@/context/DashboardContext";
import type { CTUploadResponse } from "@/types/api";

const HOSPITALS = [
  "Hospital A (Bangkok)",
  "Hospital B (Chiang Mai)",
  "Hospital C (Khon Kaen)",
];

function Divider() {
  return <div className="q-sb-divider" />;
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <div className="q-sb-label">{children}</div>;
}

function StatusRow({
  label,
  value,
  valueStyle,
}: {
  label: string;
  value: string;
  valueStyle?: CSSProperties;
}) {
  return (
    <div className="q-sb-row">
      <span>{label}</span>
      <span className="q-sb-value" style={valueStyle}>
        {value}
      </span>
    </div>
  );
}

export default function Sidebar() {
  const {
    modelType, setModelType,
    hospital, setHospital,
    ctMeta, setCtMeta,
    threshold, setThreshold,
    autoTriage, setAutoTriage,
    lastResult, lastImageSrc, lastHeatmapSrc,
    lastVerdict, lastCorrectedClass,
  } = useDashboard();

  const [open, setOpen] = useState(true);
  const [isMobile, setIsMobile] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);
  const [demoPatients, setDemoPatients] = useState<string[]>([]);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [hl7Loading, setHl7Loading] = useState(false);

  useEffect(() => {
    function check() {
      const mobile = window.innerWidth < 1024;
      setIsMobile(mobile);
      if (mobile) setOpen(false);
    }

    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  useEffect(() => {
    withRetry(() => api.get<{ patients: string[] }>("/api/ct/demo"), 2, 500)
      .then((r) => setDemoPatients(r.data.patients))
      .catch(() => setDemoPatients(["049"]));
  }, []);

  const onDrop = useCallback(async (accepted: File[]) => {
    if (!accepted[0]) return;
    setUploading(true);

    try {
      const form = new FormData();
      form.append("file", accepted[0]);
      const res = await api.post<CTUploadResponse>("/api/ct/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 120_000,
      });
      setCtMeta(res.data);
      toast.success(`โหลด CT แล้ว · พร้อมอ่าน ${res.data.slice_count} สไลซ์`);
    } catch (err) {
      toast.error(getApiErrorMessage(err));
    } finally {
      setUploading(false);
    }
  }, [setCtMeta]);

  async function loadDemo(pid: string) {
    setDemoLoading(true);
    try {
      const res = await api.get<CTUploadResponse>(`/api/ct/demo/${pid}`);
      setCtMeta(res.data);
      toast.success(`โหลดผู้ป่วย ${pid} แล้ว · ${res.data.slice_count} สไลซ์`);
    } catch {
      toast.error(`ไม่สามารถโหลดเคสตัวอย่าง ${pid} ได้`);
    } finally {
      setDemoLoading(false);
    }
  }

  async function handleExportHL7() {
    if (!lastResult) {
      toast.warning("กรุณารัน AI ก่อนส่งออก");
      return;
    }
    setHl7Loading(true);
    try {
      const body: HL7ExportRequest = {
        hospital,
        top_class: lastResult.top_class,
        confidence: lastResult.confidence,
        probabilities: lastResult.probabilities,
        filename: ctMeta?.filename,
        radiologist_verdict: lastVerdict ?? undefined,
        corrected_class: lastCorrectedClass ?? undefined,
        slice_used: lastResult.slice_used,
        model_type: modelType,
      };
      const res = await api.post<HL7ExportResponse>("/api/export/hl7", body);
      const fhirJson = JSON.stringify(res.data.fhir_json, null, 2);
      const blob = new Blob([fhirJson], { type: "application/fhir+json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `diagnostic-report-${res.data.resource_id.slice(0, 8)}.fhir.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("ส่งออก HL7 FHIR R4 แล้ว");
    } catch (err) {
      toast.error(`ส่งออก HL7 ไม่สำเร็จ: ${getApiErrorMessage(err)}`);
    } finally {
      setHl7Loading(false);
    }
  }

  async function handleExportPDF() {
    if (!lastResult) {
      toast.warning("กรุณารัน AI ก่อนส่งออก");
      return;
    }

    setPdfLoading(true);
    try {
      const { generateReportPDF } = await import("@/lib/pdfExport");
      await generateReportPDF({
        hospital,
        modelType,
        topClass: lastResult.top_class,
        confidence: lastResult.confidence,
        sliceUsed: lastResult.slice_used,
        probabilities: lastResult.probabilities,
        ctImageSrc: lastImageSrc ?? undefined,
        heatmapSrc: lastHeatmapSrc ?? undefined,
        filename: ctMeta?.filename,
      });
      toast.success("ส่งออกรายงาน PDF แล้ว");
    } catch (err) {
      console.error("PDF export error:", err);
      toast.error(`ส่งออก PDF ไม่สำเร็จ: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setPdfLoading(false);
    }
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/octet-stream": [".nii", ".nii.gz", ".dcm"] },
    multiple: false,
    disabled: uploading,
  });

  const sidebarClass = [
    "q-sidebar-v2",
    !open && !isMobile ? "q-sidebar-icon-only" : "",
    !open && isMobile ? "q-sidebar-hidden-mobile" : "",
  ].filter(Boolean).join(" ");

  const isIconOnly = !open && !isMobile;

  return (
    <>
      {isMobile && open && (
        <div className="q-sb-backdrop" onClick={() => setOpen(false)} />
      )}

      {isMobile && !open && (
        <button
          className="q-sb-float-btn"
          onClick={() => setOpen(true)}
          aria-label="เปิดแถบด้านข้าง"
        >
          ☰
        </button>
      )}

      <aside className={sidebarClass}>
        <div className={`mb-3 flex items-center gap-2 ${isIconOnly ? "flex-col" : "justify-between"}`}>
          <div className={`flex min-w-0 items-center gap-2 ${isIconOnly ? "flex-col" : ""}`}>
            <span className="shrink-0 text-2xl">🧠</span>
            {!isIconOnly && (
              <div className="min-w-0">
                <div
                  className="truncate text-[0.95rem] font-bold"
                  style={{ color: "var(--text-1)", fontFamily: "var(--font-heading-stack)" }}
                >
                  Q-Sentinel
                </div>
                <div
                  className="text-[0.58rem] uppercase tracking-widest"
                  style={{ color: "var(--text-3)" }}
                >
                  QSM
                </div>
              </div>
            )}
          </div>

          <button
            className="q-sb-toggle shrink-0"
            onClick={() => setOpen(!open)}
            aria-label={open ? "ย่อแถบด้านข้าง" : "ขยายแถบด้านข้าง"}
          >
            {open ? "‹" : "›"}
          </button>
        </div>

        {!isIconOnly && (
          <div className="mb-1 flex justify-center">
            <span className="q-pill q-pill-success text-[0.7rem]">● ออนไลน์</span>
          </div>
        )}
        {isIconOnly && (
          <span
            className="text-[0.6rem] font-bold"
            style={{ color: "var(--success)" }}
            title="ออนไลน์"
          >
            ●
          </span>
        )}

        {!isIconOnly && (
          <>
            <Divider />

            <SectionLabel>สถานะระบบ</SectionLabel>
            <StatusRow label="Compute" value="CPU Mode" />
            <StatusRow
              label="AI Model"
              value="CT-ICH (AUC 96%)"
              valueStyle={{ color: "var(--success)", fontSize: "0.72rem" }}
            />
            <StatusRow label="Federation" value="3 โหนด" />
            <StatusRow
              label="PQC"
              value="ML-KEM-512"
              valueStyle={{ color: "var(--accent)" }}
            />

            <Divider />

            <SectionLabel>โหนดโรงพยาบาล</SectionLabel>
            <select
              value={hospital}
              onChange={(e) => setHospital(e.target.value)}
              className="q-select"
              style={{ borderRadius: "0.8rem", padding: "0.65rem 0.9rem", fontSize: "0.875rem" }}
            >
              {HOSPITALS.map((h) => <option key={h}>{h}</option>)}
            </select>

            <Divider />

            <SectionLabel>ผู้ป่วย</SectionLabel>
            {demoPatients.length > 0 && (
              <div className="mb-2">
                <div
                  className="mb-1.5 inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[0.68rem] font-semibold"
                  style={{
                    background: "var(--surface-info)",
                    border: "1px solid var(--info-soft)",
                    color: "var(--info)",
                  }}
                >
                  🧪 CT-ICH dataset | {demoPatients.length} เคส
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {demoPatients.map((pid) => {
                    const active = ctMeta?.filename?.startsWith(pid) ?? false;
                    return (
                      <button
                        key={pid}
                        type="button"
                        disabled={demoLoading}
                        onClick={() => loadDemo(pid)}
                        className="rounded-full px-2.5 py-1 text-[0.72rem] font-semibold transition-all"
                        style={{
                          background: active ? "var(--accent)" : "var(--surface-2)",
                          color: active ? "white" : "var(--text-2)",
                          border: `1px solid ${active ? "var(--accent)" : "var(--border)"}`,
                          fontFamily: "var(--font-mono-stack)",
                        }}
                      >
                        P{pid}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {ctMeta && (
              <div
                className="rounded-[0.85rem] border px-2.5 py-2 text-xs"
                style={{ background: "var(--success-light)", borderColor: "var(--success-soft)" }}
              >
                <div className="font-semibold" style={{ color: "var(--success)" }}>✅ โหลด CT แล้ว</div>
                <div
                  className="mt-0.5 truncate"
                  style={{ color: "var(--text-2)", fontFamily: "var(--font-mono-stack)" }}
                >
                  {ctMeta.filename} | {ctMeta.slice_count} สไลซ์
                </div>
              </div>
            )}

            <Divider />

            <SectionLabel>โมเดล AI</SectionLabel>
            {(["baseline", "hybrid"] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setModelType(m)}
                className="mb-[0.4rem] flex w-full items-center gap-2.5 rounded-[0.85rem] border px-3 py-2.5 text-left text-sm font-medium transition-all"
                style={{
                  background: modelType === m
                    ? "linear-gradient(180deg, rgba(255,240,247,0.98), rgba(255,233,242,0.94))"
                    : "rgba(255,255,255,0.7)",
                  borderColor: modelType === m ? "var(--accent-soft)" : "var(--border)",
                  color: modelType === m ? "var(--accent)" : "var(--text-2)",
                  boxShadow: modelType === m ? "0 8px 20px rgba(194,91,134,0.10)" : "none",
                }}
              >
                <span
                  className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-sm"
                  style={{
                    background: modelType === m ? "var(--accent)" : "var(--surface-2)",
                    color: modelType === m ? "white" : "var(--text-2)",
                  }}
                >
                  {m === "hybrid" ? "⬡" : "◆"}
                </span>
                <div className="min-w-0">
                  <div className="text-sm font-semibold">
                    {m === "hybrid" ? "Q-Sentinel Hybrid" : "CNN Baseline"}
                  </div>
                  <div className="text-[0.7rem]" style={{ color: "var(--text-3)" }}>
                    {m === "hybrid" ? "เสริมด้วย VQC" : "โมเดลอ้างอิง"}
                  </div>
                </div>
              </button>
            ))}

            <Divider />

            <SectionLabel>โหมดวิเคราะห์</SectionLabel>
            <div className="mb-1 flex gap-2">
              {([true, false] as const).map((v) => (
                <button
                  key={String(v)}
                  type="button"
                  onClick={() => setAutoTriage(v)}
                  className="flex-1 rounded-[0.75rem] border py-2 text-xs font-semibold transition-all"
                  style={{
                    background: autoTriage === v ? "var(--accent-light)" : "var(--surface-2)",
                    borderColor: autoTriage === v ? "var(--accent-soft)" : "var(--border)",
                    color: autoTriage === v ? "var(--accent)" : "var(--text-3)",
                  }}
                >
                  {v ? "🚑 อัตโนมัติ" : "🎯 กำหนดเอง"}
                </button>
              ))}
            </div>

            <Divider />

            <SectionLabel>Threshold</SectionLabel>
            <div className="q-sb-row">
              <span>เกณฑ์ตัดสิน</span>
              <span className="q-sb-value" style={{ color: "var(--accent)" }}>
                {threshold.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min={1}
              max={50}
              value={Math.round(threshold * 100)}
              onChange={(e) => setThreshold(Number(e.target.value) / 100)}
              className="w-full"
              style={{ accentColor: "var(--accent)" }}
            />
            <div className="mt-0.5 flex justify-between text-[0.65rem]" style={{ color: "var(--text-3)" }}>
              <span>ไว</span>
              <span>เฉพาะเจาะจง</span>
            </div>

            <Divider />

            <SectionLabel>อัปโหลด CT Scan</SectionLabel>
            <div
              {...getRootProps()}
              className="q-upload-row"
              data-active={isDragActive}
            >
              <input {...getInputProps()} />
              <span className="text-xl">📁</span>
              <div className="min-w-0">
                <div className="text-xs font-semibold" style={{ color: "var(--text-1)" }}>
                  {uploading ? "กำลังอัปโหลด..." : isDragActive ? "วางไฟล์ CT ที่นี่" : "NIfTI หรือ DICOM"}
                </div>
                <div className="text-[0.67rem]" style={{ color: "var(--text-3)" }}>
                  ลากและวางได้ | สูงสุด 200 MB
                </div>
              </div>
            </div>

            <Divider />

            <SectionLabel>ส่งออก</SectionLabel>
            <button
              type="button"
              onClick={handleExportPDF}
              disabled={!lastResult || pdfLoading}
              className="q-btn-secondary w-full py-2.5 text-xs font-semibold"
              style={{
                opacity: !lastResult || pdfLoading ? 0.5 : 1,
                cursor: !lastResult || pdfLoading ? "not-allowed" : "pointer",
              }}
            >
              {pdfLoading ? "กำลังสร้าง..." : "📄 ส่งออกรายงาน PDF"}
            </button>
            <button
              type="button"
              onClick={handleExportHL7}
              disabled={!lastResult || hl7Loading}
              className="q-btn-secondary w-full py-2.5 text-xs font-semibold"
              style={{
                opacity: !lastResult || hl7Loading ? 0.5 : 1,
                cursor: !lastResult || hl7Loading ? "not-allowed" : "pointer",
                marginTop: "0.4rem",
              }}
            >
              {hl7Loading ? "กำลังสร้าง..." : "🏥 ส่งออก HL7 FHIR R4"}
            </button>

            <div
              className="pt-3 text-center text-[0.67rem] leading-5"
              style={{ color: "var(--text-3)" }}
            >
              Q-Sentinel Mesh v1.0
              <br />
              CEDT Hackathon 2026
            </div>
          </>
        )}
      </aside>
    </>
  );
}
