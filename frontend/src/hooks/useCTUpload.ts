"use client";
import { useState } from "react";
import api from "@/lib/api";
import type { CTUploadResponse } from "@/types/api";

export function useCTUpload() {
  const [ctMeta, setCtMeta] = useState<CTUploadResponse | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function upload(file: File) {
    setUploading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await api.post<CTUploadResponse>("/api/ct/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 120_000,
      });
      setCtMeta(res.data);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Upload failed";
      setError(msg);
    } finally {
      setUploading(false);
    }
  }

  function reset() {
    setCtMeta(null);
    setError(null);
  }

  return { ctMeta, uploading, error, upload, reset };
}
