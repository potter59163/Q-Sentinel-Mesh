"use client";

import type { WindowPreset } from "@/types/api";

const WINDOW_LABELS: Record<WindowPreset, string> = {
  brain: "Brain",
  blood: "Blood",
  subdural: "Subdural",
  bone: "Bone",
  wide: "Wide",
};

interface Props {
  imageSrc: string | null;
  heatmapSrc: string | null;
  sliceIdx: number;
  sliceCount: number;
  window: WindowPreset;
  heatmapOpacity: number;
  onSliceChange: (idx: number) => void;
  onWindowChange: (w: WindowPreset) => void;
  loading: boolean;
}

export default function CTViewer({
  imageSrc,
  heatmapSrc,
  sliceIdx,
  sliceCount,
  window: currentWindow,
  heatmapOpacity,
  onSliceChange,
  onWindowChange,
  loading,
}: Props) {
  return (
    <div className="overflow-hidden rounded-[1.5rem] border" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
      <div
        className="border-b px-3 py-3 sm:px-4"
        style={{
          borderColor: "var(--border)",
          background: "linear-gradient(180deg, rgba(255,246,248,0.92), rgba(255,255,255,0.72))",
        }}
      >
        <div className="mb-3 flex items-center justify-between gap-3">
          <div>
            <div className="q-eyebrow">Viewer Controls</div>
            <div className="mt-1 text-xs leading-5" style={{ color: "var(--text-2)" }}>
              Choose a clinical window preset before reviewing the active slice and heatmap overlay.
            </div>
          </div>
          <span className="text-[11px]" style={{ color: "var(--text-3)" }}>
            Axial view
          </span>
        </div>
        <div className="flex flex-wrap gap-2">
          {(Object.keys(WINDOW_LABELS) as WindowPreset[]).map((preset) => {
            const active = currentWindow === preset;
            return (
              <button
                key={preset}
                type="button"
                onClick={() => onWindowChange(preset)}
                className="rounded-full px-3 py-1.5 text-xs font-semibold transition-all"
                style={{
                  background: active ? "var(--accent)" : "rgba(255,255,255,0.84)",
                  color: active ? "white" : "var(--text-2)",
                  border: `1px solid ${active ? "var(--accent)" : "var(--border)"}`,
                  boxShadow: active ? "0 10px 24px rgba(194,91,134,0.18)" : "none",
                }}
              >
                {WINDOW_LABELS[preset]}
              </button>
            );
          })}
        </div>
      </div>

      <div className="relative bg-black/95" style={{ minHeight: 320, aspectRatio: "1 / 1" }}>
        {loading ? (
          <div className="absolute inset-0 z-20 flex items-center justify-center">
            <div className="rounded-full px-4 py-2 text-xs font-semibold" style={{ background: "rgba(255,255,255,0.88)", color: "var(--text-1)" }}>
              Loading slice...
            </div>
          </div>
        ) : null}

        {imageSrc ? (
          <>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={imageSrc} alt="CT slice" className="absolute inset-0 h-full w-full object-contain" />
            {heatmapSrc ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={heatmapSrc}
                alt="AI attention heatmap"
                className="absolute inset-0 h-full w-full object-contain"
                style={{ opacity: heatmapOpacity, transition: "opacity 120ms linear" }}
              />
            ) : null}
          </>
        ) : (
          <div className="absolute inset-0 flex items-center justify-center px-6 text-center">
            <div>
              <div className="mb-3 text-5xl opacity-65">🩻</div>
              <div className="text-sm font-semibold text-white">CT viewer waiting for input</div>
              <p className="mt-2 text-xs leading-6 text-white/70">
                Upload a study or load a demo case from the sidebar to begin slice review.
              </p>
            </div>
          </div>
        )}

        {imageSrc ? (
          <>
            <div
              className="absolute left-3 top-3 rounded-full px-3 py-1 text-[11px] font-semibold"
              style={{ background: "rgba(16,16,20,0.72)", color: "white", fontFamily: "var(--font-mono)" }}
            >
              Slice {sliceIdx + 1}/{sliceCount} · {currentWindow.toUpperCase()}
            </div>
            <div className="absolute right-3 top-3 flex flex-wrap gap-2">
              <span className="rounded-full px-3 py-1 text-[11px] font-semibold" style={{ background: "rgba(16,16,20,0.72)", color: "white" }}>
                CT Layer
              </span>
              {heatmapSrc ? (
                <span className="rounded-full px-3 py-1 text-[11px] font-semibold" style={{ background: "rgba(194,91,134,0.88)", color: "white" }}>
                  AI Heatmap
                </span>
              ) : null}
            </div>
          </>
        ) : null}
      </div>

      {sliceCount > 0 ? (
        <div
          className="border-t px-4 py-4"
          style={{
            borderColor: "var(--border)",
            background: "linear-gradient(180deg, rgba(255,252,253,0.82), rgba(255,246,249,0.96))",
          }}
        >
          <div className="mb-2 flex items-center justify-between text-xs">
            <span style={{ color: "var(--text-2)" }}>Slice navigation</span>
            <span className="q-value" style={{ color: "var(--accent)" }}>
              {sliceIdx + 1}/{sliceCount}
            </span>
          </div>
          <input
            type="range"
            min={0}
            max={sliceCount - 1}
            value={sliceIdx}
            onChange={(e) => onSliceChange(Number(e.target.value))}
            className="w-full"
            style={{ accentColor: "var(--accent)" }}
          />
          <div className="mt-2 flex justify-between text-[11px]" style={{ color: "var(--text-3)" }}>
            <span>First slice</span>
            <span>Review progression</span>
            <span>Last slice</span>
          </div>
        </div>
      ) : null}
    </div>
  );
}
