"use client";

const ROADMAP_PHASES = [
  {
    phase: "Phase 1",
    title: "HL7 FHIR R4 Adapter",
    status: "live" as const,
    timeline: "Q2 2026",
    items: [
      "สร้าง DiagnosticReport พร้อม LOINC / SNOMED coding",
      "ส่งคะแนนความมั่นใจของ AI เป็น FHIR extension",
      "ฝัง verdict ของรังสีแพทย์ไว้ในรายงาน",
      "ติดธง PQC-encryption เพื่อใช้ใน audit trail",
      "ส่งออกจาก dashboard ได้ในคลิกเดียว (JSON download)",
    ],
    icon: "📋",
  },
  {
    phase: "Phase 2",
    title: "DICOM SR + DICOMweb Push",
    status: "planned" as const,
    timeline: "Q3 2026",
    items: [
      "สร้าง Structured Report (SR) ควบคู่กับ FHIR",
      "ส่งกลับเข้า PACS ผ่าน DICOMweb STOW-RS",
      "เก็บ heatmap overlay เป็น DICOM Secondary Capture",
      "เชื่อม Worklist (MWL) สำหรับเติมข้อมูลอัตโนมัติ",
      "ทดสอบร่วมกับ Orthanc (open-source PACS)",
    ],
    icon: "🖥",
  },
  {
    phase: "Phase 3",
    title: "HIS / EMR Bi-directional Sync",
    status: "planned" as const,
    timeline: "Q4 2026",
    items: [
      "รับ HL7 v2.x ADT feed เพื่อ sync ข้อมูลผู้ป่วย",
      "ส่งรายงาน CDA (Clinical Document Architecture) กลับเข้า HIS",
      "รองรับ order-placer → fulfiller workflow (ORM/ORU messaging)",
      "รองรับ IHE RAD-28 (RWF) สำหรับคิวงานรังสีแพทย์",
      "รองรับ Thai hospital HIS เช่น HosXP, HIMS, InHospital",
    ],
    icon: "🔄",
  },
  {
    phase: "Phase 4",
    title: "PDPA & HIPAA Compliance Layer",
    status: "planned" as const,
    timeline: "Q1 2027",
    items: [
      "จัดการ patient consent ผ่าน FHIR Consent resource",
      "ทำ de-identification pipeline สำหรับข้อมูลเทรนแบบ federated",
      "ส่งออก audit log เป็น FHIR AuditEvent สำหรับ PDPA reporting",
      "ทำ role-based access control ผูกกับตัวตนของแต่ละ hospital node",
      "บังคับใช้นโยบาย data retention ผ่าน S3 lifecycle rules",
    ],
    icon: "🔒",
  },
];

const SYSTEM_MATRIX = [
  ["ระบบโรงพยาบาล", "โปรโตคอล", "สถานะ", "หมายเหตุ"],
  ["Orthanc (Open Source)", "DICOMweb / HL7 FHIR", "ทดสอบแล้ว", "ระบบอ้างอิงสำหรับ integration"],
  ["HosXP (Thai)", "HL7 v2.x", "ตามแผน Q3", "HIS ที่พบได้บ่อยในไทย"],
  ["HIMS / InHospital", "HL7 FHIR R4", "ตามแผน Q3", "สแตกของโรงพยาบาลภาครัฐ"],
  ["Sectra PACS", "DICOM + HL7", "ตามแผน Q4", "โรงพยาบาลมหาวิทยาลัย"],
  ["Epic (large centres)", "SMART on FHIR", "อยู่ใน roadmap", "เครือโรงพยาบาลเอกชน"],
];

const PEOPLE_ITEMS = [
  {
    title: "รังสีแพทย์ในลูป",
    icon: "👨‍⚕️",
    points: [
      "กดยืนยัน ไม่เห็นด้วย หรือแก้ผลของ AI ได้ในคลิกเดียว",
      "ทุกความเห็นถูกเก็บและป้อนกลับสู่ federated training",
      "ติดตาม accuracy rate ได้จากสถิติ feedback",
      "ลด automation bias โดยให้รังสีแพทย์ยังเป็นผู้รับผิดชอบหลัก",
    ],
  },
  {
    title: "การอบรมและการเปลี่ยนผ่าน",
    icon: "📚",
    points: [
      "มี session อบรมหน้างานสำหรับทีมรังสี",
      "สื่อสารว่า AI เป็น second reader ไม่ใช่ตัวแทนแพทย์",
      "มีเส้นทางส่งต่อชัดเจนเมื่อคะแนนความมั่นใจต่ำ",
      "ทบทวน accuracy รายเดือนร่วมกับทีม IT โรงพยาบาล",
    ],
  },
];

const PROCESS_ITEMS = [
  {
    title: "การเชื่อมเข้ากับ Clinical Workflow",
    icon: "🔁",
    points: [
      "AI triage ทำงานเบื้องหลังระหว่างที่รังสีแพทย์เปิด worklist",
      "เคส positive ที่คะแนนความมั่นใจสูงถูกดันขึ้นต้นคิว",
      "FHIR report ถูกแนบกลับไปยังการศึกษาใน PACS เมื่อมีการยืนยันผล",
      "เคส negative ยังต้องมีการทบทวนเสมอ AI เป็นผู้ช่วย ไม่ใช่ผู้แทน",
    ],
  },
  {
    title: "Governance & Audit",
    icon: "📊",
    points: [
      "ทุก prediction และ verdict ถูกบันทึกแบบ immutable",
      "ส่งออกรายงาน accuracy รายเดือนเป็น FHIR Bundle ได้",
      "มี Data Processing Agreement ตาม PDPA กับแต่ละโรงพยาบาล",
      "วางแนวทางขึ้นทะเบียนเครื่องมือแพทย์กับ TFDA class II",
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
      {status === "live" ? "● ใช้งานแล้ว" : "○ ตามแผน"}
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
      <section className="q-dashboard-intro">
        <div className="q-dashboard-intro-row">
          <div className="q-dashboard-intro-copy">
            <div className="q-eyebrow mb-1">เส้นทางเชื่อมต่อกับโรงพยาบาล</div>
            <div className="q-dashboard-intro-title">PACS · HIS · HL7 FHIR</div>
            <p className="q-dashboard-intro-text">
              Q-Sentinel Mesh ถูกออกแบบให้แทรกตัวใน workflow เดิมของโรงพยาบาล ไม่ใช่เข้าไปแทนที่ระบบหลัก
              หน้านี้สรุปแนวทางด้าน People, Process และ Technology สำหรับการใช้งานจริง
            </p>
          </div>
          <div className="q-kicker-row">
            <span className="q-pill q-pill-success">HL7 FHIR R4 · ใช้งานแล้ว</span>
            <span className="q-pill">DICOM SR · ตามแผน</span>
            <span className="q-pill q-pill-accent">สอดคล้อง PDPA</span>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Panel
          eyebrow="People"
          title="Human-in-the-Loop"
          description="Clinical AI จะถูกใช้งานได้จริงก็ต่อเมื่อแพทย์เชื่อใจและยังคงควบคุมการตัดสินใจได้"
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
          description="การเชื่อมต่อแบบอิงมาตรฐานช่วยให้ผลจาก AI ไปถึงคนที่ควรเห็นในเวลาที่เหมาะสม"
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

      <Panel
        eyebrow="Technology"
        title="Roadmap การเชื่อมต่อ"
        description="วางแผนเชื่อม PACS / HIS แบบเป็นระยะ เริ่มจาก FHIR export ที่ใช้งานได้แล้วใน build นี้"
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

      <Panel
        eyebrow="Technology"
        title="ตารางความเข้ากันได้ของระบบ"
        description="ระบบเป้าหมายสำหรับการใช้งานในโรงพยาบาลไทย ทั้งภาครัฐ มหาวิทยาลัย และเอกชน"
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
                        color: j === 0 ? "var(--text-1)" : j === 2 && cell === "ทดสอบแล้ว" ? "var(--success)" : "var(--text-2)",
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

      <Panel
        eyebrow="Technology"
        title="สถาปัตยกรรมปัจจุบัน"
        description="Q-Sentinel Mesh วางตัวควบคู่กับโครงสร้างระบบเดิมของโรงพยาบาลอย่างไร"
      >
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {[
            {
              title: "การรับภาพ CT",
              icon: "📡",
              desc: "CT scanner → DICOM → hospital PACS ยังคงทำงานเหมือนเดิม Q-Sentinel อ่านจากสำเนาเท่านั้น ไม่แตะ primary PACS",
            },
            {
              title: "การประมวลผล AI",
              icon: "🧠",
              desc: "DICOM / NIfTI ถูกส่งเข้า Q-Sentinel แล้วรัน EfficientNet-B4 + VQC แบบ on-site หรือบน AWS Fargate ใน region ไทย",
            },
            {
              title: "การส่งรายงาน",
              icon: "📋",
              desc: "ส่ง FHIR R4 DiagnosticReport กลับเข้า PACS / HIS ได้แล้ว และมีแผนต่อยอด DICOM SR ใน Phase 2",
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
          <span className="font-semibold" style={{ color: "var(--info)" }}>หลักการออกแบบ: </span>
          Q-Sentinel ทำหน้าที่เป็น read-only AI assistant ไม่แก้ไข primary PACS ไม่เก็บภาพดิบของผู้ป่วยเกินกว่า session และ model update ทุกชุดจะถูกเข้ารหัสด้วย ML-KEM-512 (NIST FIPS 203) ก่อนออกจากเครือข่ายโรงพยาบาล
        </div>
      </Panel>
    </div>
  );
}
