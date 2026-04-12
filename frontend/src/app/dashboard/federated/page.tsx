"use client";

import { useEffect, useRef, useState } from "react";
import BenchmarkChart from "@/components/federated/BenchmarkChart";
import FederatedRoundsChart from "@/components/federated/FederatedRoundsChart";
import HospitalBreakdownChart from "@/components/federated/HospitalBreakdownChart";
import HospitalNodeCard from "@/components/federated/HospitalNodeCard";
import { useBenchmark } from "@/hooks/useBenchmark";
import { useFedRounds } from "@/hooks/useFedRounds";

const HOSPITAL_NAMES = [
  "Hospital A (Bangkok)",
  "Hospital B (Chiang Mai)",
  "Hospital C (Khon Kaen)",
];

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
    <article className="q-soft-panel rounded-[1.25rem] px-4 py-4">
      <div className="q-eyebrow mb-1">{label}</div>
      <div className="text-[1.6rem] font-bold leading-none" style={{ color: valueColor ?? "var(--text-1)", fontFamily: "var(--font-mono)" }}>
        {value}
      </div>
      <p className="mt-2 text-xs leading-5" style={{ color: "var(--text-2)" }}>
        {note}
      </p>
    </article>
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
        {description ? (
          <p className="mt-1 text-sm leading-6" style={{ color: "var(--text-2)" }}>
            {description}
          </p>
        ) : null}
      </div>
      {children}
    </section>
  );
}

export default function FederatedPage() {
  const { data: benchmark, loading: benchmarkLoading } = useBenchmark();
  const { data: rounds, loading: roundsLoading } = useFedRounds();
  const firstRound = rounds[0];
  const lastRound = rounds[rounds.length - 1];

  const baseline = benchmark?.metadata.baseline_best_auc ?? null;
  const hybrid = benchmark?.metadata.hybrid_best_auc ?? null;
  const federated = benchmark?.metadata.fed_final_auc ?? lastRound?.global_auc ?? null;
  const netLift = baseline != null && federated != null ? (federated - baseline) * 100 : null;

  const [animValue, setAnimValue] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  function animateTraining() {
    if (!baseline || !federated || timerRef.current) return;
    const start = baseline * 100;
    const end = federated * 100;
    const frames = 36;
    let index = 0;
    setAnimValue(`${start.toFixed(1)}%`);
    timerRef.current = setInterval(() => {
      index += 1;
      const next = start + ((end - start) * index) / frames;
      setAnimValue(`${next.toFixed(1)}%`);
      if (index >= frames && timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }, 45);
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <SummaryCard label="Baseline AUC" value={baseline ? `${(baseline * 100).toFixed(1)}%` : "-"} note="ผลอ้างอิงแบบ single-site ก่อนทำ federation" valueColor="var(--chart-baseline)" />
        <SummaryCard label="Hybrid AUC" value={hybrid ? `${(hybrid * 100).toFixed(1)}%` : "-"} note="ผลของ Q-Sentinel ก่อน aggregate ข้าม site" valueColor="var(--accent)" />
        <SummaryCard label="Federated AUC" value={animValue ?? (federated ? `${(federated * 100).toFixed(1)}%` : "-")} note="ผลของ global model หลังการกระจายรอบล่าสุด" valueColor="var(--success)" />
        <SummaryCard label="Net Lift" value={netLift != null ? `+${netLift.toFixed(1)}%` : "-"} note="การยกระดับเมื่อเทียบกับ baseline เดิม" valueColor="var(--info)" />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(320px,0.75fr)]">
        <Panel eyebrow="Performance Story" title="ภาพรวมผลลัพธ์">
          {benchmarkLoading ? (
            <div className="py-12 text-center text-sm" style={{ color: "var(--text-3)" }}>
              กำลังโหลด benchmark data...
            </div>
          ) : benchmark ? (
            <BenchmarkChart data={benchmark} />
          ) : (
            <div className="py-12 text-center text-sm" style={{ color: "var(--text-3)" }}>
              ยังไม่มี benchmark data
            </div>
          )}
        </Panel>

        <Panel eyebrow="Quick Read" title="ประเด็นสำคัญ">
          <div>
            <div className="q-stat-row"><span style={{ color: "var(--text-3)" }}>Topology</span><span className="q-value">3 hospitals</span></div>
            <div className="q-stat-row"><span style={{ color: "var(--text-3)" }}>Algorithm</span><span className="q-value" style={{ color: "var(--accent)" }}>FedAvg</span></div>
            <div className="q-stat-row"><span style={{ color: "var(--text-3)" }}>AUC รอบแรก</span><span className="q-value">{firstRound ? `${(firstRound.global_auc * 100).toFixed(1)}%` : "-"}</span></div>
            <div className="q-stat-row"><span style={{ color: "var(--text-3)" }}>AUC รอบล่าสุด</span><span className="q-value" style={{ color: "var(--success)" }}>{lastRound ? `${(lastRound.global_auc * 100).toFixed(1)}%` : "-"}</span></div>
            <div className="q-stat-row"><span style={{ color: "var(--text-3)" }}>Privacy posture</span><span className="q-value" style={{ color: "var(--success)" }}>Preserved</span></div>
          </div>

          <button
            type="button"
            onClick={animateTraining}
            className="q-btn-primary mt-4 w-full px-4 py-3 text-sm"
            style={{ opacity: !baseline || !federated ? 0.55 : 1, cursor: !baseline || !federated ? "not-allowed" : "pointer" }}
          >
            แสดงการยกระดับระหว่างการเทรน
          </button>
        </Panel>
      </div>

      <Panel eyebrow="Training Trace" title="ความคืบหน้าแต่ละรอบ">
        {roundsLoading ? (
          <div className="py-12 text-center text-sm" style={{ color: "var(--text-3)" }}>
            กำลังโหลดรอบการเทรน...
          </div>
        ) : rounds.length ? (
          <>
            <FederatedRoundsChart rounds={rounds} />
            <div className="mt-5">
              <div className="q-eyebrow mb-3">ผลงานของแต่ละโรงพยาบาล</div>
              <HospitalBreakdownChart rounds={rounds} />
            </div>
          </>
        ) : (
          <div className="py-12 text-center text-sm" style={{ color: "var(--text-3)" }}>
            ยังไม่มีข้อมูลรอบ federated ในระบบ
          </div>
        )}
      </Panel>

      <section>
        <div className="mb-3 flex items-center justify-between gap-3">
          <div>
            <div className="q-eyebrow mb-1">สถานะเครือข่าย</div>
            <h3 className="text-lg font-semibold" style={{ color: "var(--text-1)" }}>
              โหนดโรงพยาบาล
            </h3>
          </div>
          <span className="q-pill">ส่งเฉพาะ model update ที่เข้ารหัสแล้ว</span>
        </div>
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
          {HOSPITAL_NAMES.map((name) => (
            <HospitalNodeCard key={name} name={name} rounds={rounds} />
          ))}
        </div>
      </section>
    </div>
  );
}
