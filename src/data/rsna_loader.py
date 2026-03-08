"""
RSNA Intracranial Hemorrhage Detection — Data Pipeline

Handles DICOM loading, HU conversion, multi-window preprocessing,
and PyTorch Dataset construction.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import pydicom
import torch
from torch.utils.data import Dataset
from torchvision import transforms
from tqdm import tqdm

# ─── Hemorrhage subtypes (RSNA label order) ────────────────────────────────────
SUBTYPES = [
    "epidural",
    "intraparenchymal",
    "intraventricular",
    "subarachnoid",
    "subdural",
    "any",
]

# ─── CT Window presets (center, width) ────────────────────────────────────────
WINDOWS = {
    "brain":    (40,  80),
    "blood":    (60,  120),
    "subdural": (75,  215),
}


# ─── Custom augmentation transforms ───────────────────────────────────────────

class GaussianNoise:
    """
    Add random Gaussian noise to simulate electronic scanner noise.

    Mimics the signal variation seen in older or lower-dose CT scanners
    (e.g. county hospital equipment).  Applied BEFORE normalization so
    std=0.02 maps to ~20 HU of noise in the [0,1]-normalised space.
    """
    def __init__(self, std: float = 0.02):
        self.std = std

    def __call__(self, tensor: torch.Tensor) -> torch.Tensor:
        noise = torch.randn_like(tensor) * self.std
        return (tensor + noise).clamp(0.0, 1.0)


# ──────────────────────────────────────────────────────────────────────────────
# DICOM Processing
# ──────────────────────────────────────────────────────────────────────────────

def dicom_to_hu(dcm: pydicom.Dataset) -> np.ndarray:
    """Convert raw DICOM pixel values to Hounsfield Units."""
    img = dcm.pixel_array.astype(np.float32)

    # Handle MONOCHROME1 (inverted) photometric interpretation
    if hasattr(dcm, "PhotometricInterpretation"):
        if dcm.PhotometricInterpretation == "MONOCHROME1":
            img = img.max() - img

    # Note: pydicom's pixel_array automatically handles BitsStored and PixelRepresentation.
    # Manually masking bits here will corrupt signed (2's complement) values (e.g. air at -1024).

    # Apply rescale slope/intercept
    slope = float(getattr(dcm, "RescaleSlope", 1.0))
    intercept = float(getattr(dcm, "RescaleIntercept", 0.0))
    return img * slope + intercept


def apply_window(hu: np.ndarray, center: float, width: float) -> np.ndarray:
    """Apply CT windowing and normalize to [0, 1]."""
    low = center - width / 2.0
    high = center + width / 2.0
    return np.clip((hu - low) / (high - low), 0.0, 1.0)


def preprocess_slice(dicom_path: str | Path) -> np.ndarray:
    """
    Load a DICOM slice and return a 3-channel float32 image using
    multi-window approach: [brain, blood, subdural] → (H, W, 3).

    This is superior to adjacent-slice stacking for hemorrhage detection
    and matches top RSNA competition solutions.
    """
    dcm = pydicom.dcmread(str(dicom_path))
    hu = dicom_to_hu(dcm)

    channels = [
        apply_window(hu, center=WINDOWS["brain"][0],    width=WINDOWS["brain"][1]),
        apply_window(hu, center=WINDOWS["blood"][0],    width=WINDOWS["blood"][1]),
        apply_window(hu, center=WINDOWS["subdural"][0], width=WINDOWS["subdural"][1]),
    ]
    # (H, W, 3) float32
    return np.stack(channels, axis=-1).astype(np.float32)


def get_z_position(dcm: pydicom.Dataset) -> float:
    """Extract z-coordinate from ImagePositionPatient for slice ordering."""
    try:
        return float(dcm.ImagePositionPatient[2])
    except Exception:
        return 0.0


# ──────────────────────────────────────────────────────────────────────────────
# Label Parsing
# ──────────────────────────────────────────────────────────────────────────────

def parse_labels(csv_path: str | Path) -> pd.DataFrame:
    """
    Parse RSNA CSV into per-slice multi-label DataFrame.

    Input CSV columns: ID (e.g. "ID_000012eaf_epidural"), Label (0/1)
    Output DataFrame: index=SOPInstanceUID, columns=SUBTYPES
    """
    df = pd.read_csv(str(csv_path))

    # Split "ID_{sop}_{subtype}" into components
    df[["prefix", "sop_uid", "subtype"]] = df["ID"].str.split("_", n=2, expand=True)
    df["sop_uid"] = df["prefix"] + "_" + df["sop_uid"]
    df = df[df["subtype"].isin(SUBTYPES)]

    # Pivot to wide format: rows=sop_uid, cols=subtypes
    pivot = df.pivot_table(index="sop_uid", columns="subtype", values="Label", aggfunc="first")
    pivot = pivot.reindex(columns=SUBTYPES, fill_value=0)
    return pivot.reset_index()


# ──────────────────────────────────────────────────────────────────────────────
# Dataset Class
# ──────────────────────────────────────────────────────────────────────────────

class RSNADataset(Dataset):
    """
    PyTorch Dataset for RSNA Intracranial Hemorrhage Detection.

    Args:
        dicom_dir: Path to directory with .dcm files
        labels_df: DataFrame from parse_labels() — or None for test set
        img_size: Resize slices to (img_size, img_size)
        augment: Apply training augmentations
    """

    def __init__(
        self,
        dicom_dir: str | Path,
        labels_df: Optional[pd.DataFrame] = None,
        img_size: int = 512,
        augment: bool = False,
    ):
        self.dicom_dir = Path(dicom_dir)
        self.labels_df = labels_df
        self.img_size = img_size
        self.augment = augment

        # Build file index
        self.files = sorted(self.dicom_dir.glob("*.dcm"))
        if len(self.files) == 0:
            raise FileNotFoundError(f"No .dcm files found in {dicom_dir}")

        # Map sop_uid → file path
        self.uid_to_path: dict[str, Path] = {}
        for f in self.files:
            self.uid_to_path[f.stem] = f  # stem = filename without extension

        # Filter to labeled files if labels provided
        if labels_df is not None:
            labeled_uids = set(labels_df["sop_uid"].values)
            self.file_list = [
                (uid, self.uid_to_path[uid])
                for uid in labeled_uids
                if uid in self.uid_to_path
            ]
        else:
            self.file_list = [(f.stem, f) for f in self.files]

        # ImageNet-style normalization (since we use pretrained weights)
        self._normalize = transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        )
        self._resize = transforms.Resize(
            (img_size, img_size),
            interpolation=transforms.InterpolationMode.BILINEAR,
            antialias=True,
        )
        # Strong training augmentations — simulate real-world scanner variation
        # Order: spatial → intensity → noise → occlusion
        self._augment = transforms.Compose([
            # Spatial: different scan orientations / slight patient movement
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomVerticalFlip(p=0.15),
            transforms.RandomRotation(degrees=15),
            transforms.RandomAffine(
                degrees=0,
                translate=(0.05, 0.05),   # ±5% shift (patient not centred)
                scale=(0.90, 1.10),        # ±10% zoom (different FOV)
                shear=4,
            ),
            # Intensity: different scanner models / kVp / dose
            transforms.ColorJitter(brightness=0.20, contrast=0.20),
            transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 0.8)),
            # Noise: electronic noise in old scanners
            GaussianNoise(std=0.02),
            # Occlusion: metal artifacts / partial view
            transforms.RandomErasing(p=0.20, scale=(0.02, 0.08), ratio=(0.5, 2.0)),
        ]) if augment else None

    def __len__(self) -> int:
        return len(self.file_list)

    def __getitem__(self, idx: int):
        uid, path = self.file_list[idx]

        try:
            img = preprocess_slice(path)  # (H, W, 3) float32 in [0,1]
        except Exception:
            # Fallback: return blank slice if DICOM is corrupted
            img = np.zeros((self.img_size, self.img_size, 3), dtype=np.float32)

        # (H, W, 3) → (3, H, W) tensor
        tensor = torch.from_numpy(img).permute(2, 0, 1)
        tensor = self._resize(tensor)

        if self._augment is not None:
            tensor = self._augment(tensor)

        tensor = self._normalize(tensor)

        # Build label vector
        if self.labels_df is not None:
            row = self.labels_df[self.labels_df["sop_uid"] == uid]
            if len(row) > 0:
                label = torch.tensor(
                    row[SUBTYPES].values[0].astype(np.float32),
                    dtype=torch.float32,
                )
            else:
                label = torch.zeros(len(SUBTYPES), dtype=torch.float32)
            return tensor, label, uid
        else:
            return tensor, uid

    @staticmethod
    def collate_fn(batch):
        """Custom collate to handle variable-length uid strings.
        Supports both labeled (tensor, label, uid) and test (tensor, uid) batches.
        """
        if len(batch[0]) == 3:
            tensors, labels, uids = zip(*batch)
            return torch.stack(tensors), torch.stack(labels), list(uids)
        else:
            tensors, uids = zip(*batch)
            return torch.stack(tensors), list(uids)


# ──────────────────────────────────────────────────────────────────────────────
# Utility: Build 3D Volume from a Study
# ──────────────────────────────────────────────────────────────────────────────

def build_volume(dicom_paths: list[Path]) -> np.ndarray:
    """
    Stack multiple DICOM slices into a 3D volume sorted by z-position.

    Returns:
        volume: (D, H, W) float32 in Hounsfield Units
    """
    slices = []
    for p in dicom_paths:
        try:
            dcm = pydicom.dcmread(str(p))
            hu = dicom_to_hu(dcm)
            z = get_z_position(dcm)
            slices.append((z, hu))
        except Exception:
            continue

    if not slices:
        raise ValueError("No valid DICOM slices found.")

    slices.sort(key=lambda x: x[0])
    return np.stack([s[1] for s in slices], axis=0)  # (D, H, W)


def get_brain_mask(hu: np.ndarray) -> np.ndarray:
    """
    Compute a binary brain-only mask from a 2-D HU slice.

    Algorithm:
      1. Soft-tissue threshold: 0 < HU < 80  (brain parenchyma + hemorrhage)
      2. Find the connected component closest to the image center
         (avoids selecting scan table / pillow as "largest")
      3. Dilate to reclaim border pixels, then fill holes
         (ventricles, CSF cisterns become part of the mask)
      4. Final mask = brain interior without skull bone

    Returns:
        mask: bool ndarray same shape as `hu`
    """
    try:
        from scipy import ndimage as _ndi
    except ImportError:
        # No scipy → simple threshold fallback
        return (hu > -10) & (hu < 100)

    H, W = hu.shape
    cy, cx = H // 2, W // 2

    # Step 1 – soft tissue mask (brain ≈ 20-45 HU, blood ≈ 50-90 HU)
    tissue = (hu > 0) & (hu < 100)

    # Step 2 – connected components; pick the one nearest image center
    labeled, n_comp = _ndi.label(tissue)
    if n_comp == 0:
        return np.zeros_like(hu, dtype=bool)

    # For each component, compute centroid distance to image center
    centroids = _ndi.center_of_mass(tissue, labeled, range(1, n_comp + 1))
    best_label = 1
    best_dist = float("inf")
    sizes = np.bincount(labeled.ravel())
    min_size = H * W * 0.01  # ignore tiny components (<1% of image)
    for lbl_idx, (cy_c, cx_c) in enumerate(centroids, start=1):
        if sizes[lbl_idx] < min_size:
            continue
        dist = (cy_c - cy) ** 2 + (cx_c - cx) ** 2
        if dist < best_dist:
            best_dist = dist
            best_label = lbl_idx

    brain_mask = labeled == best_label

    # Step 3 – dilate to reclaim border voxels, then fill holes
    struct = _ndi.generate_binary_structure(2, 2)  # 8-connected
    brain_mask = _ndi.binary_dilation(brain_mask, structure=struct, iterations=5)
    brain_mask = _ndi.binary_fill_holes(brain_mask)
    # Slight erosion to trim bright rim remaining from the dilation
    brain_mask = _ndi.binary_erosion(brain_mask, structure=struct, iterations=2)

    return brain_mask


def strip_skull(hu: np.ndarray) -> np.ndarray:
    """
    Zero-out everything outside the brain parenchyma.
    Uses `get_brain_mask` for robust center-biased component selection.
    """
    mask = get_brain_mask(hu)
    hu_out = hu.copy()
    hu_out[~mask] = 0
    hu_out[hu_out < -10] = 0
    return hu_out


def get_volume_slice_tensor(
    volume_hu: np.ndarray,
    slice_idx: int,
    normalize: bool = True,
    skull_strip: bool = False,
    img_size: int = 224,
) -> torch.Tensor:
    """
    Extract a single slice from a volume and return preprocessed tensor.

    Args:
        volume_hu:   (D, H, W) HU volume
        slice_idx:   Slice index to extract
        normalize:   Apply ImageNet normalization (must match training config)
        skull_strip: Zero-out bone/air pixels so GradCAM focuses on brain tissue
        img_size:    Resize to (img_size × img_size) — must match training config

    Returns:
        tensor: (1, 3, img_size, img_size) float32 ready for model inference
    """
    hu = volume_hu[slice_idx]  # (H, W)
    if skull_strip:
        hu = strip_skull(hu)
    channels = [
        apply_window(hu, center=WINDOWS["brain"][0],    width=WINDOWS["brain"][1]),
        apply_window(hu, center=WINDOWS["blood"][0],    width=WINDOWS["blood"][1]),
        apply_window(hu, center=WINDOWS["subdural"][0], width=WINDOWS["subdural"][1]),
    ]
    img = np.stack(channels, axis=-1).astype(np.float32)  # (H, W, 3)
    tensor = torch.from_numpy(img).permute(2, 0, 1)  # (3, H, W)

    # Resize to match training resolution
    if tensor.shape[1] != img_size or tensor.shape[2] != img_size:
        resize = transforms.Resize(
            (img_size, img_size),
            interpolation=transforms.InterpolationMode.BILINEAR,
            antialias=True,
        )
        tensor = resize(tensor)

    if normalize:
        # ImageNet normalization (matches pretrained EfficientNet-B4 training)
        norm = transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        )
        tensor = norm(tensor)

    return tensor.unsqueeze(0)  # (1, 3, img_size, img_size)
