"use client";

import { useState } from "react";
import { toast } from "sonner";
import api from "@/lib/api";
import type { PQCDemoResponse } from "@/types/api";

const FLOW_STEPS = [
  ["1", "Local training", "Hospital nodes train on-site and prepare only model deltas for exchange."],
  ["2", "Key encapsulation", "ML-KEM-512 creates a shared secret using the server public key."],
  ["3", "Authenticated encryption", "HKDF-SHA256 derives an AES key and seals the weight payload with AES-256-GCM."],
  ["4", "Secure aggregation", "The server decapsulates, decrypts, aggregates, and prepares the new global weights."],
  ["5", "Encrypted return path", "Updated global weights are securely redistributed back to each hospital node."],
];

const SPECS = [
  ["KEM algorithm", "ML-KEM-512", "var(--accent)"],
  ["Standard", "NIST FIPS 203", "var(--accent)"],
  ["Security level", "128-bit post-quantum", "var(--text-1)"],
  ["Symmetric cipher", "AES-256-GCM", "var(--text-1)"],
  ["Key derivation", "HKDF-SHA256", "var(--text-1)"],
  ["Transport", "TLS 1.3 + PQC", "var(--text-1)"],
  ["Data privacy", "No raw CT leaves site", "var(--success)"],
  ["Compliance", "PDPA / HIPAA-aligned", "var(--text-1)"],
] as const;

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

export default function SecurityPage() {
  const [demoResult, setDemoResult] = useState<PQCDemoResponse | null>(null);
  const [loading, setLoading] = useState(false);

  async function runPQCDemo() {
    setLoading(true);
    try {
      const res = await api.post<PQCDemoResponse>("/api/pqc/demo");
      setDemoResult(res.data);
      toast.success(res.data.success ? "PQC demo completed successfully" : "PQC demo failed");
    } catch {
      toast.error("Unable to complete the PQC demo");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        {[
          ["KEM algorithm", "ML-KEM-512", "NIST-standardized post-quantum key encapsulation.", "var(--accent)"],
          ["Security level", "128-bit PQ", "Practical protection for production-style transport flows.", "var(--text-1)"],
          ["Privacy posture", "No raw CT", "Only encrypted model updates move across the federated network.", "var(--success)"],
          ["Transport stack", "KEM + AES", "ML-KEM-512, HKDF-SHA256, and AES-256-GCM working together.", "var(--info)"],
        ].map(([label, value, note, color]) => (
          <article key={label} className="q-soft-panel rounded-[1.25rem] px-4 py-4">
            <div className="q-eyebrow mb-1">{label}</div>
            <div className="text-[1.55rem] font-bold leading-none" style={{ color, fontFamily: "var(--font-mono)" }}>
              {value}
            </div>
            <p className="mt-2 text-xs leading-5" style={{ color: "var(--text-2)" }}>
              {note}
            </p>
          </article>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,0.92fr)]">
        <Panel eyebrow="Protocol Walkthrough" title="Encrypted Transmission Flow">
          <div className="flex flex-col">
            {FLOW_STEPS.map(([num, title, desc], index) => (
              <div
                key={`${num}-${title}`}
                className="flex gap-3 py-3"
                style={{ borderBottom: index === FLOW_STEPS.length - 1 ? "none" : "1px solid var(--border)" }}
              >
                <div
                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold"
                  style={{
                    background: "var(--accent-light)",
                    border: "1px solid var(--accent-soft)",
                    color: "var(--accent)",
                    fontFamily: "var(--font-mono)",
                  }}
                >
                  {num}
                </div>
                <div>
                  <div className="text-sm font-semibold" style={{ color: "var(--text-1)" }}>
                    {title}
                  </div>
                  <div className="mt-1 text-xs leading-6" style={{ color: "var(--text-3)" }}>
                    {desc}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Panel>

        <div className="flex flex-col gap-4">
          <Panel eyebrow="Implementation View" title="Specifications">
            {SPECS.map(([label, value, color]) => (
              <div key={label} className="q-stat-row">
                <span style={{ color: "var(--text-3)" }}>{label}</span>
                <span className="q-value text-[0.78rem]" style={{ color }}>{value}</span>
              </div>
            ))}
          </Panel>

          <Panel eyebrow="Live PQC Demo" title="Generate and Verify">
            <button
              type="button"
              onClick={runPQCDemo}
              disabled={loading}
              className="q-btn-primary w-full px-4 py-3 text-sm"
              style={{ opacity: loading ? 0.7 : 1, cursor: loading ? "not-allowed" : "pointer" }}
            >
              {loading ? "Running PQC demo..." : "Generate key pair and test encryption"}
            </button>

            {demoResult ? (
              <div
                className="mt-4 rounded-[1rem] border px-4 py-4 text-xs"
                style={{
                  background: demoResult.success ? "var(--surface-success)" : "var(--surface-3)",
                  borderColor: demoResult.success ? "var(--success-soft)" : "var(--accent-soft)",
                }}
              >
                <div className="mb-3 text-sm font-semibold" style={{ color: demoResult.success ? "var(--success)" : "var(--accent)" }}>
                  {demoResult.success ? "Verification successful" : "Verification failed"}
                  {demoResult.backend ? <span style={{ color: "var(--text-3)" }}> - {demoResult.backend}</span> : null}
                </div>
                {demoResult.success ? (
                  <div className="space-y-1.5">
                    <SpecRow label="Public key" value={`${demoResult.public_key_bytes} bytes`} />
                    <SpecRow label="Secret key" value={`${demoResult.secret_key_bytes} bytes`} />
                    <SpecRow label="KEM ciphertext" value={`${demoResult.kem_ciphertext_bytes} bytes`} />
                    <SpecRow label="AES ciphertext" value={`${demoResult.aes_ciphertext_bytes} bytes`} />
                    <div className="my-2 border-t" style={{ borderColor: "var(--border)" }} />
                    <SpecRow label="Key generation" value={`${demoResult.keygen_ms.toFixed(1)} ms`} />
                    <SpecRow label="Encrypt" value={`${demoResult.encrypt_ms.toFixed(1)} ms`} />
                    <SpecRow label="Decrypt" value={`${demoResult.decrypt_ms.toFixed(1)} ms`} />
                  </div>
                ) : (
                  <div style={{ color: "var(--text-2)" }}>{demoResult.error ?? "Unknown PQC error"}</div>
                )}
              </div>
            ) : null}
          </Panel>
        </div>
      </div>

      <section className="q-card rounded-[1.5rem] px-5 py-5" style={{ background: "linear-gradient(180deg, rgba(253,234,241,0.98), rgba(255,243,247,0.94))", borderColor: "var(--accent-soft)" }}>
        <div className="q-eyebrow mb-1" style={{ color: "var(--accent)" }}>
          Why it matters
        </div>
        <h3 className="text-lg font-semibold" style={{ color: "var(--accent)" }}>
          Healthcare AI needs a security story that lasts
        </h3>
        <p className="mt-2 text-sm leading-7" style={{ color: "var(--text-2)" }}>
          Long-lived medical data and model IP should not depend only on cryptography that may be broken by future quantum computers.
          Standardizing on ML-KEM-512 now gives hospital collaboration a stronger trust and privacy narrative.
        </p>
      </section>
    </div>
  );
}

function SpecRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span style={{ color: "var(--text-3)" }}>{label}</span>
      <span className="q-value" style={{ color: "var(--text-1)" }}>
        {value}
      </span>
    </div>
  );
}
