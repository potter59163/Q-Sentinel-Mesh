"""
train_high_acc.py — Q-Sentinel Mesh High-Accuracy Training

Techniques for maximum AUC on CT-ICH dataset:
  1. Strong augmentation  (Mixup + Random Erasing + Affine + ColorJitter)
  2. Progressive unfreezing (head → partial backbone → full backbone)
  3. OneCycleLR scheduler  (fast warmup + cosine decay)
  4. Early stopping        (patience = 7, watching val AUC)
  5. Label smoothing       (0.05 — reduces overconfidence)
  6. Larger dropout        (0.4 for small dataset)
  7. Threshold calibration (per-class optimal threshold on val set)

Expected improvement: 0.858 → 0.90+ AUC

Usage:
    python train_high_acc.py
"""

from __future__ import annotations

import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from sklearn.metrics import roc_auc_score
from tqdm import tqdm

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"\n{'='*60}")
print(f"  Q-Sentinel High-Accuracy Training")
print(f"  Device: {DEVICE.upper()}", end="")
if torch.cuda.is_available():
    print(f" ({torch.cuda.get_device_name(0)})", end="")
print(f"\n{'='*60}\n")

# ─── Dataset Paths ─────────────────────────────────────────────────────────────
DATASET_DIR = ROOT.parent / "computed-tomography-images-for-intracranial-hemorrhage-detection-and-segmentation-1.3.1"
NII_DIR  = DATASET_DIR / "ct_scans"
CSV_PATH = DATASET_DIR / "hemorrhage_diagnosis_raw_ct.csv"

WEIGHTS_DIR = ROOT / "weights"
DATA_DIR    = ROOT / "data"
WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

BEST_MODEL_PATH   = WEIGHTS_DIR / "high_acc_b4.pth"
THRESHOLDS_PATH   = DATA_DIR   / "optimal_thresholds.json"
HIGH_ACC_HIST     = DATA_DIR   / "high_acc_results.json"

# ─── Hyperparameters ───────────────────────────────────────────────────────────
IMG_SIZE   = 224
BATCH_SIZE = 8          # RTX 5060 — 1.7GB free VRAM
GRAD_ACCUM = 2          # effective batch = 16
USE_AMP    = True

# Progressive unfreezing schedule
PHASE1_EPOCHS = 6       # frozen backbone, train head only
PHASE2_EPOCHS = 8       # unfreeze last 2 blocks
PHASE3_EPOCHS = 6       # unfreeze ALL backbone (very low LR)
TOTAL_EPOCHS  = PHASE1_EPOCHS + PHASE2_EPOCHS + PHASE3_EPOCHS  # 20

EARLY_STOP_PATIENCE = 8  # stop if no AUC improvement for 8 epochs

LR_HEAD     = 3e-4    # head learning rate (Phase 1)
LR_BLOCKS   = 5e-5    # last 2 blocks LR (Phase 2)
LR_BACKBONE = 1e-5    # full backbone LR (Phase 3)

MIXUP_ALPHA  = 0.3    # Mixup interpolation alpha
LABEL_SMOOTH = 0.05   # label smoothing epsilon
DROPOUT      = 0.4    # larger dropout for small dataset

VAL_RATIO = 0.15


# ══════════════════════════════════════════════════════════════════════════════
# UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def mixup_batch(imgs: torch.Tensor, labels: torch.Tensor, alpha: float = 0.3):
    """Mixup: interpolate between two random samples in the batch."""
    if alpha <= 0:
        return imgs, labels
    lam = float(np.random.beta(alpha, alpha))
    idx = torch.randperm(imgs.size(0), device=imgs.device)
    mixed_imgs   = lam * imgs + (1 - lam) * imgs[idx]
    mixed_labels = lam * labels + (1 - lam) * labels[idx]
    return mixed_imgs, mixed_labels


def smooth_labels(labels: torch.Tensor, eps: float = 0.05) -> torch.Tensor:
    """Label smoothing: push hard 0/1 labels toward eps / 1-eps."""
    return labels * (1 - eps) + eps * 0.5


class FocalLossSmooth(nn.Module):
    """Focal Loss + Label Smoothing for multi-label binary classification."""
    def __init__(self, alpha: float = 0.25, gamma: float = 2.0, smooth: float = 0.05):
        super().__init__()
        self.alpha  = alpha
        self.gamma  = gamma
        self.smooth = smooth

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        # Apply label smoothing
        if self.smooth > 0:
            targets = smooth_labels(targets, self.smooth)
        bce     = F.binary_cross_entropy_with_logits(logits, targets, reduction="none")
        prob    = torch.sigmoid(logits)
        p_t     = targets * prob + (1 - targets) * (1 - prob)
        alpha_t = targets * self.alpha + (1 - targets) * (1 - self.alpha)
        focal_w = alpha_t * (1 - p_t) ** self.gamma
        return (focal_w * bce).mean()


def compute_auc(truths: np.ndarray, preds: np.ndarray) -> float:
    """Macro-average AUC over classes that have both positives and negatives."""
    aucs = []
    for c in range(truths.shape[1]):
        if len(np.unique(truths[:, c])) > 1:
            aucs.append(roc_auc_score(truths[:, c], preds[:, c]))
    return float(np.mean(aucs)) if aucs else 0.5


def find_optimal_thresholds(truths: np.ndarray, preds: np.ndarray) -> list:
    """
    Per-class threshold optimization using Youden's J statistic.
    Finds threshold that maximizes (sensitivity + specificity - 1).
    """
    thresholds = []
    for c in range(preds.shape[1]):
        y_true = truths[:, c]
        y_pred = preds[:, c]
        if len(np.unique(y_true)) < 2:
            thresholds.append(0.5)
            continue
        # Grid search over thresholds
        best_thr, best_j = 0.5, -1
        for thr in np.arange(0.05, 0.95, 0.02):
            preds_bin = (y_pred >= thr).astype(int)
            tp = ((preds_bin == 1) & (y_true == 1)).sum()
            tn = ((preds_bin == 0) & (y_true == 0)).sum()
            fp = ((preds_bin == 1) & (y_true == 0)).sum()
            fn = ((preds_bin == 0) & (y_true == 1)).sum()
            sens = tp / (tp + fn + 1e-8)
            spec = tn / (tn + fp + 1e-8)
            j = sens + spec - 1
            if j > best_j:
                best_j = j
                best_thr = thr
        thresholds.append(round(float(best_thr), 3))
    return thresholds


# ══════════════════════════════════════════════════════════════════════════════
# PHASE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def set_phase(model: nn.Module, phase: int):
    """
    Phase 1: Only head trainable
    Phase 2: Head + last 2 backbone blocks trainable
    Phase 3: Full model trainable (backbone LR = 1/10 head LR)
    """
    # First freeze everything
    for p in model.parameters():
        p.requires_grad = False

    if phase >= 1:
        # Always train head
        for p in model.head.parameters():
            p.requires_grad = True

    if phase >= 2:
        # Unfreeze last 2 blocks of EfficientNet-B4
        blocks = list(model.backbone.blocks.children())
        for block in blocks[-2:]:
            for p in block.parameters():
                p.requires_grad = True
        # Also unfreeze conv_head and bn2
        if hasattr(model.backbone, 'conv_head'):
            for p in model.backbone.conv_head.parameters():
                p.requires_grad = True
        if hasattr(model.backbone, 'bn2'):
            for p in model.backbone.bn2.parameters():
                p.requires_grad = True

    if phase >= 3:
        # Unfreeze ALL backbone
        for p in model.backbone.parameters():
            p.requires_grad = True

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  [Phase {phase}] Trainable params: {trainable:,}")
    return model


def make_optimizer(model: nn.Module, phase: int):
    """Create optimizer with different LRs per parameter group based on phase."""
    head_params = [p for p in model.head.parameters() if p.requires_grad]

    if phase == 1:
        param_groups = [{"params": head_params, "lr": LR_HEAD}]
    elif phase == 2:
        blocks = list(model.backbone.blocks.children())
        block_params = []
        for block in blocks[-2:]:
            block_params.extend([p for p in block.parameters() if p.requires_grad])
        for mod_name in ['conv_head', 'bn2']:
            if hasattr(model.backbone, mod_name):
                block_params.extend(
                    [p for p in getattr(model.backbone, mod_name).parameters() if p.requires_grad]
                )
        param_groups = [
            {"params": block_params, "lr": LR_BLOCKS},
            {"params": head_params,  "lr": LR_HEAD},
        ]
    else:  # phase 3
        backbone_params = [p for p in model.backbone.parameters() if p.requires_grad]
        param_groups = [
            {"params": backbone_params, "lr": LR_BACKBONE},
            {"params": head_params,     "lr": LR_HEAD * 0.1},
        ]

    return torch.optim.AdamW(param_groups, weight_decay=1e-4)


# ══════════════════════════════════════════════════════════════════════════════
# TRAINING LOOP
# ══════════════════════════════════════════════════════════════════════════════

def train_epoch(model, loader, optimizer, scaler, criterion, epoch_desc):
    model.train()
    total_loss = 0.0
    optimizer.zero_grad()

    for step, (imgs, labels, _) in enumerate(tqdm(loader, desc=epoch_desc, leave=False, ncols=72)):
        imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)

        # Mixup augmentation
        imgs, labels = mixup_batch(imgs, labels, MIXUP_ALPHA)

        with torch.amp.autocast(device_type=DEVICE, enabled=(USE_AMP and DEVICE == "cuda")):
            loss = criterion(model(imgs), labels) / GRAD_ACCUM
        scaler.scale(loss).backward()
        total_loss += loss.item() * GRAD_ACCUM

        if (step + 1) % GRAD_ACCUM == 0 or (step + 1) == len(loader):
            scaler.unscale_(optimizer)
            nn.utils.clip_grad_norm_(
                [p for p in model.parameters() if p.requires_grad], 1.0
            )
            scaler.step(optimizer)
            scaler.update()
            optimizer.zero_grad()

    return total_loss / len(loader)


@torch.no_grad()
def validate(model, loader):
    model.eval()
    preds, truths = [], []
    total_loss = 0.0
    criterion_eval = FocalLossSmooth(smooth=0.0)  # no smoothing at eval

    for imgs, labels, _ in loader:
        imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
        with torch.amp.autocast(device_type=DEVICE, enabled=(USE_AMP and DEVICE == "cuda")):
            logits = model(imgs)
        total_loss += criterion_eval(logits, labels).item()
        preds.append(torch.sigmoid(logits.float()).cpu().numpy())
        truths.append(labels.cpu().numpy())

    all_preds  = np.concatenate(preds)
    all_truths = np.concatenate(truths)
    auc = compute_auc(all_truths, all_preds)
    return total_loss / len(loader), auc, all_truths, all_preds


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    from src.data.nifti_loader import build_ich_datasets
    from src.models.cnn_encoder import build_efficientnet_b4

    # ── Build datasets ──────────────────────────────────────────────────────────
    # Use "strong" augmentation mode for training
    from src.data.nifti_loader import ICHDataset, get_patient_split

    train_patients, val_patients = get_patient_split(
        CSV_PATH, NII_DIR, val_ratio=VAL_RATIO, seed=42
    )

    train_set = ICHDataset(
        NII_DIR, CSV_PATH, img_size=IMG_SIZE,
        augment="strong",   # heavy augmentation
        normalize=True,
        patients=train_patients,
    )
    val_set = ICHDataset(
        NII_DIR, CSV_PATH, img_size=IMG_SIZE,
        augment=False,
        normalize=True,
        patients=val_patients,
    )

    print(f"  Train: {len(train_set)} slices | Val: {len(val_set)} slices")
    print(f"  Batch: {BATCH_SIZE} | GradAccum: {GRAD_ACCUM} | AMP: {USE_AMP}")
    print(f"  Plan: {PHASE1_EPOCHS}ep frozen → {PHASE2_EPOCHS}ep partial → {PHASE3_EPOCHS}ep full")

    train_loader = DataLoader(
        train_set, batch_size=BATCH_SIZE, shuffle=True,
        num_workers=0, pin_memory=False,
    )
    val_loader = DataLoader(
        val_set, batch_size=BATCH_SIZE * 2, shuffle=False,
        num_workers=0, pin_memory=False,
    )

    # ── Build model ─────────────────────────────────────────────────────────────
    model = build_efficientnet_b4(pretrained=True, dropout=DROPOUT, freeze_backbone=False)
    model.to(DEVICE)

    # Load previous best weights if available (warm start)
    prev_weights = WEIGHTS_DIR / "baseline_b4.pth"
    if prev_weights.exists():
        print(f"  Warm-start from existing baseline weights...")
        model.load_state_dict(torch.load(prev_weights, map_location=DEVICE))
        print(f"  Loaded: {prev_weights}")

    criterion = FocalLossSmooth(alpha=0.25, gamma=2.0, smooth=LABEL_SMOOTH)
    scaler    = torch.amp.GradScaler(device=DEVICE, enabled=(USE_AMP and DEVICE == "cuda"))

    history = {"train_loss": [], "val_loss": [], "val_auc": [], "phase": []}
    best_auc   = 0.0
    no_improve = 0
    best_truths, best_preds = None, None

    # ── Progressive training phases ─────────────────────────────────────────────
    phase_schedule = (
        [(1, e) for e in range(1, PHASE1_EPOCHS + 1)] +
        [(2, e) for e in range(1, PHASE2_EPOCHS + 1)] +
        [(3, e) for e in range(1, PHASE3_EPOCHS + 1)]
    )

    current_phase = 0
    optimizer = None

    for global_ep, (phase, local_ep) in enumerate(phase_schedule, start=1):
        t0 = time.time()

        # Switch phase → rebuild optimizer + scheduler
        if phase != current_phase:
            current_phase = phase
            model = set_phase(model, phase)
            optimizer = make_optimizer(model, phase)
            phase_total = [PHASE1_EPOCHS, PHASE2_EPOCHS, PHASE3_EPOCHS][phase - 1]
            scheduler = torch.optim.lr_scheduler.OneCycleLR(
                optimizer,
                max_lr=[g["lr"] for g in optimizer.param_groups],
                epochs=phase_total,
                steps_per_epoch=max(1, len(train_loader) // GRAD_ACCUM),
                pct_start=0.15,
                anneal_strategy="cos",
            )
            print(f"\n  ──── Phase {phase} started ────")

        # Train one epoch
        desc = f"  Ep {global_ep:2d}/{TOTAL_EPOCHS} Ph{phase} [train]"
        train_loss = train_epoch(model, train_loader, optimizer, scaler, criterion, desc)
        scheduler.step()

        # Validate
        val_loss, auc, all_truths, all_preds = validate(model, val_loader)
        elapsed = time.time() - t0

        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["val_auc"].append(auc)
        history["phase"].append(phase)

        print(
            f"  Epoch {global_ep:2d}/{TOTAL_EPOCHS}  "
            f"Ph{phase}  train={train_loss:.4f}  val={val_loss:.4f}  "
            f"AUC={auc:.4f}  ({elapsed:.0f}s)"
        )

        if auc > best_auc:
            best_auc = auc
            no_improve = 0
            best_truths, best_preds = all_truths, all_preds
            torch.save(model.state_dict(), BEST_MODEL_PATH)
            print(f"    ✅ New best AUC={best_auc:.4f} → saved")
        else:
            no_improve += 1
            print(f"    (no improvement {no_improve}/{EARLY_STOP_PATIENCE})")
            if no_improve >= EARLY_STOP_PATIENCE:
                print(f"  ⏹ Early stopping at epoch {global_ep} (patience {EARLY_STOP_PATIENCE})")
                break

    # ── Threshold calibration on val set ────────────────────────────────────────
    print("\n  Computing optimal per-class thresholds on validation set...")
    opt_thresholds = find_optimal_thresholds(best_truths, best_preds)
    SUBTYPES = ["epidural", "intraparenchymal", "intraventricular",
                "subarachnoid", "subdural", "any"]
    thr_dict = {k: v for k, v in zip(SUBTYPES, opt_thresholds)}
    with open(THRESHOLDS_PATH, "w") as f:
        json.dump(thr_dict, f, indent=2)

    print("  Per-class optimal thresholds:")
    for k, v in thr_dict.items():
        print(f"    {k:22s}: {v:.3f}")

    # ── Save results ─────────────────────────────────────────────────────────────
    results = {"history": history, "best_auc": best_auc, "optimal_thresholds": thr_dict}
    with open(HIGH_ACC_HIST, "w") as f:
        json.dump(results, f, indent=2)

    # Also update baseline_b4.pth so run_all.py / dashboard uses the better model
    import shutil
    shutil.copy(BEST_MODEL_PATH, WEIGHTS_DIR / "baseline_b4.pth")
    print(f"\n  ✅ Best model also copied to baseline_b4.pth for dashboard use")

    print(f"\n{'='*60}")
    print(f"  HIGH-ACCURACY TRAINING COMPLETE")
    print(f"  Best Val AUC: {best_auc:.4f}")
    print(f"  Weights: {BEST_MODEL_PATH}")
    print(f"  Thresholds: {THRESHOLDS_PATH}")
    print(f"{'='*60}\n")
    return best_auc


if __name__ == "__main__":
    main()
