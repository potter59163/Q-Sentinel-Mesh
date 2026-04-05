"""
Federated data loading utilities for real multi-machine runs.

Supports:
1. Mock synthetic CT data for local smoke testing
2. CT-ICH NIfTI + CSV with patient-level partitioning
3. RSNA-style DICOM + labels CSV

The goal is to keep the client/server scripts on the same preprocessing path as
the training code, while allowing each machine to point at its own local data.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import torch
from torch.utils.data import DataLoader, random_split

from src.data.mock_data import MockCTDataset


def _parse_patient_ids(raw: str | None) -> list[int]:
    if not raw:
        return []
    patient_ids: list[int] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        patient_ids.append(int(chunk))
    return patient_ids


def _split_patient_ids(patient_ids: list[int], node_id: int, num_nodes: int = 3) -> list[int]:
    sorted_ids = sorted(patient_ids)
    return sorted_ids[node_id::num_nodes]


def _load_manifest(manifest_path: str | Path | None) -> dict:
    if not manifest_path:
        return {}
    path = Path(manifest_path)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_client_dataloaders(
    *,
    node_id: int,
    batch_size: int,
    img_size: int,
    mock_samples: int,
    val_split: float = 0.2,
    seed: int = 42,
    data_source: str = "mock",
    manifest_path: str | Path | None = None,
    nii_dir: str | Path | None = None,
    csv_path: str | Path | None = None,
    dicom_dir: str | Path | None = None,
    labels_csv: str | Path | None = None,
    patient_ids: str | None = None,
    auto_partition: bool = False,
):
    """
    Build train/val loaders for one federated node.

    `data_source` values:
    - mock
    - ctich
    - rsna
    """
    manifest = _load_manifest(manifest_path)

    if manifest:
        data_source = manifest.get("source", data_source)
        nii_dir = manifest.get("nii_dir", nii_dir)
        csv_path = manifest.get("csv_path", csv_path)
        dicom_dir = manifest.get("dicom_dir", dicom_dir)
        labels_csv = manifest.get("labels_csv", labels_csv)
        patient_ids = manifest.get("patient_ids", patient_ids)
        auto_partition = bool(manifest.get("auto_partition", auto_partition))

    source = (data_source or "mock").strip().lower()

    if source == "ctich":
        if not nii_dir or not csv_path:
            raise ValueError("CT-ICH mode requires both --nii-dir and --csv-path (or a manifest).")

        from src.data.nifti_loader import ICHDataset, parse_ich_labels

        nii_dir_path = Path(nii_dir)
        csv_path_path = Path(csv_path)
        selected_patients = _parse_patient_ids(patient_ids if isinstance(patient_ids, str) else None)
        if not selected_patients and isinstance(patient_ids, list):
            selected_patients = [int(pid) for pid in patient_ids]

        if not selected_patients:
            labels_df = parse_ich_labels(csv_path_path)
            available = set()
            for nii_file in nii_dir_path.glob("*.nii"):
                try:
                    available.add(int(nii_file.stem))
                except ValueError:
                    continue
            all_patients = sorted(available.intersection(set(labels_df["patient_num"].unique())))
            if not all_patients:
                raise FileNotFoundError("No labeled CT-ICH patients found for the provided paths.")
            selected_patients = _split_patient_ids(all_patients, node_id=node_id, num_nodes=3) if auto_partition else all_patients

        if len(selected_patients) < 2:
            raise ValueError(
                f"Node {node_id} has only {len(selected_patients)} CT-ICH patient(s). "
                "Provide at least 2 patients so local train/val splits are possible."
            )

        rng = torch.Generator().manual_seed(seed + node_id)
        shuffled = torch.randperm(len(selected_patients), generator=rng).tolist()
        ordered_patients = [selected_patients[idx] for idx in shuffled]
        n_val_patients = max(1, int(round(len(ordered_patients) * val_split)))
        val_patients = ordered_patients[:n_val_patients]
        train_patients = ordered_patients[n_val_patients:]
        if not train_patients:
            train_patients, val_patients = ordered_patients[1:], ordered_patients[:1]

        train_ds = ICHDataset(
            nii_dir=nii_dir_path,
            csv_path=csv_path_path,
            img_size=img_size,
            augment=True,
            normalize=True,
            patients=train_patients,
        )
        val_ds = ICHDataset(
            nii_dir=nii_dir_path,
            csv_path=csv_path_path,
            img_size=img_size,
            augment=False,
            normalize=True,
            patients=val_patients,
        )

        dataset_info = {
            "source": "ctich",
            "train_examples": len(train_ds),
            "val_examples": len(val_ds),
            "train_patients": train_patients,
            "val_patients": val_patients,
        }

    elif source == "rsna":
        if not dicom_dir or not labels_csv:
            raise ValueError("RSNA mode requires both --dicom-dir and --labels-csv (or a manifest).")

        from src.data.rsna_loader import RSNADataset, parse_labels

        labels_df = parse_labels(labels_csv)
        rng = torch.Generator().manual_seed(seed + node_id)
        n_val = max(1, int(len(labels_df) * val_split))
        n_train = len(labels_df) - n_val
        train_idx, val_idx = random_split(range(len(labels_df)), [n_train, n_val], generator=rng)
        train_df = labels_df.iloc[list(train_idx)].reset_index(drop=True)
        val_df = labels_df.iloc[list(val_idx)].reset_index(drop=True)

        train_ds = RSNADataset(dicom_dir, train_df, img_size=img_size, augment=True)
        val_ds = RSNADataset(dicom_dir, val_df, img_size=img_size, augment=False)
        dataset_info = {
            "source": "rsna",
            "train_examples": len(train_ds),
            "val_examples": len(val_ds),
        }

    else:
        dataset = MockCTDataset(n_samples=mock_samples, img_size=img_size, seed=node_id * 100 + seed)
        n_train = max(1, int((1.0 - val_split) * len(dataset)))
        n_val = len(dataset) - n_train
        if n_val == 0:
            n_train, n_val = len(dataset) - 1, 1
        train_ds, val_ds = random_split(
            dataset,
            [n_train, n_val],
            generator=torch.Generator().manual_seed(seed + node_id),
        )
        dataset_info = {
            "source": "mock",
            "train_examples": len(train_ds),
            "val_examples": len(val_ds),
        }

    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        num_workers=0,
        pin_memory=torch.cuda.is_available(),
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
        pin_memory=torch.cuda.is_available(),
    )
    return train_loader, val_loader, dataset_info
