"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { toast } from "sonner";
import api from "@/lib/api";
import { ROLE_CONFIG, setAuth, type UserRole } from "@/lib/auth";

// Public-facing roles only (dev is hidden easter egg)
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
  const [selected, setSelected] = useState<UserRole | null>(null);
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [devUnlocked, setDevUnlocked] = useState(false);
  const [devClickCount, setDevClickCount] = useState(0);

  function handleDevTap() {
    const next = devClickCount + 1;
    setDevClickCount(next);
    if (next >= 3) {
      setDevUnlocked(true);
      setSelected("dev");
      toast("⚡ Developer mode unlocked", { description: "Full system access granted." });
    }
  }

  async function handleLogin() {
    if (!selected) { toast.warning("Select your role first."); return; }
    if (!password)  { toast.warning("Enter the access password."); return; }

    setLoading(true);
    try {
      const res = await api.post<{ access_token: string; role: UserRole }>(
        "/api/auth/login",
        { password, role: selected }
      );
      setAuth(res.data.access_token);
      toast.success(`Signed in as ${ROLE_CONFIG[res.data.role].label}`);
      const from = params.get("from");
      const dest = from && from.startsWith("/dashboard")
        ? from
        : ROLE_CONFIG[res.data.role].defaultPath;
      router.push(dest);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Access denied — check your password.";
      toast.error(msg);
    } finally {
      setLoading(false);
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
              Quantum-Federated Stroke Diagnostic Intelligence Network
            </p>
          </div>
        </div>
        <div className="flex flex-wrap justify-center gap-2">
          <span className="q-pill">⚡ EfficientNet-B4</span>
          <span className="q-pill">⬡ VQC 4-qubit</span>
          <span className="q-pill">🔒 ML-KEM-512</span>
          <span className="q-pill">🏥 3 Hospital Nodes</span>
        </div>
      </div>

      <div
        className="relative w-full max-w-2xl rounded-[1.75rem] border p-8"
        style={{ background: "var(--surface)", borderColor: "var(--border)", boxShadow: "0 24px 64px rgba(194,91,134,0.08)" }}
      >
        <div className="q-eyebrow mb-1 text-center">Access Control</div>
        <h2 className="mb-1 text-center text-xl font-bold" style={{ color: "var(--text-1)" }}>
          Select your role
        </h2>
        <p className="mb-6 text-center text-sm" style={{ color: "var(--text-2)" }}>
          Each role has access to the tools relevant to your clinical or operational function.
        </p>

        {/* Role cards */}
        <div className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {ROLES.map(([roleKey, cfg]) => {
            const isSelected = selected === roleKey;
            const badgeStyle = ROLE_BADGE_STYLE[roleKey];
            return (
              <button
                key={roleKey}
                type="button"
                onClick={() => setSelected(roleKey)}
                className="group relative flex flex-col items-start gap-2 rounded-[1.25rem] border p-4 text-left transition-all"
                style={{
                  background: isSelected
                    ? `color-mix(in srgb, ${badgeStyle.color} 8%, var(--surface))`
                    : "var(--surface-2)",
                  borderColor: isSelected ? (badgeStyle.color as string) : "var(--border)",
                  boxShadow: isSelected ? `0 8px 24px ${badgeStyle.color}22` : "none",
                  outline: "none",
                }}
              >
                {/* Role icon + name */}
                <div className="flex w-full items-center gap-3">
                  <span
                    className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-xl"
                    style={{
                      background: isSelected ? `${badgeStyle.color}22` : "var(--surface-3)",
                    }}
                  >
                    {cfg.icon}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-bold" style={{ color: isSelected ? (badgeStyle.color as string) : "var(--text-1)" }}>
                      {cfg.label}
                    </div>
                  </div>
                  {/* Selection indicator */}
                  <span
                    className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 text-[10px] font-bold"
                    style={{
                      borderColor: isSelected ? (badgeStyle.color as string) : "var(--border)",
                      background: isSelected ? (badgeStyle.color as string) : "transparent",
                      color: "white",
                    }}
                  >
                    {isSelected ? "✓" : ""}
                  </span>
                </div>

                {/* Description */}
                <p className="text-xs leading-5" style={{ color: "var(--text-2)" }}>
                  {cfg.description}
                </p>

                {/* Tab access pills */}
                <div className="flex flex-wrap gap-1">
                  {cfg.tabs.map((tab) => {
                    const tabLabel: Record<string, string> = {
                      "/dashboard": "Diagnostic",
                      "/dashboard/federated": "Federated",
                      "/dashboard/security": "Security",
                      "/dashboard/pacs": "PACS",
                    };
                    return (
                      <span
                        key={tab}
                        className="rounded-full border px-2 py-0.5 text-[0.65rem] font-semibold"
                        style={isSelected ? badgeStyle : { background: "var(--surface-3)", borderColor: "var(--border)", color: "var(--text-3)" }}
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

        {/* Password field */}
        <div className="mb-4">
          <label className="q-eyebrow mb-2 block">Access Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleLogin()}
            placeholder="Enter demo password"
            className="w-full rounded-[0.85rem] border px-4 py-3 text-sm outline-none transition-all"
            style={{
              background: "var(--surface-2)",
              borderColor: "var(--border-strong)",
              color: "var(--text-1)",
            }}
            autoComplete="current-password"
          />
        </div>

        {/* Login button */}
        <button
          type="button"
          onClick={handleLogin}
          disabled={loading || !selected || !password}
          className="q-btn-primary w-full py-3.5 text-sm font-bold"
          style={{ opacity: loading || !selected || !password ? 0.55 : 1, cursor: loading || !selected || !password ? "not-allowed" : "pointer" }}
        >
          {loading ? "Authenticating..." : selected ? `Sign in as ${ROLE_CONFIG[selected].label}` : "Select a role to continue"}
        </button>

        <p className="mt-4 text-center text-[0.72rem]" style={{ color: "var(--text-3)" }}>
          CEDT Hackathon 2026 · Demo environment · Prototype only
        </p>

        {/* Easter egg — hidden dev trigger, bottom-right corner */}
        <button
          type="button"
          onClick={handleDevTap}
          aria-hidden="true"
          tabIndex={-1}
          style={{
            position: "absolute",
            bottom: 14,
            right: 16,
            width: 18,
            height: 18,
            opacity: devUnlocked ? 0.7 : devClickCount > 0 ? 0.25 : 0.08,
            background: "none",
            border: "none",
            cursor: "default",
            fontSize: 12,
            transition: "opacity 0.4s",
            color: "#f59e0b",
          }}
        >
          ⚡
        </button>
      </div>

      {/* Dev card — slides in after unlock */}
      {devUnlocked && (
        <div
          className="mt-3 w-full max-w-2xl animate-pulse-once"
          style={{ animation: "fadeSlideIn 0.4s ease both" }}
        >
          <button
            type="button"
            onClick={() => setSelected("dev")}
            className="group flex w-full items-center gap-4 rounded-[1.25rem] border px-5 py-4 text-left transition-all"
            style={{
              background: selected === "dev"
                ? "rgba(245,158,11,0.10)"
                : "rgba(245,158,11,0.04)",
              borderColor: selected === "dev" ? "#f59e0b" : "rgba(245,158,11,0.25)",
              boxShadow: selected === "dev" ? "0 0 28px rgba(245,158,11,0.18)" : "none",
            }}
          >
            <span
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-2xl"
              style={{ background: "rgba(245,158,11,0.12)" }}
            >
              ⚡
            </span>
            <div className="flex-1">
              <div className="text-sm font-bold" style={{ color: "#f59e0b" }}>
                Developer / Creator
              </div>
              <div className="text-xs" style={{ color: "var(--text-3)" }}>
                Full system access · all modules unlocked · built this
              </div>
            </div>
            <span
              className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 text-[10px] font-bold"
              style={{
                borderColor: selected === "dev" ? "#f59e0b" : "rgba(245,158,11,0.3)",
                background: selected === "dev" ? "#f59e0b" : "transparent",
                color: "white",
              }}
            >
              {selected === "dev" ? "✓" : ""}
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
