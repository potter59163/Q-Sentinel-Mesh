import { useEffect, useState } from "react";
import api from "@/lib/api";
import type { FedRound } from "@/types/api";

export function useFedRounds() {
  const [data, setData] = useState<FedRound[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<FedRound[]>("/api/federated/rounds")
      .then((r) => setData(r.data))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return { data, loading, error };
}
