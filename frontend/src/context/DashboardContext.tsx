"use client";

import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import type { CTUploadResponse, ModelType, PredictResponse } from "@/types/api";

interface DashboardContextType {
  modelType: ModelType;
  setModelType: (v: ModelType) => void;
  hospital: string;
  setHospital: (v: string) => void;
  ctMeta: CTUploadResponse | null;
  setCtMeta: (v: CTUploadResponse | null) => void;
  threshold: number;
  setThreshold: (v: number) => void;
  autoTriage: boolean;
  setAutoTriage: (v: boolean) => void;
  scansAnalyzed: number;
  incrementScans: () => void;
  // For PDF export - saved after successful AI analysis.
  lastResult: PredictResponse | null;
  setLastResult: (v: PredictResponse | null) => void;
  lastImageSrc: string | null;
  setLastImageSrc: (v: string | null) => void;
  lastHeatmapSrc: string | null;
  setLastHeatmapSrc: (v: string | null) => void;
}

const DashboardContext = createContext<DashboardContextType | null>(null);

export function DashboardProvider({ children }: { children: ReactNode }) {
  const [modelType, setModelType] = useState<ModelType>("hybrid");
  const [hospital, setHospital] = useState("Hospital A (Bangkok)");
  const [ctMeta, setCtMeta] = useState<CTUploadResponse | null>(null);
  const [threshold, setThreshold] = useState(0.15);
  const [autoTriage, setAutoTriage] = useState(true);
  const [scansAnalyzed, setScansAnalyzed] = useState(0);
  const incrementScans = useCallback(() => setScansAnalyzed((n) => n + 1), []);
  const [lastResult, setLastResult] = useState<PredictResponse | null>(null);
  const [lastImageSrc, setLastImageSrc] = useState<string | null>(null);
  const [lastHeatmapSrc, setLastHeatmapSrc] = useState<string | null>(null);

  return (
    <DashboardContext.Provider
      value={{
        modelType,
        setModelType,
        hospital,
        setHospital,
        ctMeta,
        setCtMeta,
        threshold,
        setThreshold,
        autoTriage,
        setAutoTriage,
        scansAnalyzed,
        incrementScans,
        lastResult,
        setLastResult,
        lastImageSrc,
        setLastImageSrc,
        lastHeatmapSrc,
        setLastHeatmapSrc,
      }}
    >
      {children}
    </DashboardContext.Provider>
  );
}

export function useDashboard() {
  const ctx = useContext(DashboardContext);
  if (!ctx) throw new Error("useDashboard must be used within DashboardProvider");
  return ctx;
}
