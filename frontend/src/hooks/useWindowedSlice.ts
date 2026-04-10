"use client";
import { useState, useCallback, useRef } from "react";
import api from "@/lib/api";
import type { WindowPreset, CTWindowResponse } from "@/types/api";

const cache = new Map<string, string>();

export function useWindowedSlice() {
  const [imageSrc, setImageSrc] = useState<string | null>(null);
  const [huStats, setHuStats] = useState<CTWindowResponse["hu_stats"] | null>(null);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchSlice = useCallback(
    (s3Key: string, sliceIdx: number, window: WindowPreset) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(async () => {
        const cacheKey = `${s3Key}-${sliceIdx}-${window}`;
        if (cache.has(cacheKey)) {
          setImageSrc(cache.get(cacheKey)!);
          return;
        }
        setLoading(true);
        try {
          const res = await api.post<CTWindowResponse>("/api/ct/window", {
            s3_key: s3Key,
            slice_idx: sliceIdx,
            window,
          });
          cache.set(cacheKey, res.data.image_b64);
          setImageSrc(res.data.image_b64);
          setHuStats(res.data.hu_stats);
        } catch {
          /* ignore */
        } finally {
          setLoading(false);
        }
      }, 150);
    },
    []
  );

  return { imageSrc, huStats, loading, fetchSlice };
}
