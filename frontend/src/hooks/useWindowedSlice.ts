"use client";

import { useCallback, useRef, useState } from "react";
import api, { getApiErrorMessage } from "@/lib/api";
import type { CTWindowResponse, WindowPreset } from "@/types/api";

const cache = new Map<string, CTWindowResponse>();

export function useWindowedSlice() {
  const [imageSrc, setImageSrc] = useState<string | null>(null);
  const [huStats, setHuStats] = useState<CTWindowResponse["hu_stats"] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const fetchSlice = useCallback((s3Key: string, sliceIdx: number, window: WindowPreset) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);

    debounceRef.current = setTimeout(async () => {
      const cacheKey = `${s3Key}-${sliceIdx}-${window}`;
      if (cache.has(cacheKey)) {
        if (abortRef.current) abortRef.current.abort();
        const cached = cache.get(cacheKey)!;
        setImageSrc(cached.image_b64);
        setHuStats(cached.hu_stats);
        setLoading(false);
        setError(null);
        return;
      }

      if (abortRef.current) abortRef.current.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setLoading(true);
      setError(null);

      try {
        const res = await api.post<CTWindowResponse>(
          "/api/ct/window",
          {
            s3_key: s3Key,
            slice_idx: sliceIdx,
            window,
          },
          { signal: controller.signal }
        );

        if (controller.signal.aborted) return;

        cache.set(cacheKey, res.data);
        setImageSrc(res.data.image_b64);
        setHuStats(res.data.hu_stats);
      } catch (err) {
        if (controller.signal.aborted) return;
        setError(getApiErrorMessage(err));
      } finally {
        if (abortRef.current === controller) {
          setLoading(false);
        }
      }
    }, 150);
  }, []);

  return { imageSrc, huStats, loading, error, fetchSlice };
}
