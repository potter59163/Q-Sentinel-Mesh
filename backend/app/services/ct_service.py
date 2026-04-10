"""CT loading, HU normalization, and windowing service.
Logic ported from dashboard/components/ct_viewer.py and app.py lines 382-390.
"""
import base64
import io
import threading
import time
from typing import Dict, Optional, Tuple

import numpy as np
from PIL import Image

from app.models.ct import CTUploadResponse, CTWindowResponse, HUStats, WindowPreset

# Window presets: (center, width) in HU — from ct_viewer.py line 22-31
WINDOW_PRESETS: Dict[str, Tuple[int, int]] = {
    "brain":    (40,  80),
    "blood":    (60, 100),
    "subdural": (75, 215),
    "bone":     (400, 1800),
    "wide":     (40, 380),
}

# In-memory cache: s3_key → (volume_hu: np.ndarray, timestamp: float)
_cache: Dict[str, Tuple[np.ndarray, float]] = {}
_cache_lock = threading.Lock()
_TTL = 1800  # 30 minutes


def _evict_expired():
    now = time.time()
    with _cache_lock:
        expired = [k for k, (_, ts) in _cache.items() if now - ts > _TTL]
        for k in expired:
            del _cache[k]


def _normalize_hu(volume: np.ndarray) -> np.ndarray:
    """Port of app.py lines 382-390: handle 8/9-bit, normalized, and raw HU."""
    if volume.max() <= 1.5:
        # Normalized [0,1] float
        return (volume * 2000.0 - 1000.0).astype(np.float32)
    elif volume.max() <= 255:
        # 8-bit or 9-bit (pydicom without rescale)
        return (volume.astype(np.float32) * 8.0 - 1024.0)
    else:
        return volume.astype(np.float32)


def _apply_window(slice_hu: np.ndarray, center: int, width: int) -> np.ndarray:
    """Apply HU windowing → [0, 255] uint8."""
    lo = center - width / 2
    hi = center + width / 2
    clipped = np.clip(slice_hu, lo, hi)
    normalized = (clipped - lo) / (hi - lo)
    return (normalized * 255).astype(np.uint8)


def _to_base64_png(arr: np.ndarray) -> str:
    img = Image.fromarray(arr, mode="L").convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


class CTService:
    def load_ct(self, content: bytes, filename: str, s3_key: str) -> CTUploadResponse:
        """Parse NIfTI or DICOM bytes, normalize HU, cache volume."""
        ext = filename.lower().split(".")[-1]

        if ext == "nii":
            volume = self._load_nifti(content)
        elif ext == "dcm":
            volume = self._load_dicom(content)
        else:
            raise ValueError(f"Unsupported extension: {ext}")

        volume_hu = _normalize_hu(volume)

        with _cache_lock:
            _cache[s3_key] = (volume_hu, time.time())

        d, h, w = volume_hu.shape
        return CTUploadResponse(
            s3_key=s3_key,
            slice_count=d,
            shape=(d, h, w),
            min_hu=float(volume_hu.min()),
            max_hu=float(volume_hu.max()),
            filename=filename,
        )

    def _load_nifti(self, content: bytes) -> np.ndarray:
        import nibabel as nib
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".nii", delete=False) as f:
            f.write(content)
            tmp_path = f.name
        try:
            img = nib.load(tmp_path)
            data = np.array(img.dataobj)
            # NIfTI: axes are (H, W, D) → reorder to (D, H, W)
            if data.ndim == 3:
                data = np.transpose(data, (2, 0, 1))
            elif data.ndim == 4:
                data = np.transpose(data[:, :, :, 0], (2, 0, 1))
            return data
        finally:
            os.unlink(tmp_path)

    def _load_dicom(self, content: bytes) -> np.ndarray:
        import pydicom
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".dcm", delete=False) as f:
            f.write(content)
            tmp_path = f.name
        try:
            ds = pydicom.dcmread(tmp_path)
            arr = ds.pixel_array.astype(np.float32)
            # Single DICOM = single slice → wrap in axis 0
            if arr.ndim == 2:
                arr = arr[np.newaxis, ...]
            return arr
        finally:
            os.unlink(tmp_path)

    def get_volume(self, s3_key: str) -> Optional[np.ndarray]:
        _evict_expired()
        with _cache_lock:
            entry = _cache.get(s3_key)
        if entry is None:
            return None
        return entry[0]

    def get_windowed_slice(
        self, s3_key: str, slice_idx: int, window: WindowPreset
    ) -> Optional[CTWindowResponse]:
        volume = self.get_volume(s3_key)
        if volume is None:
            return None

        slice_idx = max(0, min(slice_idx, volume.shape[0] - 1))
        slice_hu = volume[slice_idx]

        center, width = WINDOW_PRESETS.get(window, WINDOW_PRESETS["brain"])
        windowed = _apply_window(slice_hu, center, width)
        image_b64 = _to_base64_png(windowed)

        return CTWindowResponse(
            image_b64=image_b64,
            hu_stats=HUStats(
                mean=float(slice_hu.mean()),
                std=float(slice_hu.std()),
                min=float(slice_hu.min()),
                max=float(slice_hu.max()),
            ),
        )


ct_service = CTService()
