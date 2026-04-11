"use client";
import { useState } from "react";
import api, { getApiErrorMessage } from "@/lib/api";
import type { PredictRequest, PredictResponse } from "@/types/api";

export function usePrediction() {
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastLatencyMs, setLastLatencyMs] = useState<number | null>(null);
  const [lastRequestId, setLastRequestId] = useState<string | null>(null);

  async function predict(req: PredictRequest): Promise<PredictResponse | null> {
    setLoading(true);
    setError(null);
    try {
      const res = await api.post<PredictResponse>("/api/predict", req);
      const latency = Number(res.headers?.["x-response-time-ms"]);
      setLastLatencyMs(Number.isFinite(latency) ? latency : null);
      setLastRequestId(res.headers?.["x-request-id"] ?? null);
      setResult(res.data);
      return res.data;
    } catch (e: unknown) {
      const msg = getApiErrorMessage(e);
      setError(msg);
      return null;
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    setResult(null);
    setError(null);
    setLastLatencyMs(null);
    setLastRequestId(null);
  }

  return { result, loading, error, predict, reset, lastLatencyMs, lastRequestId };
}
