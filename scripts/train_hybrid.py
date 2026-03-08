"""
train_hybrid.py — Q-Sentinel Hybrid Quantum-Classical Training

Loads pretrained CNN baseline weights, then fine-tunes the full
Hybrid Q-Sentinel model (CNN + VQC).

Usage:
    python notebooks/train_hybrid.py

Requires: weights/baseline_b4.pth (run train_baseline.py first)
Saves: weights/hybrid_qsentinel.pth
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

from src.models.hybrid_model import build_hybrid_model
from src.models.cnn_encoder import FocalLoss
from src.data.rsna_loader import RSNADataset, parse_labels
from src.data.mock_data import build_mock_dataset

# ─── Config ───────────────────────────────────────────────────────────────────
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
EPOCHS = 5            # Fine-tune quantum layer on top of pretrained CNN
BATCH_SIZE = 8        # Smaller batch: VQC is slower than pure CNN
IMG_SIZE = 512
VAL_SPLIT = 0.15
LR = 5e-5             # Lower LR for fine-tuning

BASELINE_WEIGHTS = Path("weights/baseline_b4.pth")
HYBRID_WEIGHTS   = Path("weights/hybrid_qsentinel.pth")
RESULTS_OUT      = Path("data/hybrid_results.json")

DATA_DIR   = Path("data/raw/stage_2_train")
LABELS_CSV = Path("data/raw/stage_2_train.csv")

print(f"Device: {DEVICE}")
print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")


# ─── Dataset ──────────────────────────────────────────────────────────────────
if DATA_DIR.exists() and LABELS_CSV.exists():
    print("Loading RSNA dataset...")
    labels_df = parse_labels(LABELS_CSV)
    dataset = RSNADataset(DATA_DIR, labels_df, img_size=IMG_SIZE)
else:
    print("Using mock dataset.")
    dataset = build_mock_dataset(n_samples=1000, img_size=256)

n_val = int(len(dataset) * VAL_SPLIT)
n_train = len(dataset) - n_val
train_set, val_set = random_split(
    dataset, [n_train, n_val],
    generator=torch.Generator().manual_seed(42),
)

train_loader = DataLoader(train_set, batch_size=BATCH_SIZE, shuffle=True, num_workers=2)
val_loader   = DataLoader(val_set,   batch_size=BATCH_SIZE, shuffle=False, num_workers=2)
print(f"Train: {n_train} | Val: {n_val}")


# ─── Model: Load pretrained CNN backbone into Hybrid ──────────────────────────
model = build_hybrid_model(pretrained=False, freeze_blocks=6)

if BASELINE_WEIGHTS.exists():
    print(f"Loading pretrained CNN backbone from {BASELINE_WEIGHTS}...")
    state_dict = torch.load(BASELINE_WEIGHTS, map_location=DEVICE)
    # Filter to backbone weights only (head weights shape won't match)
    backbone_state = {
        k.replace("backbone.", ""): v
        for k, v in state_dict.items()
        if k.startswith("backbone.")
    }
    missing, unexpected = model.backbone.load_state_dict(backbone_state, strict=False)
    print(f"  Loaded backbone. Missing: {len(missing)}, Unexpected: {len(unexpected)}")
else:
    print("No baseline weights found — training from scratch.")

model.to(DEVICE)

# Only train VQC module + head (backbone frozen by freeze_blocks)
trainable_params = [p for p in model.parameters() if p.requires_grad]
print(f"Trainable params: {sum(p.numel() for p in trainable_params):,}")

criterion = FocalLoss(alpha=0.25, gamma=2.0)
optimizer = torch.optim.AdamW(trainable_params, lr=LR, weight_decay=1e-5)
scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)


# ─── Training Loop ────────────────────────────────────────────────────────────
history = {"train_loss": [], "val_loss": [], "val_auc": []}
best_auc = 0.0

for epoch in range(EPOCHS):
    # Train
    model.train()
    train_loss = 0.0

    for batch in tqdm(train_loader, desc=f"Epoch {epoch+1}/{EPOCHS} [Train]", leave=False):
        imgs, labels = batch[0], batch[1]
        imgs = imgs.to(DEVICE)
        labels = labels.to(DEVICE)

        optimizer.zero_grad()
        logits = model(imgs)
        loss = criterion(logits, labels)
        loss.backward()
        nn.utils.clip_grad_norm_(trainable_params, max_norm=1.0)
        optimizer.step()
        train_loss += loss.item()

    scheduler.step()
    avg_train_loss = train_loss / len(train_loader)

    # Validate
    model.eval()
    val_loss = 0.0
    all_preds, all_labels = [], []

    with torch.no_grad():
        for batch in tqdm(val_loader, desc=f"Epoch {epoch+1}/{EPOCHS} [Val]", leave=False):
            imgs, labels = batch[0], batch[1]
            imgs = imgs.to(DEVICE)
            labels = labels.to(DEVICE)

            logits = model(imgs)
            loss = criterion(logits, labels)
            probs = torch.sigmoid(logits)

            val_loss += loss.item()
            all_preds.append(probs.cpu().numpy())
            all_labels.append(labels.cpu().numpy())

    avg_val_loss = val_loss / len(val_loader)

    try:
        val_auc = roc_auc_score(
            np.concatenate(all_labels)[:, -1],
            np.concatenate(all_preds)[:, -1],
        )
    except Exception:
        val_auc = 0.5

    history["train_loss"].append(avg_train_loss)
    history["val_loss"].append(avg_val_loss)
    history["val_auc"].append(val_auc)

    print(
        f"Epoch {epoch+1:2d}/{EPOCHS}  |  "
        f"Train: {avg_train_loss:.4f}  |  "
        f"Val: {avg_val_loss:.4f}  |  "
        f"AUC: {val_auc:.4f}"
    )

    if val_auc > best_auc:
        best_auc = val_auc
        HYBRID_WEIGHTS.parent.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), HYBRID_WEIGHTS)
        print(f"  ✅ Saved best hybrid model (AUC: {best_auc:.4f})")


# ─── Save Results ─────────────────────────────────────────────────────────────
with open(RESULTS_OUT, "w") as f:
    json.dump({"history": history, "best_auc": best_auc}, f, indent=2)

print(f"\n{'='*50}")
print(f"Hybrid training complete.")
print(f"Best AUC: {best_auc:.4f}")
print(f"Weights:  {HYBRID_WEIGHTS}")
