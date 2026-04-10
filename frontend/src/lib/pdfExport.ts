/**
 * Q-Sentinel Mesh — PDF Report Export
 * Uses jsPDF + html2canvas for browser-side generation.
 * Mirrors the structure from dashboard/utils/pdf_export.py
 */
import type { HemorrhageProbabilities } from "@/types/api";

interface ReportData {
  hospital: string;
  modelType: string;
  topClass: string;
  confidence: number;
  sliceUsed: number;
  probabilities: HemorrhageProbabilities;
  ctImageSrc?: string;
  heatmapSrc?: string;
  filename?: string;
}

const ACCENT = "#c25b86";
const TEXT1  = "#412b34";
const TEXT2  = "#6d5360";
const TEXT3  = "#9c7f8c";
const BORDER = "#ecd9e2";
const BG     = "#fff8fb";

const SUBTYPE_LABELS: Record<string, string> = {
  any: "Any Hemorrhage",
  epidural: "Epidural",
  subdural: "Subdural",
  subarachnoid: "Subarachnoid",
  intraparenchymal: "Intraparenchymal",
  intraventricular: "Intraventricular",
};

const SUBTYPE_ORDER = ["any", "epidural", "subdural", "subarachnoid", "intraparenchymal", "intraventricular"];

export async function generateReportPDF(data: ReportData): Promise<void> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const jsPDFModule = await import("jspdf") as any;
  const jsPDF = jsPDFModule.jsPDF ?? jsPDFModule.default?.jsPDF ?? jsPDFModule.default;

  const doc = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
  const PW = 210; // page width mm
  const PH = 297; // page height mm
  const MARGIN = 18;
  const CONTENT_W = PW - 2 * MARGIN;

  // ── Helper functions ────────────────────────────────────────────────────────
  function line(x1: number, y: number, x2: number, color = BORDER) {
    doc.setDrawColor(color);
    doc.line(x1, y, x2, y);
  }

  function rect(x: number, y: number, w: number, h: number, fill: string, strokeColor?: string) {
    doc.setFillColor(fill);
    if (strokeColor) {
      doc.setDrawColor(strokeColor);
      doc.roundedRect(x, y, w, h, 2, 2, "FD");
    } else {
      doc.roundedRect(x, y, w, h, 2, 2, "F");
    }
  }

  function text(str: string, x: number, y: number, opts?: {
    size?: number; color?: string; bold?: boolean; align?: "left" | "center" | "right";
  }) {
    const { size = 10, color = TEXT1, bold = false, align = "left" } = opts ?? {};
    doc.setFontSize(size);
    doc.setTextColor(color);
    doc.setFont("helvetica", bold ? "bold" : "normal");
    doc.text(str, x, y, { align });
  }

  // ══════════════════════════════════════════════════════════════════════════
  // PAGE 1: Header + CT scan + Detection result
  // ══════════════════════════════════════════════════════════════════════════

  // Pink top bar
  doc.setFillColor(ACCENT);
  doc.rect(0, 0, PW, 14, "F");

  text("Q-Sentinel Mesh", MARGIN, 9.5, { size: 14, color: "#ffffff", bold: true });
  text("CT Hemorrhage Detection Report", PW - MARGIN, 9.5, { size: 9, color: "#fce8f0", align: "right" });

  let y = 22;

  // Report metadata
  const now = new Date();
  const dateStr = now.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
  const timeStr = now.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });

  rect(MARGIN, y, CONTENT_W, 22, BG, BORDER);
  text("Hospital", MARGIN + 4, y + 6, { size: 8, color: TEXT3 });
  text(data.hospital, MARGIN + 4, y + 12, { size: 10, bold: true });
  text("Model", MARGIN + 65, y + 6, { size: 8, color: TEXT3 });
  text(data.modelType === "hybrid" ? "Q-Sentinel Hybrid" : "CNN Baseline", MARGIN + 65, y + 12, { size: 10, bold: true });
  text("Generated", MARGIN + 130, y + 6, { size: 8, color: TEXT3 });
  text(`${dateStr} · ${timeStr}`, MARGIN + 130, y + 12, { size: 9 });
  y += 28;

  // Detection result banner
  const detected = data.probabilities.any >= 0.15;
  rect(MARGIN, y, CONTENT_W, 18, detected ? "#fde7ef" : "#eef9f1", detected ? "#f1c7d8" : "#b7dec6");
  text(
    detected ? `⚠ HEMORRHAGE DETECTED: ${data.topClass.toUpperCase()}` : "✓ NO HEMORRHAGE DETECTED",
    MARGIN + 4, y + 7,
    { size: 11, bold: true, color: detected ? ACCENT : "#4c8f6b" }
  );
  text(
    `Confidence: ${(data.confidence * 100).toFixed(1)}%  ·  Slice: ${data.sliceUsed + 1}  ·  ${data.filename ?? "CT Upload"}`,
    MARGIN + 4, y + 14,
    { size: 8, color: TEXT2 }
  );
  y += 24;

  // CT images side by side
  const hasHeatmap = !!(data.heatmapSrc && data.heatmapSrc.length > 20);
  const imgW = hasHeatmap ? (CONTENT_W - 4) / 2 : CONTENT_W;
  const imgH = imgW * 0.85;

  text("CT Scan — Brain Window", MARGIN, y + 4, { size: 9, color: TEXT3, bold: true });
  if (hasHeatmap) text("Grad-CAM Heatmap", MARGIN + imgW + 4 + 2, y + 4, { size: 9, color: TEXT3, bold: true });
  y += 7;

  if (data.ctImageSrc && data.ctImageSrc.length > 20) {
    try {
      doc.addImage(data.ctImageSrc, "PNG", MARGIN, y, imgW, imgH);
      // Draw border only (no fill over image)
      doc.setDrawColor(BORDER);
      doc.rect(MARGIN, y, imgW, imgH, "S");
    } catch {/* skip if image fails */}
  } else {
    rect(MARGIN, y, imgW, imgH, "#f5f5f5", BORDER);
    text("CT image not available", MARGIN + imgW / 2, y + imgH / 2, { size: 8, color: TEXT3, align: "center" });
  }

  if (hasHeatmap) {
    const hx = MARGIN + imgW + 4;
    try {
      doc.addImage(data.heatmapSrc!, "PNG", hx, y, imgW, imgH);
      doc.setDrawColor(BORDER);
      doc.rect(hx, y, imgW, imgH, "S");
    } catch {/* skip */}
  }

  y += imgH + 8;

  // ══════════════════════════════════════════════════════════════════════════
  // PAGE 1 (continued): Probability table
  // ══════════════════════════════════════════════════════════════════════════

  if (y + 60 > PH - 20) { doc.addPage(); y = 22; }

  text("Detection Probabilities", MARGIN, y, { size: 11, bold: true });
  line(MARGIN, y + 2, PW - MARGIN);
  y += 8;

  for (const key of SUBTYPE_ORDER) {
    const prob = data.probabilities[key as keyof HemorrhageProbabilities] ?? 0;
    const pct = prob * 100;
    const isPos = pct >= 15;
    const barColor = isPos ? ACCENT : "#d0bfc9";
    const barW = (CONTENT_W - 70) * Math.min(pct / 100, 1);

    text(SUBTYPE_LABELS[key] ?? key, MARGIN, y + 4.5, { size: 9, color: isPos ? ACCENT : TEXT2, bold: isPos });

    // Track bar
    rect(MARGIN + 52, y, CONTENT_W - 70, 5, "#fff3f7", BORDER);
    if (barW > 0) {
      doc.setFillColor(barColor);
      doc.roundedRect(MARGIN + 52, y, barW, 5, 1, 1, "F");
    }

    text(`${pct.toFixed(1)}%`, PW - MARGIN - 2, y + 4.5, { size: 9, color: isPos ? ACCENT : TEXT3, bold: isPos, align: "right" });
    text(isPos ? "POSITIVE" : "—", PW - MARGIN - 18, y + 4.5, { size: 7, color: isPos ? ACCENT : TEXT3, align: "right" });
    y += 9;
  }

  // ══════════════════════════════════════════════════════════════════════════
  // Footer
  // ══════════════════════════════════════════════════════════════════════════
  const footerY = PH - 12;
  line(MARGIN, footerY - 4, PW - MARGIN, "#dfbfcd");
  text("Q-Sentinel Mesh · CEDT Hackathon 2026 · Prototype — Not for Clinical Use", PW / 2, footerY, {
    size: 7, color: TEXT3, align: "center",
  });

  // Save
  const safeHospital = data.hospital.replace(/[^a-zA-Z0-9]/g, "_").slice(0, 20);
  doc.save(`qsentinel_report_${safeHospital}_${Date.now()}.pdf`);
}
