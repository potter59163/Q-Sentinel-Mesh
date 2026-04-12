"use client";

// PACS Integration Roadmap — People + Process + Technology strategy

const ROADMAP_PHASES = [
  {
    phase: "Phase 1",
    title: "HL7 FHIR R4 Adapter",
    status: "live" as const,
    timeline: "Q2 2026",
    items: [
      "DiagnosticReport resource with LOINC / SNOMED coding",
      "AI confidence score as FHIR extension",
      "Radiologist verdict embedded in report",
      "PQC-encryption flag for audit trail",
      "One-click export from dashboard (JSON download)",
    ],
    icon: "📋",
  },
  {
    phase: "Phase 2",
    title: "DICOM SR + DICOMweb Push",
    status: "planned" as const,
    timeline: "Q3 2026",
    items: [
      "Structured Report (SR) generated alongside FHIR",
      "Push to hospital PACS via DICOMweb STOW-RS",
      "Heatmap overlay stored as DICOM Secondary Capture",
      "Worklist integration (MWL) for auto-population",
      "Tested with Orthanc (open-source PACS)",
    ],
    icon: "🖥",
  },
  {
    phase: "Phase 3",
    title: "HIS / EMR Bi-directional Sync",
    status: "planned" as const,
    timeline: "Q4 2026",
    items: [
      "HL7 v2.x ADT feed for patient demographic sync",
      "CDA (Clinical Document Architecture) report push to HIS",
      "Order-placer → fulfiller workflow (ORM/ORU messaging)",
      "IHE RAD-28 (RWF) for radiologist workflow queue",
      "Thai hospital HIS compatibility: HosXP, HIMS, InHospital",
    ],
    icon: "🔄",
  },
  {
    phase: "Phase 4",
    title: "PDPA & HIPAA Compliance Layer",
    status: "planned" as const,
    timeline: "Q1 2027",
    items: [
      "Patient consent management (FHIR Consent resource)",
      "De-identification pipeline for federated training data",
      "Audit log export (FHIR AuditEvent) for PDPA DPA reporting",
      "Role-based access control tied to hospital node identity",
      "Data retention policy enforcement (S3 lifecycle rules)",
    ],
    icon: "🔒",
  },
];

const SYSTEM_MATRIX = [
  ["Hospital System", "Protocol", "Status", "Notes"],
  ["Orthanc (Open Source)", "DICOMweb / HL7 FHIR", "Tested", "Reference integration"],
  ["HosXP (Thai)", "HL7 v2.x", "Planned Q3", "Most common Thai HIS"],
  ["HIMS / InHospital", "HL7 FHIR R4", "Planned Q3", "Government hospital stack"],
  ["Sectra PACS", "DICOM + HL7", "Planned Q4", "University hospital"],
  ["Epic (large centres)", "SMART on FHIR", "Roadmap", "Private hospital group"],
];

const PEOPLE_ITEMS = [
  {
    title: "Radiologist in the Loop",
    icon: "👨‍⚕️",
    points: [
      "Confirm / Reject / Correct AI verdict with one click",
      "All verdicts stored and fed back to federated training",
      "Accuracy rate tracked in Feedback Stats",
      "Prevents automation bias — radiologist remains accountable",
    ],
  },
  {
    title: "Training & Change Management",
    icon: "📚",
    points: [
      "On-site training session for radiology staff",
      "\"AI as second reader\" framing, not replacement",
      "Clear escalation path: low confidence → senior radiologist",
      "Monthly accuracy review meetings with hospital IT",
    ],
  },
];

const PROCESS_ITEMS = [
  {
    title: "Clinical Workflow Integration",
    icon: "🔁",
    points: [
      "AI triage runs in background while radiologist loads worklist",
      "High-confidence positives flagged at top of queue (auto-triage)",
      "FHIR report auto-attached to study in PACS on confirm",
      "Negative scans still reviewed — AI supplements, not replaces",
    ],
  },
  {
    title: "Governance & Audit",
    icon: "📊",
    points: [
      "Every AI prediction + radiologist verdict logged (immutable)",
      "Monthly aggregate accuracy report exported as FHIR Bundle",
      "PDPA Data Processing Agreement signed with each hospital",
      "Medical device registration pathway (TFDA class II)",
    ],
  },
];

function StatusBadge({ status }: { status: "live" | "planned" }) {
  return (
    <span
      className="q-pill text-[0.68rem]"
      style={
        status === "live"
          ? { background: "var(--success-light)", color: "var(--success)", border: "1px solid var(--success-soft)" }
          : { background: "var(--surface-2)", color: "var(--text-3)", border: "1px solid var(--border)" }
      }
    >
      {status === "live" ? "● Live" : "○ Planned"}
    </span>
  );
}

function Panel({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="q-card rounded-[1.4rem] p-5">
      <div className="mb-4">
        <div className="q-eyebrow mb-1">{eyebrow}</div>
        <h3 className="text-lg font-semibold" style={{ color: "var(--text-1)" }}>
          {title}
        </h3>
        {description && (
          <p className="mt-1 text-sm leading-6" style={{ color: "var(--text-2)" }}>
            {description}
          </p>
        )}
      </div>
      {children}
    </section>
  );
}

export default function PacsPage() {
  return (
    <div className="q-dashboard-stack">
      {/* Intro */}
      <section className="q-dashboard-intro">
        <div className="q-dashboard-intro-row">
          <div className="q-dashboard-intro-copy">
            <div className="q-eyebrow mb-1">Hospital Integration Roadmap</div>
            <div className="q-dashboard-intro-title">PACS · HIS · HL7 FHIR</div>
            <p className="q-dashboard-intro-text">
              Q-Sentinel Mesh is designed to slot into existing hospital workflows — not replace them.
              This tab outlines the People, Process, and Technology strategy for real-world clinical deployment.
            </p>
          </div>
          <div className="q-kicker-row">
            <span className="q-pill q-pill-success">HL7 FHIR R4 · Live</span>
            <span className="q-pill">DICOM SR · Planned</span>
            <span className="q-pill q-pill-accent">PDPA Aligned</span>
          </div>
        </div>
      </section>

      {/* People + Process */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Panel
          eyebrow="People"
          title="Human-in-the-Loop"
          description="Clinical AI succeeds when doctors trust it. These mechanisms keep radiologists in control."
        >
          <div className="flex flex-col gap-4">
            {PEOPLE_ITEMS.map((item) => (
              <div key={item.title}>
                <div className="mb-2 flex items-center gap-2">
                  <span className="text-lg">{item.icon}</span>
                  <span className="text-sm font-semibold" style={{ color: "var(--text-1)" }}>
                    {item.title}
                  </span>
                </div>
                <ul className="space-y-1">
                  {item.points.map((p) => (
                    <li key={p} className="flex items-start gap-2 text-xs leading-5" style={{ color: "var(--text-2)" }}>
                      <span className="mt-0.5 shrink-0" style={{ color: "var(--accent)" }}>·</span>
                      {p}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </Panel>

        <Panel
          eyebrow="Process"
          title="Clinical Workflow & Governance"
          description="Standards-based integration ensures AI findings reach the right people at the right time."
        >
          <div className="flex flex-col gap-4">
            {PROCESS_ITEMS.map((item) => (
              <div key={item.title}>
                <div className="mb-2 flex items-center gap-2">
                  <span className="text-lg">{item.icon}</span>
                  <span className="text-sm font-semibold" style={{ color: "var(--text-1)" }}>
                    {item.title}
                  </span>
                </div>
                <ul className="space-y-1">
                  {item.points.map((p) => (
                    <li key={p} className="flex items-start gap-2 text-xs leading-5" style={{ color: "var(--text-2)" }}>
                      <span className="mt-0.5 shrink-0" style={{ color: "var(--accent)" }}>·</span>
                      {p}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      {/* Technology — Integration Roadmap phases */}
      <Panel
        eyebrow="Technology"
        title="Integration Roadmap"
        description="A phased approach to full PACS / HIS integration, starting with standards-based FHIR export already live in this build."
      >
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {ROADMAP_PHASES.map((phase) => (
            <div
              key={phase.phase}
              className="rounded-[1.1rem] border p-4"
              style={{ background: "var(--surface-2)", borderColor: phase.status === "live" ? "var(--success-soft)" : "var(--border)" }}
            >
              <div className="mb-2 flex items-center justify-between gap-2">
                <span className="text-xl">{phase.icon}</span>
                <StatusBadge status={phase.status} />
              </div>
              <div className="text-[0.68rem] font-bold uppercase tracking-widest" style={{ color: "var(--text-3)" }}>
                {phase.phase} · {phase.timeline}
              </div>
              <div className="mt-1 text-sm font-semibold" style={{ color: "var(--text-1)" }}>
                {phase.title}
              </div>
              <ul className="mt-3 space-y-1.5">
                {phase.items.map((item) => (
                  <li key={item} className="flex items-start gap-2 text-[0.73rem] leading-5" style={{ color: "var(--text-2)" }}>
                    <span
                      className="mt-0.5 shrink-0"
                      style={{ color: phase.status === "live" ? "var(--success)" : "var(--text-3)" }}
                    >
                      {phase.status === "live" ? "✓" : "○"}
                    </span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </Panel>

      {/* System compatibility matrix */}
      <Panel
        eyebrow="Technology"
        title="Hospital System Compatibility Matrix"
        description="Target systems for Thai hospital deployment — covering public, university, and private networks."
      >
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                {SYSTEM_MATRIX[0].map((h) => (
                  <th
                    key={h}
                    className="pb-2 pr-4 text-left font-semibold"
                    style={{ color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.05em", fontSize: "0.65rem" }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {SYSTEM_MATRIX.slice(1).map((row, i) => (
                <tr key={i} style={{ borderBottom: "1px solid var(--border-light)" }}>
                  {row.map((cell, j) => (
                    <td
                      key={j}
                      className="py-2.5 pr-4"
                      style={{
                        color: j === 0 ? "var(--text-1)" : j === 2 && cell === "Tested" ? "var(--success)" : "var(--text-2)",
                        fontWeight: j === 0 ? 600 : 400,
                      }}
                    >
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* Architecture note */}
      <Panel
        eyebrow="Technology"
        title="Current Architecture"
        description="How Q-Sentinel Mesh sits alongside existing hospital infrastructure."
      >
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {[
            {
              title: "CT Acquisition",
              icon: "📡",
              desc: "CT scanner → DICOM → hospital PACS (unchanged). Q-Sentinel reads a copy — never touches the primary PACS.",
            },
            {
              title: "AI Processing",
              icon: "🧠",
              desc: "DICOM / NIfTI uploaded to Q-Sentinel. EfficientNet-B4 + VQC runs inference on-site or in Thai-region AWS Fargate.",
            },
            {
              title: "Report Delivery",
              icon: "📋",
              desc: "FHIR R4 DiagnosticReport (live) or DICOM SR (Phase 2) pushed back to PACS / HIS with radiologist verdict attached.",
            },
          ].map((card) => (
            <div
              key={card.title}
              className="rounded-[1rem] border p-4 text-center"
              style={{ background: "var(--surface)", borderColor: "var(--border)" }}
            >
              <div className="mb-2 text-3xl">{card.icon}</div>
              <div className="mb-1 text-sm font-semibold" style={{ color: "var(--text-1)" }}>
                {card.title}
              </div>
              <p className="text-xs leading-5" style={{ color: "var(--text-2)" }}>
                {card.desc}
              </p>
            </div>
          ))}
        </div>
        <div
          className="mt-4 rounded-[0.85rem] border px-4 py-3 text-xs leading-6"
          style={{ background: "var(--surface-info)", borderColor: "var(--info-soft)", color: "var(--text-2)" }}
        >
          <span className="font-semibold" style={{ color: "var(--info)" }}>Design principle: </span>
          Q-Sentinel operates as a read-only AI assistant. It never modifies the primary PACS, never stores raw patient images beyond the session, and all federated model updates are encrypted with ML-KEM-512 (NIST FIPS 203) before leaving the hospital network.
        </div>
      </Panel>
    </div>
  );
}
