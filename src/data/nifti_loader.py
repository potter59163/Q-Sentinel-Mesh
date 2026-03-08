"""
CT-ICH NIfTI Data Loader

Loads the real CT-ICH dataset (PhysioNet):
  - 75 patients (NIfTI .nii files, ~2814 slices total)
  - Labels from hemorrhage_diagnosis_raw_ct.csv
  - Subtypes: epidural, intraparenchymal, intraventricular, subarachnoid, subdural, any

Compatible label order with RSNA / Q-Sentinel model:
  [epidural, intraparenchymal, intraventricular, subarachnoid, subdural, any]
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, List, Tuple

import nibabel as nib
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset
from torchvision import transforms

# ─── Label order (matches RSNA / cnn_encoder.py SUBTYPES) ────────────────────
SUBTYPES = [
    "epidural",
    "intraparenchymal",
    "intraventricular",
    "subarachnoid",
    "subdural",
    "any",
]

# Mapping: CT-ICH CSV column → RSNA SUBTYPES index
_CSV_COL_TO_IDX = {
    "Epidural":          0,
    "Intraparenchymal":  1,
    "Intraventricular":  2,
    "Subarachnoid":      3,
    "Subdural":          4,
    # "any" (index 5) = 1 - No_Hemorrhage
}

# CT Window presets (center, width)  — same as rsna_loader.py
WINDOWS = {
    "brain":    (40,  80),
    "blood":    (60,  120),
    "subdural": (75,  215),
}


# ──────────────────────────────────────────────────────────────────────────────
# NIfTI Processing
# ──────────────────────────────────────────────────────────────────────────────

def load_nifti_volume(nii_path: str | Path) -> np.ndarray:
    """
    Load a NIfTI CT scan and return (D, H, W) float32 in Hounsfield Units.
    The CT-ICH scans are already in HU-like range (no RescaleSlope needed).
    """
    img = nib.load(str(nii_path))
    data = img.get_fdata(dtype=np.float32)  # (H, W, D) or (H, W, D, T)

    # Handle 4D (some scanners add a time dim)
    if data.ndim == 4:
        data = data[..., 0]

    # NIfTI axes are (H, W, D) → reorder to (D, H, W)
    data = np.transpose(data, (2, 0, 1))
    return data


def apply_window(hu: np.ndarray, center: float, width: float) -> np.ndarray:
    """Apply CT windowing and normalize to [0, 1]."""
    low = center - width / 2.0
    high = center + width / 2.0
    return np.clip((hu - low) / (high - low), 0.0, 1.0)


def hu_slice_to_tensor(
    hu: np.ndarray,
    img_size: int = 224,
    normalize: bool = True,
) -> torch.Tensor:
    """
    Convert a single HU slice (H, W) to a 3-channel tensor using multi-window.

    Returns:
        tensor: (3, img_size, img_size) float32
    """
    channels = [
        apply_window(hu, center=WINDOWS["brain"][0],    width=WINDOWS["brain"][1]),
        apply_window(hu, center=WINDOWS["blood"][0],    width=WINDOWS["blood"][1]),
        apply_window(hu, center=WINDOWS["subdural"][0], width=WINDOWS["subdural"][1]),
    ]
    img = np.stack(channels, axis=-1).astype(np.float32)   # (H, W, 3)
    tensor = torch.from_numpy(img).permute(2, 0, 1)         # (3, H, W)

    # Resize
    resize = transforms.Resize(
        (img_size, img_size),
        interpolation=transforms.InterpolationMode.BILINEAR,
        antialias=True,
    )
    tensor = resize(tensor)

    # ImageNet normalization (matches pretrained EfficientNet-B4)
    if normalize:
        norm = transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        )
        tensor = norm(tensor)

    return tensor


# ──────────────────────────────────────────────────────────────────────────────
# Label Parsing
# ──────────────────────────────────────────────────────────────────────────────

def parse_ich_labels(csv_path: str | Path) -> pd.DataFrame:
    """
    Parse hemorrhage_diagnosis_raw_ct.csv into a per-slice label DataFrame.

    Returns DataFrame with columns:
        patient_num (int), slice_num (int),
        epidural, intraparenchymal, intraventricular, subarachnoid, subdural, any
    """
    df = pd.read_csv(str(csv_path))

    # Normalize BOM-prefixed column name
    df.columns = [c.lstrip('\ufeff').strip() for c in df.columns]

    # Compute 'any' = 1 if No_Hemorrhage == 0
    df["any"] = (df["No_Hemorrhage"] == 0).astype(int)

    # Rename to RSNA subtypes
    rename = {
        "Epidural":          "epidural",
        "Intraparenchymal":  "intraparenchymal",
        "Intraventricular":  "intraventricular",
        "Subarachnoid":      "subarachnoid",
        "Subdural":          "subdural",
        "PatientNumber":     "patient_num",
        "SliceNumber":       "slice_num",
    }
    df = df.rename(columns=rename)

    # Select and type-cast
    cols = ["patient_num", "slice_num"] + SUBTYPES
    df = df[cols].copy()
    df["patient_num"] = df["patient_num"].astype(int)
    df["slice_num"] = df["slice_num"].astype(int)
    for c in SUBTYPES:
        df[c] = df[c].astype(float)

    return df.reset_index(drop=True)


# ──────────────────────────────────────────────────────────────────────────────
# Dataset
# ──────────────────────────────────────────────────────────────────────────────

class ICHDataset(Dataset):
    """
    PyTorch Dataset for the CT-ICH NIfTI dataset.

    Pre-caches all processed tensors at init time for fast __getitem__.
    Each item is one CT slice with multi-label hemorrhage annotations.

    Args:
        nii_dir:     Path to folder with .nii files (named e.g. 049.nii)
        csv_path:    Path to hemorrhage_diagnosis_raw_ct.csv
        img_size:    Resize slices to (img_size x img_size)
        augment:     Apply training augmentations
        normalize:   Apply ImageNet normalization
        patients:    Optional list of patient numbers to include (for splitting)
    """

    # ImageNet normalization constants
    _MEAN = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
    _STD  = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)

    def __init__(
        self,
        nii_dir: str | Path,
        csv_path: str | Path,
        img_size: int = 224,
        augment: bool = False,
        normalize: bool = True,
        patients: Optional[List[int]] = None,
    ):
        self.nii_dir  = Path(nii_dir)
        self.img_size = img_size
        self.normalize = normalize
        self.augment   = augment

        # Parse labels
        labels_df = parse_ich_labels(csv_path)

        # Find available NIfTI files
        available = set()
        for f in self.nii_dir.glob("*.nii"):
            try:
                available.add(int(f.stem))
            except ValueError:
                pass

        if patients is not None:
            available = available.intersection(set(patients))

        # Pre-process ALL slices into float16 tensors (3, H, W) at init time.
        # This avoids repeated resize operations during training.
        _resize = transforms.Resize(
            (img_size, img_size),
            interpolation=transforms.InterpolationMode.BILINEAR,
            antialias=True,
        )

        self._tensors: List[torch.Tensor]  = []   # float16 (3, H, W) — no norm yet
        self._labels:  List[np.ndarray]    = []
        self._uids:    List[str]            = []
        n_patients = 0

        for pnum in sorted(available):
            patient_rows = labels_df[labels_df["patient_num"] == pnum]
            if patient_rows.empty:
                continue

            nii_path = self.nii_dir / f"{pnum:03d}.nii"
            try:
                vol = load_nifti_volume(nii_path)   # (D, H, W)
            except Exception as e:
                print(f"  Warning: could not load {nii_path}: {e}")
                continue

            n_patients += 1
            n_slices = vol.shape[0]

            for _, row in patient_rows.iterrows():
                s = int(row["slice_num"]) - 1   # 1-indexed → 0-indexed
                if not (0 <= s < n_slices):
                    continue

                hu = vol[s]   # (H, W) float32
                channels = [
                    apply_window(hu, WINDOWS["brain"][0],    WINDOWS["brain"][1]),
                    apply_window(hu, WINDOWS["blood"][0],    WINDOWS["blood"][1]),
                    apply_window(hu, WINDOWS["subdural"][0], WINDOWS["subdural"][1]),
                ]
                img = np.stack(channels, axis=-1).astype(np.float32)  # (H, W, 3)
                t   = torch.from_numpy(img).permute(2, 0, 1)           # (3, H, W)
                t   = _resize(t)                                        # (3, img_size, img_size)
                t   = t.half()                                          # float16 to save RAM

                self._tensors.append(t)
                self._labels.append(row[SUBTYPES].values.astype(np.float32))
                self._uids.append(f"p{pnum:03d}_s{s:03d}")

        print(f"  ICHDataset: {len(self._tensors)} slices from {n_patients} patients")

        # Augmentations (applied to already-resized tensors → very fast)
        # "strong" mode = heavy augmentation for max accuracy training
        if augment == "strong" or augment is True:
            self._augment_fn = transforms.Compose([
                transforms.RandomHorizontalFlip(p=0.5),
                transforms.RandomVerticalFlip(p=0.25),
                transforms.RandomRotation(degrees=15),
                transforms.RandomAffine(
                    degrees=0,
                    translate=(0.06, 0.06),
                    scale=(0.88, 1.12),
                    shear=5,
                ),
                transforms.ColorJitter(brightness=0.20, contrast=0.20),
                transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 0.8)),
                transforms.RandomErasing(p=0.25, scale=(0.02, 0.10), ratio=(0.5, 2.0)),
            ])
        elif augment == "light":
            self._augment_fn = transforms.Compose([
                transforms.RandomHorizontalFlip(),
                transforms.RandomRotation(10),
            ])
        else:
            self._augment_fn = None

    def __len__(self) -> int:
        return len(self._tensors)

    def __getitem__(self, idx: int):
        # float16 → float32 (very fast)
        tensor = self._tensors[idx].float()

        if self._augment_fn is not None:
            tensor = self._augment_fn(tensor)

        if self.normalize:
            tensor = (tensor - self._MEAN) / self._STD

        label = torch.tensor(self._labels[idx], dtype=torch.float32)
        return tensor, label, self._uids[idx]

    @staticmethod
    def collate_fn(batch):
        tensors, labels, uids = zip(*batch)
        return torch.stack(tensors), torch.stack(labels), list(uids)


def get_patient_split(
    csv_path: str | Path,
    nii_dir: str | Path,
    val_ratio: float = 0.15,
    seed: int = 42,
) -> Tuple[List[int], List[int]]:
    """
    Split patients into train/val sets (patient-level split to prevent leakage).

    Returns:
        train_patients, val_patients (lists of patient numbers)
    """
    labels_df = parse_ich_labels(csv_path)
    available = set()
    for f in Path(nii_dir).glob("*.nii"):
        try:
            available.add(int(Path(f).stem))
        except ValueError:
            pass

    patients = sorted(available.intersection(set(labels_df["patient_num"].unique())))
    rng = np.random.default_rng(seed)
    rng.shuffle(patients)

    n_val = max(1, int(len(patients) * val_ratio))
    val_patients = patients[:n_val]
    train_patients = patients[n_val:]

    return train_patients, val_patients


def build_ich_datasets(
    nii_dir: str | Path,
    csv_path: str | Path,
    img_size: int = 224,
    val_ratio: float = 0.15,
    seed: int = 42,
) -> Tuple["ICHDataset", "ICHDataset"]:
    """
    Build train and validation ICHDatasets with patient-level split.

    Returns:
        train_dataset, val_dataset
    """
    train_patients, val_patients = get_patient_split(
        csv_path, nii_dir, val_ratio=val_ratio, seed=seed
    )

    train_ds = ICHDataset(
        nii_dir=nii_dir,
        csv_path=csv_path,
        img_size=img_size,
        augment=True,
        normalize=True,
        patients=train_patients,
    )
    val_ds = ICHDataset(
        nii_dir=nii_dir,
        csv_path=csv_path,
        img_size=img_size,
        augment=False,
        normalize=True,
        patients=val_patients,
    )

    return train_ds, val_ds
