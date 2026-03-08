"""
Mock CT Scan Data Generator

Generates realistic-looking synthetic CT scan data for development
and demo purposes when real RSNA data is not available.

Strategy:
- Brain tissue: HU ~20-40 (gray matter ~36, white matter ~20-30)
- Hemorrhage regions: HU ~50-80 (hyperdense blood)
- Air: HU ~-1000 (skull exterior)
- Bone: HU ~700-3000 (skull)
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
import torch
from torch.utils.data import Dataset


# ─── Hemorrhage subtype mapping ───────────────────────────────────────────────
SUBTYPES = [
    "epidural",
    "intraparenchymal",
    "intraventricular",
    "subarachnoid",
    "subdural",
    "any",
]

# Approximate hemorrhage locations (center_x, center_y as fraction of [0,1])
HEMORRHAGE_LOCATIONS = {
    "epidural":          [(0.5, 0.1), (0.5, 0.9)],   # peripheral, near skull
    "intraparenchymal":  [(0.4, 0.4), (0.6, 0.6)],   # deep brain
    "intraventricular":  [(0.5, 0.5)],                 # center (ventricles)
    "subarachnoid":      [(0.5, 0.2), (0.2, 0.5)],   # surface
    "subdural":          [(0.5, 0.1), (0.1, 0.5)],   # just under skull
}


def _generate_skull(size: int = 256) -> np.ndarray:
    """Generate a circular skull mask in HU."""
    ct = np.full((size, size), -1000.0, dtype=np.float32)  # air
    cx, cy = size // 2, size // 2

    # Skull (bone): white ring
    skull_radius = int(size * 0.46)
    skull_thickness = int(size * 0.05)
    for y in range(size):
        for x in range(size):
            d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            if d < skull_radius:
                ct[y, x] = np.random.normal(30, 5)           # brain tissue
            if skull_radius - skull_thickness < d < skull_radius:
                ct[y, x] = np.random.normal(1000, 100)       # bone

    return ct


def generate_mock_slice(
    subtype: str = "normal",
    size: int = 256,
    seed: Optional[int] = None,
) -> np.ndarray:
    """
    Generate a synthetic brain CT slice in Hounsfield Units.

    Args:
        subtype: Hemorrhage type or 'normal'
        size:    Slice resolution (size × size)
        seed:    Random seed for reproducibility

    Returns:
        hu_slice: (size, size) float32 HU array
    """
    if seed is not None:
        np.random.seed(seed)

    ct = _generate_skull(size)

    if subtype != "normal" and subtype in HEMORRHAGE_LOCATIONS:
        # Add hemorrhage blob (Gaussian) at appropriate brain location
        cx, cy = size // 2, size // 2
        for frac_x, frac_y in HEMORRHAGE_LOCATIONS[subtype]:
            hx = int(cx + (frac_x - 0.5) * size * 0.6)
            hy = int(cy + (frac_y - 0.5) * size * 0.6)
            radius = int(size * np.random.uniform(0.04, 0.10))

            # Create hemorrhage blob
            Y, X = np.ogrid[:size, :size]
            blob_mask = (X - hx) ** 2 + (Y - hy) ** 2 <= radius ** 2
            ct[blob_mask] = np.random.normal(65, 10, blob_mask.sum())  # blood HU

    # Add realistic noise
    ct += np.random.normal(0, 8, ct.shape)
    return ct.astype(np.float32)


def generate_mock_volume(
    subtype: str = "normal",
    depth: int = 30,
    size: int = 256,
    seed: Optional[int] = None,
) -> np.ndarray:
    """
    Generate a 3D CT volume.

    Returns:
        volume: (depth, size, size) float32 HU array
    """
    slices = [
        generate_mock_slice(subtype=subtype, size=size, seed=(seed + i if seed is not None else None))
        for i in range(depth)
    ]
    return np.stack(slices, axis=0)


# ─── Mock PyTorch Dataset ─────────────────────────────────────────────────────

class MockCTDataset(Dataset):
    """
    In-memory mock CT dataset for development and demo.

    Generates synthetic 3-channel multi-window tensors with labels.
    """

    def __init__(
        self,
        n_samples: int = 500,
        img_size: int = 256,
        seed: int = 42,
    ):
        self.img_size = img_size
        rng = np.random.default_rng(seed)

        self.samples = []
        self.labels = []

        # Class distribution (roughly matching RSNA dataset imbalance)
        class_weights = [0.05, 0.20, 0.08, 0.15, 0.20, 0.32]  # approximate
        subtypes_with_normal = SUBTYPES[:5] + ["normal"]
        weights_with_normal = [0.05, 0.20, 0.08, 0.15, 0.20, 0.32]

        for i in range(n_samples):
            subtype_idx = rng.choice(len(subtypes_with_normal), p=weights_with_normal)
            subtype = subtypes_with_normal[subtype_idx]

            # Build label vector
            label = np.zeros(6, dtype=np.float32)
            if subtype != "normal":
                idx = SUBTYPES.index(subtype)
                label[idx] = 1.0
                label[5] = 1.0  # 'any' is always 1 if any subtype is positive

            self.samples.append((subtype, i))
            self.labels.append(label)

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int):
        subtype, seed = self.samples[idx]
        hu_slice = generate_mock_slice(subtype=subtype, size=self.img_size, seed=seed)

        # Apply multi-window preprocessing
        from .rsna_loader import apply_window, WINDOWS
        channels = [
            apply_window(hu_slice, center=WINDOWS["brain"][0],    width=WINDOWS["brain"][1]),
            apply_window(hu_slice, center=WINDOWS["blood"][0],    width=WINDOWS["blood"][1]),
            apply_window(hu_slice, center=WINDOWS["subdural"][0], width=WINDOWS["subdural"][1]),
        ]
        img = np.stack(channels, axis=-1).astype(np.float32)   # (H, W, 3)
        tensor = torch.from_numpy(img).permute(2, 0, 1)         # (3, H, W)

        label = torch.tensor(self.labels[idx], dtype=torch.float32)
        return tensor, label, f"mock_{idx:05d}"


def build_mock_dataset(n_samples: int = 500, img_size: int = 256) -> MockCTDataset:
    """Factory function for mock dataset."""
    return MockCTDataset(n_samples=n_samples, img_size=img_size)
