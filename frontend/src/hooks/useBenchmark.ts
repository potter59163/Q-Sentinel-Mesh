import { useEffect, useState } from "react";
import api from "@/lib/api";
import type { BenchmarkData } from "@/types/api";

export function useBenchmark() {
  const [data, setData] = useState<BenchmarkData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<BenchmarkData>("/api/metrics/benchmark")
      .then((r) => setData(r.data))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return { data, loading, error };
}
