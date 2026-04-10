"use client";
import { useCallback } from "react";
import { useDropzone } from "react-dropzone";

interface Props {
  onFile: (file: File) => void;
  uploading: boolean;
  ctMeta: { filename: string; slice_count: number; shape: number[] } | null;
}

export default function FileUploadPanel({ onFile, uploading, ctMeta }: Props) {
  const onDrop = useCallback(
    (accepted: File[]) => {
      if (accepted[0]) onFile(accepted[0]);
    },
    [onFile]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/octet-stream": [".nii", ".dcm"] },
    multiple: false,
  });

  return (
    <div className="flex flex-col gap-3">
      <div
        {...getRootProps()}
        className="border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all"
        style={{
          borderColor: isDragActive ? "var(--accent)" : "var(--border)",
          background: isDragActive ? "var(--accent-light)" : "var(--surface-2)",
        }}
      >
        <input {...getInputProps()} />
        <div className="text-2xl mb-2">📂</div>
        <div className="text-sm font-medium" style={{ color: "var(--text-1)" }}>
          {uploading ? "กำลังอัพโหลด..." : isDragActive ? "วางไฟล์ที่นี่" : "อัพโหลด CT Scan"}
        </div>
        <div className="text-xs mt-1" style={{ color: "var(--text-3)" }}>
          รองรับ NIfTI (.nii) และ DICOM (.dcm)
        </div>
      </div>

      {ctMeta && (
        <div
          className="rounded-xl p-4 text-sm"
          style={{ background: "var(--success-light)", border: "1px solid var(--success-soft)" }}
        >
          <div className="font-semibold mb-1" style={{ color: "var(--success)" }}>
            ✓ โหลดสำเร็จ
          </div>
          <div style={{ color: "var(--text-2)" }}>{ctMeta.filename}</div>
          <div className="text-xs mt-1" style={{ color: "var(--text-3)" }}>
            {ctMeta.slice_count} slices · {ctMeta.shape.join(" × ")} px
          </div>
        </div>
      )}
    </div>
  );
}
