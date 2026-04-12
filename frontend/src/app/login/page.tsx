"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { toast } from "sonner";
import api from "@/lib/api";
import { ROLE_CONFIG, setAuth, type UserRole } from "@/lib/auth";

const ROLES = (Object.entries(ROLE_CONFIG) as [UserRole, (typeof ROLE_CONFIG)[UserRole]][])
  .filter(([k]) => k !== "dev");

const ROLE_BADGE_STYLE: Record<UserRole, React.CSSProperties> = {
  radiologist:       { background: "rgba(194,91,134,0.10)", borderColor: "rgba(194,91,134,0.25)", color: "#c25b86" },
  hospital_operator: { background: "rgba(59,130,246,0.10)",  borderColor: "rgba(59,130,246,0.25)",  color: "#2563eb" },
  fed_ai_admin:      { background: "rgba(76,143,107,0.10)",  borderColor: "rgba(76,143,107,0.25)",  color: "#4c8f6b" },
  hospital_it:       { background: "rgba(124,58,237,0.10)",  borderColor: "rgba(124,58,237,0.25)",  color: "#7c3aed" },
  dev:               { background: "rgba(245,158,11,0.12)",  borderColor: "rgba(245,158,11,0.30)",  color: "#f59e0b" },
};

function LoginContent() {
  const router = useRouter();
  const params = useSearchParams();
  const [loading, setLoading] = useState<UserRole | null>(null);
  const [devClickCount, setDevClickCount] = useState(0);
  const [devUnlocked, setDevUnlocked] = useState(false);

  async function handleSelect(role: UserRole) {
    setLoading(role);
    try {
      const res = await api.post<{ access_token: string; role: UserRole }>(
        "/api/auth/login",
        { role },
      );
      setAuth(res.data.access_token);
      toast.success(`เข้าสู่ระบบในบทบาท ${ROLE_CONFIG[res.data.role].label}`);
      const from = params.get("from");
      const dest = from && from.startsWith("/dashboard")
        ? from
        : ROLE_CONFIG[res.data.role].defaultPath;
      router.push(dest);
    } catch {
      toast.error("เข้าสู่ระบบไม่สำเร็จ กรุณาลองอีกครั้ง");
    } finally {
      setLoading(null);
    }
  }

  function handleDevTap() {
    const next = devClickCount + 1;
    setDevClickCount(next);
    if (next >= 3) {
      setDevUnlocked(true);
      toast("⚡ เปิดโหมดผู้พัฒนาแล้ว", { description: "เข้าถึงทุกส่วนของระบบได้ครบ" });
    }
  }

  return (
    <div
      className="flex min-h-screen flex-col items-center justify-center px-4 py-12"
      style={{ background: "var(--bg)" }}
    >
      {/* Header */}
      <div className="mb-8 text-center">
        <div className="mb-3 flex items-center justify-center gap-3">
          <span className="text-4xl">🧠</span>
          <div>
            <h1 className="text-3xl font-bold" style={{ color: "var(--text-1)", fontFamily: "var(--font-heading-stack)" }}>
              Q-Sentinel Mesh
            </h1>
            <p className="text-sm" style={{ color: "var(--text-3)" }}>
              เครือข่ายอัจฉริยะสำหรับคัดกรอง stroke แบบ Quantum-Federated
            </p>
          </div>
        </div>
        <div className="flex flex-wrap justify-center gap-2">
          <span className="q-pill">⚡ EfficientNet-B4</span>
          <span className="q-pill">⬡ VQC 4-qubit</span>
          <span className="q-pill">🔒 ML-KEM-512</span>
          <span className="q-pill">🏥 3 โหนดโรงพยาบาล</span>
        </div>
      </div>

      {/* Card */}
      <div
        className="relative w-full max-w-2xl rounded-[1.75rem] border p-8"
        style={{ background: "var(--surface)", borderColor: "var(--border)", boxShadow: "0 24px 64px rgba(194,91,134,0.08)" }}
      >
        <div className="q-eyebrow mb-1 text-center">สิทธิ์การเข้าใช้งาน</div>
        <h2 className="mb-1 text-center text-xl font-bold" style={{ color: "var(--text-1)" }}>
          เลือกบทบาทของคุณ
        </h2>
        <p className="mb-6 text-center text-sm" style={{ color: "var(--text-2)" }}>
          กดที่บทบาทเพื่อเข้าสู่ระบบทันที
        </p>

        {/* Role cards */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {ROLES.map(([roleKey, cfg]) => {
            const isLoading = loading === roleKey;
            const badgeStyle = ROLE_BADGE_STYLE[roleKey];
            return (
              <button
                key={roleKey}
                type="button"
                disabled={loading !== null}
                onClick={() => handleSelect(roleKey)}
                className="group flex flex-col items-start gap-2 rounded-[1.25rem] border p-4 text-left transition-all"
                style={{
                  background: isLoading
                    ? `color-mix(in srgb, ${badgeStyle.color} 10%, var(--surface))`
                    : "var(--surface-2)",
                  borderColor: isLoading ? (badgeStyle.color as string) : "var(--border)",
                  boxShadow: isLoading ? `0 8px 24px ${badgeStyle.color}22` : "none",
                  opacity: loading !== null && !isLoading ? 0.45 : 1,
                  cursor: loading !== null ? "not-allowed" : "pointer",
                  outline: "none",
                }}
              >
                <div className="flex w-full items-center gap-3">
                  <span
                    className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-xl transition-all"
                    style={{
                      background: isLoading ? `${badgeStyle.color}22` : "var(--surface-3)",
                    }}
                  >
                    {isLoading ? (
                      <span className="animate-spin text-sm">⟳</span>
                    ) : cfg.icon}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div
                      className="text-sm font-bold"
                      style={{ color: isLoading ? (badgeStyle.color as string) : "var(--text-1)" }}
                    >
                      {cfg.label}
                    </div>
                  </div>
                  <span
                    className="shrink-0 text-[0.7rem] font-semibold transition-all"
                    style={{ color: isLoading ? (badgeStyle.color as string) : "var(--text-3)" }}
                  >
                    {isLoading ? "กำลังเข้า..." : "→"}
                  </span>
                </div>

                <p className="text-xs leading-5" style={{ color: "var(--text-2)" }}>
                  {cfg.description}
                </p>

                {/* Tab access pills */}
                <div className="flex flex-wrap gap-1">
                  {cfg.tabs.map((tab) => {
                    const tabLabel: Record<string, string> = {
                      "/dashboard":           "วิเคราะห์",
                      "/dashboard/federated": "Federated",
                      "/dashboard/security":  "Security",
                      "/dashboard/pacs":      "PACS",
                    };
                    return (
                      <span
                        key={tab}
                        className="rounded-full border px-2 py-0.5 text-[0.65rem] font-semibold"
                        style={
                          isLoading
                            ? badgeStyle
                            : { background: "var(--surface-3)", borderColor: "var(--border)", color: "var(--text-3)" }
                        }
                      >
                        {tabLabel[tab] ?? tab}
                      </span>
                    );
                  })}
                </div>
              </button>
            );
          })}
        </div>

        <p className="mt-6 text-center text-[0.72rem]" style={{ color: "var(--text-3)" }}>
          CEDT Hackathon 2026 · Demo environment · Prototype only
        </p>

        {/* Hidden dev trigger — tap 3× */}
        <button
          type="button"
          onClick={handleDevTap}
          aria-hidden="true"
          tabIndex={-1}
          style={{
            position: "absolute", bottom: 14, right: 16,
            width: 18, height: 18, opacity: devUnlocked ? 0.7 : devClickCount > 0 ? 0.25 : 0.08,
            background: "none", border: "none", cursor: "default",
            fontSize: 12, transition: "opacity 0.4s", color: "#f59e0b",
          }}
        >
          ⚡
        </button>
      </div>

      {/* Dev card — slides in after unlock */}
      {devUnlocked && (
        <div className="mt-3 w-full max-w-2xl" style={{ animation: "fadeSlideIn 0.4s ease both" }}>
          <button
            type="button"
            disabled={loading !== null}
            onClick={() => handleSelect("dev")}
            className="flex w-full items-center gap-4 rounded-[1.25rem] border px-5 py-4 text-left transition-all"
            style={{
              background: loading === "dev" ? "rgba(245,158,11,0.10)" : "rgba(245,158,11,0.04)",
              borderColor: loading === "dev" ? "#f59e0b" : "rgba(245,158,11,0.25)",
              boxShadow: loading === "dev" ? "0 0 28px rgba(245,158,11,0.18)" : "none",
              opacity: loading !== null && loading !== "dev" ? 0.45 : 1,
            }}
          >
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-2xl" style={{ background: "rgba(245,158,11,0.12)" }}>
              {loading === "dev" ? <span className="animate-spin text-sm">⟳</span> : "⚡"}
            </span>
            <div className="flex-1">
              <div className="text-sm font-bold" style={{ color: "#f59e0b" }}>ผู้พัฒนา / ผู้สร้างระบบ</div>
              <div className="text-xs" style={{ color: "var(--text-3)" }}>Full system access · all modules unlocked</div>
            </div>
            <span className="text-[0.7rem] font-semibold" style={{ color: "#f59e0b" }}>
              {loading === "dev" ? "กำลังเข้า..." : "→"}
            </span>
          </button>
        </div>
      )}

      <style>{`
        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(8px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginContent />
    </Suspense>
  );
}
