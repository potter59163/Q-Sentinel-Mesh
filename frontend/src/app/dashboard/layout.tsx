import MetricsStrip from "@/components/layout/MetricsStrip";
import NavTabs from "@/components/layout/NavTabs";
import Sidebar from "@/components/layout/Sidebar";
import { DashboardProvider } from "@/context/DashboardContext";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <DashboardProvider>
      <div className="q-app-shell">
        <Sidebar />
        <div className="q-app-main">
          <div className="q-hero-card q-fade-top">
            <div className="q-hero-watermark" aria-hidden>QSM</div>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0">
                <h1
                  className="flex items-center gap-2 text-2xl font-bold"
                  style={{ color: "var(--text-1)", fontFamily: "var(--font-heading-stack)" }}
                >
                  🧠 Q-Sentinel Mesh
                </h1>
                <p className="mt-0.5 text-sm" style={{ color: "var(--text-2)" }}>
                  เครือข่ายอัจฉริยะสำหรับคัดกรอง stroke แบบ Quantum-Federated
                </p>
                <div className="mt-2.5 flex flex-wrap gap-1.5">
                  <span className="q-pill">⚡ EfficientNet-B4</span>
                  <span className="q-pill">⬡ VQC 4-qubit</span>
                  <span className="q-pill">🔒 ML-KEM-512</span>
                  <span className="q-pill">🏥 3 โหนดโรงพยาบาล</span>
                </div>
              </div>
              <div className="hidden shrink-0 flex-col items-end gap-1.5 sm:flex">
                <span className="q-pill q-pill-success">● ออนไลน์</span>
                <span className="q-pill">PQC · NIST FIPS 203</span>
                <span className="q-pill q-pill-accent">⬡ เสริมพลังด้วยควอนตัม</span>
              </div>
            </div>
          </div>

          <MetricsStrip />
          <NavTabs />

          <ErrorBoundary>
            <div>{children}</div>
          </ErrorBoundary>

          <footer
            className="mt-4 text-center text-[0.7rem] leading-6"
            style={{ color: "var(--text-3)" }}
          >
            Q-Sentinel Mesh v1.0 · CEDT Hackathon 2026 · อินเทอร์เฟซต้นแบบสำหรับงานวิจัยและการสาธิตเท่านั้น
          </footer>
        </div>
      </div>
    </DashboardProvider>
  );
}
