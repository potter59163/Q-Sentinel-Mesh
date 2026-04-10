"use client";
import { useState } from "react";
import api from "@/lib/api";
import type { PredictRequest, PredictResponse } from "@/types/api";

export function usePrediction() {
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function predict(req: PredictRequest): Promise<PredictResponse | null> {
    setLoading(true);
    setError(null);
    try {
      const res = await api.post<PredictResponse>("/api/predict", req);
      setResult(res.data);
      return res.data;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Inference failed";
      setError(msg);
      return null;
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    setResult(null);
    setError(null);
  }

  return { result, loading, error, predict, reset };
}
