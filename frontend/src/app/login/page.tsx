"use client";

import { Activity, Brain, LockKeyhole, Sparkles } from "lucide-react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import api from "@/lib/api";
import { setToken } from "@/lib/auth";

const FEATURES = [
  { icon: <Brain className="h-4 w-4" />, title: "Diagnostic review", copy: "Inspect slices, run the model, and read explanation overlays in one flow." },
  { icon: <Activity className="h-4 w-4" />, title: "Federated metrics", copy: "Show hospital contribution and global performance without moving raw CT data." },
  { icon: <LockKeyhole className="h-4 w-4" />, title: "PQC security", copy: "Support the demo with a clear post-quantum protection story." },
];

export default function LoginPage() {
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await api.post("/api/auth/login", { password });
      const token: string = res.data.access_token;
      setToken(token);
      document.cookie = `qsentinel_token=${token}; path=/; max-age=86400; SameSite=Lax`;
      router.push("/dashboard");
    } catch {
      toast.error("Incorrect password");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen px-4 py-8 sm:py-10">
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-6xl items-center justify-center">
        <div className="grid w-full gap-6 lg:grid-cols-[1.05fr_minmax(360px,0.8fr)]">
          <section className="q-card rounded-[1.75rem] px-6 py-7 sm:px-8">
            <div className="q-kicker-row mb-4">
              <span className="q-pill q-pill-success">
                <Activity className="h-3.5 w-3.5" />
                Research demo online
              </span>
              <span className="q-pill q-pill-accent">🧠 Q-Sentinel Mesh</span>
            </div>

            <div className="q-page-intro">
              <h1 data-heading="display" className="q-page-intro-title">
                Clinical AI dashboards that feel easier to trust and easier to use.
              </h1>
              <p className="q-page-intro-copy">
                Sign in to open the CT review workspace, federated learning overview, and post-quantum security layer in one connected interface.
              </p>
            </div>

            <div className="mt-6 grid gap-3 sm:grid-cols-3">
              {FEATURES.map((feature) => (
                <div key={feature.title} className="q-surface-muted px-4 py-4">
                  <div className="q-inline-icon mb-3 rounded-full border p-2" style={{ borderColor: "var(--accent-soft)", color: "var(--accent)", background: "var(--accent-light)" }}>
                    {feature.icon}
                  </div>
                  <div className="text-sm font-semibold" style={{ color: "var(--text-1)" }}>
                    {feature.title}
                  </div>
                  <p className="mt-2 text-xs leading-5" style={{ color: "var(--text-2)" }}>
                    {feature.copy}
                  </p>
                </div>
              ))}
            </div>
          </section>

          <section className="q-card rounded-[1.75rem] px-6 py-8 sm:px-8">
            <div className="mb-7 text-center">
              <div className="mb-3 inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold" style={{ borderColor: "var(--accent-soft)", background: "var(--accent-light)", color: "var(--accent)" }}>
                <Sparkles className="h-3.5 w-3.5" />
                Secure workspace access
              </div>
              <h2 data-heading="display" className="text-3xl font-semibold" style={{ color: "var(--accent)" }}>
                Sign in
              </h2>
              <p className="mt-2 text-sm" style={{ color: "var(--text-3)" }}>
                Use the demo password to enter the workspace.
              </p>
            </div>

            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="mb-2 block text-sm font-medium" style={{ color: "var(--text-2)" }}>
                  Demo password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter the demo password"
                  required
                  className="q-input"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="q-btn-primary w-full px-4 py-3 text-sm"
                style={{ opacity: loading ? 0.7 : 1, cursor: loading ? "not-allowed" : "pointer" }}
              >
                {loading ? "Signing in..." : "Enter workspace"}
              </button>
            </form>

            <div className="mt-5 q-surface-muted px-4 py-4">
              <div className="q-eyebrow mb-1">Inside the workspace</div>
              <p className="text-xs leading-6" style={{ color: "var(--text-2)" }}>
                You can move from CT intake to AI result, then compare federated performance and security signals without changing tools.
              </p>
            </div>

            <p className="mt-6 text-center text-xs leading-6" style={{ color: "var(--text-3)" }}>
              CEDT Hackathon 2026 - Research demonstration build
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
