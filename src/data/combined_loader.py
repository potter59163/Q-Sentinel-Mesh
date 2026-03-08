"""
Combined Multi-Dataset Loader for CT Hemorrhage Detection

Merges three heterogeneous datasets into a single unified PyTorch Dataset:
  1. CT-ICH (PhysioNet NIfTI) — 75 patients, ~2814 slices, multi-label
  2. RSNA 12K (Kaggle PNGs)   — 5849 unique images, multi-label (folder-based)
  3. Afridi ICH (Kaggle JPGs)  — 2501 images, binary (hemorrhage/normal)

All outputs share a common label vector:
  [epidural, intraparenchymal, intraventricular, subarachnoid, subdural, any]
"""

from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset, ConcatDataset
from torchvision import transforms

# Label order — shared with nifti_loader.py and rsna_loader.py
SUBTYPES = [
    "epidural",
    "intraparenchymal",
    "intraventricular",
    "subarachnoid",
    "subdural",
    "any",
]

# Folder-name → label-index mapping for RSNA 12K dataset
_RSNA_FOLDER_MAP = {
    "Any":                 5,   # any
    "Epidural":            0,
    "Intraparenchymal":    1,
    "Intraventricular":    2,
    "Subarachnoid":        3,
    "Subdural":            4,
}


# ------------------------------------------------------------------------------
# RSNA 12K PNG Dataset
# ------------------------------------------------------------------------------

class RSNA12KDataset(Dataset):
    """
    Loads RSNA 12K PNG images with multi-label annotations derived from
    folder structure (e.g. Epidural_Positive, Subdural_Normal).

    Args:
        root_dir:   Path to RNSA_Subset_PNGs_12K/ folder
        img_size:   Resize to (img_size, img_size)
        augment:    Apply training augmentations
        normalize:  Apply ImageNet normalization
    """

    def __init__(
        self,
        root_dir: str | Path,
        img_size: int = 224,
        augment: bool = False,
        normalize: bool = True,
    ):
        self.img_size = img_size
        self.normalize = normalize
        root = Path(root_dir)

        # -- Scan all folders to build per-image multi-label --------------
        image_folders: dict[str, set] = defaultdict(set)
        for folder_name in sorted(os.listdir(root)):
            folder_path = root / folder_name
            if not folder_path.is_dir():
                continue
            # Parse folder: "Epidural_Positive" → subtype="Epidural", polarity="Positive"
            parts = folder_name.rsplit("_", 1)
            if len(parts) != 2 or parts[1] not in ("Normal", "Positive", "Positvie"):
                continue  # skip unknown folders
            for img_file in folder_path.iterdir():
                if img_file.suffix.lower() in (".png", ".jpg", ".jpeg"):
                    image_folders[img_file.name].add(folder_name)

        # -- Build label vectors ------------------------------------------
        self._paths: List[Path] = []
        self._labels: List[np.ndarray] = []

        for img_name, folders in sorted(image_folders.items()):
            label = np.zeros(6, dtype=np.float32)
            # Find any folder where this image appears as "Positive"
            img_path = None
            for folder_name in folders:
                parts = folder_name.rsplit("_", 1)
                subtype_name = parts[0]
                polarity = parts[1]
                if polarity in ("Positive", "Positvie"):  # handle typo in dataset
                    idx = _RSNA_FOLDER_MAP.get(subtype_name)
                    if idx is not None:
                        label[idx] = 1.0
                # Pick a valid path for reading (any folder will do)
                candidate = root / folder_name / img_name
                if candidate.exists():
                    img_path = candidate

            if img_path is None:
                continue

            # Ensure "any" is set if any subtype is positive
            if label[:5].max() > 0:
                label[5] = 1.0

            self._paths.append(img_path)
            self._labels.append(label)

        print(f"  RSNA12KDataset: {len(self._paths)} images "
              f"({int(sum(l[5] for l in self._labels))} positive)")

        # -- Transforms ---------------------------------------------------
        base_transforms = [
            transforms.Resize((img_size, img_size)),
            transforms.ToTensor(),
        ]
        if augment:
            aug_transforms = [
                transforms.RandomHorizontalFlip(0.5),
                transforms.RandomRotation(15),
                transforms.RandomAffine(0, translate=(0.06, 0.06), scale=(0.9, 1.1)),
                transforms.ColorJitter(brightness=0.15, contrast=0.15),
            ]
            base_transforms = base_transforms[:1] + aug_transforms + base_transforms[1:]

        if normalize:
            base_transforms.append(
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
            )
        self._transform = transforms.Compose(base_transforms)

    def __len__(self):
        return len(self._paths)

    def __getitem__(self, idx):
        img = Image.open(self._paths[idx]).convert("RGB")
        tensor = self._transform(img)
        label = torch.tensor(self._labels[idx], dtype=torch.float32)
        uid = self._paths[idx].stem
        return tensor, label, uid


# ------------------------------------------------------------------------------
# Afridi ICH Binary Dataset
# ------------------------------------------------------------------------------

class AfridiICHDataset(Dataset):
    """
    Loads Afridi ICH dataset images with binary labels.
    Folder structure: .../Train(or Test)/Hemorrhage/hemorrhage_images/
                      .../Train(or Test)/Normal/normal_images/

    Since this is binary, only "any" label is set for positive cases;
    all subtype labels remain 0 (conservative labeling).

    Args:
        root_dir:   Path to "intracranial brain hemorrhage dataset/Original/" folder
        split:      "Train" or "Test" or "all" (both)
        img_size:   Resize to (img_size, img_size)
        augment:    Apply training augmentations
        normalize:  Apply ImageNet normalization
    """

    def __init__(
        self,
        root_dir: str | Path,
        split: str = "all",
        img_size: int = 224,
        augment: bool = False,
        normalize: bool = True,
    ):
        self.img_size = img_size
        self.normalize = normalize
        root = Path(root_dir)

        self._paths: List[Path] = []
        self._labels: List[np.ndarray] = []

        splits = ["Train", "Test"] if split == "all" else [split]

        for sp in splits:
            # Hemorrhage images → any=1
            hem_dir = root / sp / "Hemorrhage" / "hemorrhage_images"
            if hem_dir.exists():
                for f in sorted(hem_dir.iterdir()):
                    if f.suffix.lower() in (".jpg", ".jpeg", ".png"):
                        label = np.zeros(6, dtype=np.float32)
                        label[5] = 1.0  # any=1
                        self._paths.append(f)
                        self._labels.append(label)

            # Normal images → all zeros
            norm_dir = root / sp / "Normal" / "normal_images"
            if norm_dir.exists():
                for f in sorted(norm_dir.iterdir()):
                    if f.suffix.lower() in (".jpg", ".jpeg", ".png"):
                        self._paths.append(f)
                        self._labels.append(np.zeros(6, dtype=np.float32))

        n_pos = int(sum(l[5] for l in self._labels))
        print(f"  AfridiICHDataset: {len(self._paths)} images "
              f"({n_pos} hemorrhage, {len(self._paths)-n_pos} normal)")

        # -- Transforms ---------------------------------------------------
        base_transforms = [
            transforms.Resize((img_size, img_size)),
            transforms.ToTensor(),
        ]
        if augment:
            aug_transforms = [
                transforms.RandomHorizontalFlip(0.5),
                transforms.RandomRotation(15),
                transforms.RandomAffine(0, translate=(0.06, 0.06), scale=(0.9, 1.1)),
                transforms.ColorJitter(brightness=0.15, contrast=0.15),
            ]
            base_transforms = base_transforms[:1] + aug_transforms + base_transforms[1:]

        if normalize:
            base_transforms.append(
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
            )
        self._transform = transforms.Compose(base_transforms)

    def __len__(self):
        return len(self._paths)

    def __getitem__(self, idx):
        img = Image.open(self._paths[idx]).convert("RGB")
        tensor = self._transform(img)
        label = torch.tensor(self._labels[idx], dtype=torch.float32)
        uid = f"afridi_{self._paths[idx].stem}"
        return tensor, label, uid


# ------------------------------------------------------------------------------
# Combined Builder
# ------------------------------------------------------------------------------

def build_combined_datasets(
    # CT-ICH paths
    nii_dir: str | Path,
    csv_path: str | Path,
    # RSNA 12K root
    rsna_12k_dir: Optional[str | Path] = None,
    # Afridi root
    afridi_dir: Optional[str | Path] = None,
    # Settings
    img_size: int = 224,
    val_ratio: float = 0.15,
    seed: int = 42,
) -> Tuple[Dataset, Dataset]:
    """
    Build combined train/val datasets from all available sources.

    Strategy:
      - CT-ICH: patient-level split (prevent data leakage)
      - RSNA 12K: random split (images are independent slices)
      - Afridi: random split (images are independent)

    Returns:
        (train_dataset, val_dataset) as ConcatDatasets
    """
    from src.data.nifti_loader import build_ich_datasets

    print("\n  -- Loading datasets --")

    train_parts: List[Dataset] = []
    val_parts: List[Dataset] = []

    # 1. CT-ICH (always included)
    ich_train, ich_val = build_ich_datasets(
        nii_dir=nii_dir,
        csv_path=csv_path,
        img_size=img_size,
        val_ratio=val_ratio,
        seed=seed,
    )
    train_parts.append(ich_train)
    val_parts.append(ich_val)

    # 2. RSNA 12K PNGs (if available)
    if rsna_12k_dir and Path(rsna_12k_dir).exists():
        full_rsna = RSNA12KDataset(
            root_dir=rsna_12k_dir,
            img_size=img_size,
            augment=False,  # will set per-split later
            normalize=True,
        )
        # Random split
        n = len(full_rsna)
        n_val = max(1, int(n * val_ratio))
        n_train = n - n_val
        rng = torch.Generator().manual_seed(seed)
        rsna_train, rsna_val = torch.utils.data.random_split(full_rsna, [n_train, n_val], generator=rng)

        # Wrap train split with augmentation
        rsna_train_aug = RSNA12KDataset(
            root_dir=rsna_12k_dir,
            img_size=img_size,
            augment=True,
            normalize=True,
        )
        # Use same indices as the split
        rsna_train_aug = torch.utils.data.Subset(rsna_train_aug, rsna_train.indices)

        train_parts.append(rsna_train_aug)
        val_parts.append(rsna_val)

    # 3. Afridi ICH (if available)
    if afridi_dir and Path(afridi_dir).exists():
        full_afridi = AfridiICHDataset(
            root_dir=afridi_dir,
            split="all",
            img_size=img_size,
            augment=False,
            normalize=True,
        )
        n = len(full_afridi)
        n_val = max(1, int(n * val_ratio))
        n_train = n - n_val
        rng = torch.Generator().manual_seed(seed + 1)
        afridi_train, afridi_val = torch.utils.data.random_split(full_afridi, [n_train, n_val], generator=rng)

        # Wrap train split with augmentation
        afridi_train_aug = AfridiICHDataset(
            root_dir=afridi_dir,
            split="all",
            img_size=img_size,
            augment=True,
            normalize=True,
        )
        afridi_train_aug = torch.utils.data.Subset(afridi_train_aug, afridi_train.indices)

        train_parts.append(afridi_train_aug)
        val_parts.append(afridi_val)

    # Merge
    if len(train_parts) == 1:
        train_ds = train_parts[0]
        val_ds = val_parts[0]
    else:
        train_ds = ConcatDataset(train_parts)
        val_ds = ConcatDataset(val_parts)

    print(f"\n  -- Combined totals --")
    print(f"  Train: {len(train_ds)} | Val: {len(val_ds)}")
    print(f"  Sources: {len(train_parts)} datasets\n")

    return train_ds, val_ds
