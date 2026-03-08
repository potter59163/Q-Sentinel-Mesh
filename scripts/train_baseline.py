"""
train_baseline.py — EfficientNet-B4 Baseline Training

Usage:
    python notebooks/train_baseline.py

Trains on RSNA dataset (or mock data if unavailable).
Saves weights to: weights/baseline_b4.pth
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split
from tqdm import tqdm
import numpy as np
from sklearn.metrics import roc_auc_score

from src.models.cnn_encoder import build_efficientnet_b4, FocalLoss, get_optimizer_and_scheduler
from src.data.rsna_loader import RSNADataset, parse_labels, SUBTYPES
from src.data.mock_data import build_mock_dataset

# ─── Config ───────────────────────────────────────────────────────────────────
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
EPOCHS = 10
BATCH_SIZE = 16
IMG_SIZE = 512
VAL_SPLIT = 0.15
LR = 1e-4

DATA_DIR  = Path("data/raw/stage_2_train")
LABELS_CSV = Path("data/raw/stage_2_train.csv")
WEIGHTS_OUT = Path("weights/baseline_b4.pth")
RESULTS_OUT = Path("data/baseline_results.json")

print(f"Device: {DEVICE}")
print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")


# ─── Dataset ──────────────────────────────────────────────────────────────────
if DATA_DIR.exists() and LABELS_CSV.exists():
    print(f"Loading RSNA dataset from {DATA_DIR}...")
    labels_df = parse_labels(LABELS_CSV)
    dataset = RSNADataset(
        dicom_dir=DATA_DIR,
        labels_df=labels_df,
        img_size=IMG_SIZE,
        augment=False,  # will set True for train split below
    )
    print(f"Dataset size: {len(dataset)} slices")
else:
    print("RSNA data not found — using mock dataset.")
    dataset = build_mock_dataset(n_samples=2000, img_size=256)

# Train/Val split
n_val = int(len(dataset) * VAL_SPLIT)
n_train = len(dataset) - n_val
train_set, val_set = random_split(
    dataset,
    [n_train, n_val],
    generator=torch.Generator().manual_seed(42),
)

train_loader = DataLoader(
    train_set, batch_size=BATCH_SIZE, shuffle=True,
    num_workers=4, pin_memory=True,
)
val_loader = DataLoader(
    val_set, batch_size=BATCH_SIZE, shuffle=False,
    num_workers=4, pin_memory=True,
)
print(f"Train: {n_train} | Val: {n_val}")


# ─── Model ────────────────────────────────────────────────────────────────────
model = build_efficientnet_b4(pretrained=True, freeze_backbone=True)
model.to(DEVICE)
print(f"Model params: {sum(p.numel() for p in model.parameters() if p.requires_grad):,}")

criterion = FocalLoss(alpha=0.25, gamma=2.0)
optimizer, scheduler = get_optimizer_and_scheduler(
    model, lr=LR, epochs=EPOCHS, steps_per_epoch=len(train_loader)
)

# ─── Training Loop ────────────────────────────────────────────────────────────
history = {"train_loss": [], "val_loss": [], "val_auc": []}
best_auc = 0.0

for epoch in range(EPOCHS):
    # ── Train ─────────────────────────────────────────────────────────────────
    model.train()
    train_loss = 0.0
    pbar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{EPOCHS} [Train]", leave=False)

    for batch in pbar:
        imgs, labels = batch[0], batch[1]
        imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)

        optimizer.zero_grad()
        logits = model(imgs)
        loss = criterion(logits, labels)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        scheduler.step()

        train_loss += loss.item()
        pbar.set_postfix(loss=f"{loss.item():.4f}")

    avg_train_loss = train_loss / len(train_loader)

    # ── Validate ──────────────────────────────────────────────────────────────
    model.eval()
    val_loss = 0.0
    all_preds, all_labels = [], []

    with torch.no_grad():
        for batch in tqdm(val_loader, desc=f"Epoch {epoch+1}/{EPOCHS} [Val]", leave=False):
            imgs, labels = batch[0], batch[1]
            imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)

            logits = model(imgs)
            loss = criterion(logits, labels)
            probs = torch.sigmoid(logits)

            val_loss += loss.item()
            all_preds.append(probs.cpu().numpy())
            all_labels.append(labels.cpu().numpy())

    avg_val_loss = val_loss / len(val_loader)

    try:
        all_preds_np = np.concatenate(all_preds, axis=0)
        all_labels_np = np.concatenate(all_labels, axis=0)
        val_auc = roc_auc_score(all_labels_np[:, -1], all_preds_np[:, -1])
    except Exception:
        val_auc = 0.5

    history["train_loss"].append(avg_train_loss)
    history["val_loss"].append(avg_val_loss)
    history["val_auc"].append(val_auc)

    print(
        f"Epoch {epoch+1:2d}/{EPOCHS}  |  "
        f"Train Loss: {avg_train_loss:.4f}  |  "
        f"Val Loss: {avg_val_loss:.4f}  |  "
        f"Val AUC: {val_auc:.4f}"
    )

    # ── Save best ─────────────────────────────────────────────────────────────
    if val_auc > best_auc:
        best_auc = val_auc
        WEIGHTS_OUT.parent.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), WEIGHTS_OUT)
        print(f"  ✅ Saved best model (AUC: {best_auc:.4f}) → {WEIGHTS_OUT}")

# ─── Save Results ─────────────────────────────────────────────────────────────
RESULTS_OUT.parent.mkdir(parents=True, exist_ok=True)
with open(RESULTS_OUT, "w") as f:
    json.dump({"history": history, "best_auc": best_auc}, f, indent=2)

print(f"\nTraining complete. Best AUC: {best_auc:.4f}")
print(f"Weights: {WEIGHTS_OUT}")
print(f"Results: {RESULTS_OUT}")
