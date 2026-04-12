"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import type { CTUploadResponse, ModelType, PredictResponse, RadiologistVerdict } from "@/types/api";
import { getStoredAuth, type UserRole } from "@/lib/auth";

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
  // Current user role
  userRole: UserRole | null;
  // Radiologist review
  lastSessionId: string | null;
  setLastSessionId: (v: string | null) => void;
  lastVerdict: RadiologistVerdict | null;
  setLastVerdict: (v: RadiologistVerdict | null) => void;
  lastCorrectedClass: string | null;
  setLastCorrectedClass: (v: string | null) => void;
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
  const [userRole, setUserRole] = useState<UserRole | null>(null);
  useEffect(() => {
    const auth = getStoredAuth();
    if (auth) setUserRole(auth.role as UserRole);
  }, []);

  const [lastResult, setLastResult] = useState<PredictResponse | null>(null);
  const [lastImageSrc, setLastImageSrc] = useState<string | null>(null);
  const [lastHeatmapSrc, setLastHeatmapSrc] = useState<string | null>(null);
  const [lastSessionId, setLastSessionId] = useState<string | null>(null);
  const [lastVerdict, setLastVerdict] = useState<RadiologistVerdict | null>(null);
  const [lastCorrectedClass, setLastCorrectedClass] = useState<string | null>(null);

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
        userRole,
        lastSessionId,
        setLastSessionId,
        lastVerdict,
        setLastVerdict,
        lastCorrectedClass,
        setLastCorrectedClass,
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
