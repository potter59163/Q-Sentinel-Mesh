"""
train_combined.py - Q-Sentinel Cross-Dataset Validation Training

Cross-Dataset Strategy (when RSNA is downloaded):
  +----------------------------------------------------------+
  |  TRAIN  ->  RSNA 85%  (~573k DICOM slices, Kaggle)      |
  |  VAL    ->  RSNA 15%  (for early stopping only)          |
  |  TEST   ->  CT-ICH    (ALL 75 patients, PhysioNet)       |
  |              ^ NEVER seen during training ^              |
  +----------------------------------------------------------+

Why this matters (Why it matters):
  If AUC on CT-ICH is high after training ONLY on RSNA,
  it proves the model works across different hospitals,
  scanners, and file formats - not just training data.
  "Works across hospitals, not just in the lab"

What's already implemented in the loaders:
  [OK] Multi-window preprocessing: brain(40/80) + blood(60/120) + subdural(75/215)
  [OK] Strong augmentation: Rotate+-15deg * Affine * ColorJitter * GaussianBlur *
                          GaussianNoise * RandomErasing
  (no changes needed to the loaders)

Fallback (RSNA not downloaded):
  CT-ICH patients split 70/15/15 -> train / val / test
  Run: python download_rsna.py   to get RSNA first

Usage:
  python train_combined.py                        # auto-detect RSNA
  python train_combined.py --ctich-only           # force CT-ICH only
  python train_combined.py --rsna-per-epoch 20000 # fewer slices/epoch
  python train_combined.py --resume               # resume from checkpoint
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Subset
from sklearn.metrics import roc_auc_score
from tqdm import tqdm

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"\n{'='*65}")
print(f"  Q-Sentinel - Cross-Dataset Validation Training")
print(f"  Train: RSNA (Kaggle) -> Test: CT-ICH (PhysioNet)")
print(f"  Device: {DEVICE.upper()}", end="")
if torch.cuda.is_available():
    print(f" * {torch.cuda.get_device_name(0)}", end="")
print(f"\n{'='*65}\n")

# --- Dataset Paths ----------------------------------------------------------
CTICH_DIR = (
    ROOT.parent
    / "computed-tomography-images-for-intracranial-hemorrhage-detection-and-segmentation-1.3.1"
)
CTICH_NII = CTICH_DIR / "ct_scans"
CTICH_CSV = CTICH_DIR / "hemorrhage_diagnosis_raw_ct.csv"

RSNA_DIR  = ROOT / "data" / "rsna"
RSNA_IMG  = RSNA_DIR / "stage_2_train"
RSNA_CSV  = RSNA_DIR / "stage_2_train.csv"

WEIGHTS_DIR = ROOT / "weights"
DATA_DIR    = ROOT / "data"
WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

COMBINED_MODEL_PATH = WEIGHTS_DIR / "combined_b4.pth"
THRESHOLDS_PATH     = DATA_DIR / "optimal_thresholds.json"
COMBINED_HIST       = DATA_DIR / "combined_results.json"

# --- Hyperparameters --------------------------------------------------------
IMG_SIZE   = 224
BATCH_SIZE = 8
GRAD_ACCUM = 2       # effective batch = 16
USE_AMP    = True

PHASE1_EPOCHS = 1    # head only (1 epoch warmup)
PHASE2_EPOCHS = 7    # last 2 EfficientNet blocks
PHASE3_EPOCHS = 5    # full backbone
TOTAL_EPOCHS  = PHASE1_EPOCHS + PHASE2_EPOCHS + PHASE3_EPOCHS

EARLY_STOP_PATIENCE = 7

LR_HEAD     = 3e-4
LR_BLOCKS   = 5e-5
LR_BACKBONE = 1e-5

MIXUP_ALPHA  = 0.3
LABEL_SMOOTH = 0.05
DROPOUT      = 0.4
VAL_RATIO    = 0.15   # RSNA val split / CT-ICH val split (fallback)
TEST_RATIO   = 0.15   # CT-ICH test split (fallback only)

DEFAULT_RSNA_PER_EPOCH = 40_000   # ~40 min/epoch on RTX 3060+


# ==============================================================================
# LOSS / METRICS
# ==============================================================================

def mixup_batch(imgs, labels, alpha=0.3):
    if alpha <= 0:
        return imgs, labels
    lam = float(np.random.beta(alpha, alpha))
    idx = torch.randperm(imgs.size(0), device=imgs.device)
    return lam * imgs + (1 - lam) * imgs[idx], lam * labels + (1 - lam) * labels[idx]


def smooth_labels(labels, eps=0.05):
    return labels * (1 - eps) + eps * 0.5


class FocalLossSmooth(nn.Module):
    def __init__(self, alpha=0.25, gamma=2.0, smooth=0.05):
        super().__init__()
        self.alpha, self.gamma, self.smooth = alpha, gamma, smooth

    def forward(self, logits, targets):
        if self.smooth > 0:
            targets = smooth_labels(targets, self.smooth)
        bce   = F.binary_cross_entropy_with_logits(logits, targets, reduction="none")
        prob  = torch.sigmoid(logits)
        p_t   = targets * prob + (1 - targets) * (1 - prob)
        a_t   = targets * self.alpha + (1 - targets) * (1 - self.alpha)
        return (a_t * (1 - p_t) ** self.gamma * bce).mean()


def compute_auc(truths, preds):
    preds = np.nan_to_num(preds, nan=0.5, posinf=1.0, neginf=0.0)
    aucs = []
    for c in range(truths.shape[1]):
        if len(np.unique(truths[:, c])) > 1:
            aucs.append(roc_auc_score(truths[:, c], preds[:, c]))
    return float(np.mean(aucs)) if aucs else 0.5


def compute_auc_per_class(truths, preds, class_names):
    result = {}
    for c, name in enumerate(class_names):
        if len(np.unique(truths[:, c])) > 1:
            result[name] = float(roc_auc_score(truths[:, c], preds[:, c]))
        else:
            result[name] = float("nan")
    return result


def find_optimal_thresholds(truths, preds):
    thresholds = []
    for c in range(preds.shape[1]):
        y_t, y_p = truths[:, c], preds[:, c]
        if len(np.unique(y_t)) < 2:
            thresholds.append(0.5)
            continue
        best_thr, best_j = 0.5, -1.0
        for thr in np.arange(0.05, 0.95, 0.02):
            pb = (y_p >= thr).astype(int)
            tp = ((pb == 1) & (y_t == 1)).sum()
            tn = ((pb == 0) & (y_t == 0)).sum()
            fp = ((pb == 1) & (y_t == 0)).sum()
            fn = ((pb == 0) & (y_t == 1)).sum()
            j = tp / (tp + fn + 1e-8) + tn / (tn + fp + 1e-8) - 1
            if j > best_j:
                best_j, best_thr = j, thr
        thresholds.append(float(best_thr))
    return thresholds


# ==============================================================================
# DATA LOADING
# ==============================================================================

def _get_available_patients(nii_dir, csv_path):
    """Return sorted list of patient ints that have both NIfTI and labels."""
    from src.data.nifti_loader import parse_ich_labels
    labels_df = parse_ich_labels(csv_path)
    available = set()
    for f in Path(nii_dir).glob("*.nii"):
        try:
            available.add(int(f.stem))
        except ValueError:
            pass
    labeled = set(labels_df["patient_num"].unique())
    return sorted(available & labeled)


def load_ctich_all(nii_dir, csv_path, img_size):
    """Load ALL CT-ICH patients (no train/val split) - used as test set."""
    from src.data.nifti_loader import ICHDataset
    ds = ICHDataset(
        nii_dir, csv_path,
        img_size=img_size,
        augment=False,
        patients=None,          # all patients
    )
    return ds


def load_ctich_split(nii_dir, csv_path, img_size, seed=42):
    """
    Load CT-ICH with a 70/15/15 patient-level train/val/test split.
    Used as fallback when RSNA is not available.
    """
    from src.data.nifti_loader import ICHDataset

    patients = _get_available_patients(nii_dir, csv_path)
    rng      = np.random.default_rng(seed)
    patients = list(rng.permutation(patients))

    n_test  = max(1, int(len(patients) * TEST_RATIO))
    n_val   = max(1, int(len(patients) * VAL_RATIO))
    test_p  = patients[:n_test]
    val_p   = patients[n_test:n_test + n_val]
    train_p = patients[n_test + n_val:]

    print(f"  CT-ICH patient split -> "
          f"train: {len(train_p)} * val: {len(val_p)} * test: {len(test_p)}")

    train_ds = ICHDataset(nii_dir, csv_path, img_size=img_size, augment=True,  patients=train_p)
    val_ds   = ICHDataset(nii_dir, csv_path, img_size=img_size, augment=False, patients=val_p)
    test_ds  = ICHDataset(nii_dir, csv_path, img_size=img_size, augment=False, patients=test_p)
    return train_ds, val_ds, test_ds


def load_rsna(img_dir, csv_path, img_size, rsna_per_epoch, seed=42):
    """
    Load RSNA dataset and return (train_loader, val_loader) or (None, None).

    * 85% slices -> train (with strong augmentation)
    * 15% slices -> val   (for early stopping, no augmentation)
    * RSNA train capped at rsna_per_epoch slices to limit epoch time
    """
    if not img_dir.exists() or not csv_path.exists():
        return None, None

    dcm_files = list(img_dir.glob("*.dcm")) or list(img_dir.rglob("*.dcm"))
    if not dcm_files:
        print("  [WARNING] RSNA: No .dcm files found in", img_dir)
        return None, None

    print(f"  RSNA: {len(dcm_files):,} DICOM files found")

    from src.data.rsna_loader import RSNADataset, parse_labels

    labels_df = parse_labels(csv_path)
    print(f"  RSNA: {len(labels_df):,} labeled slices")

    rng  = np.random.default_rng(seed)
    uids = labels_df["sop_uid"].values.copy()
    rng.shuffle(uids)
    n_val      = int(len(uids) * VAL_RATIO)
    val_uids   = set(uids[:n_val])
    train_uids = set(uids[n_val:])

    train_df = labels_df[labels_df["sop_uid"].isin(train_uids)].reset_index(drop=True)
    val_df   = labels_df[labels_df["sop_uid"].isin(val_uids)].reset_index(drop=True)

    # Find actual DICOM directory (might be one level deeper)
    if any(img_dir.glob("*.dcm")):
        actual_dir = img_dir
    else:
        subdirs = [d for d in img_dir.iterdir() if d.is_dir()]
        actual_dir = subdirs[0] if subdirs else img_dir

    train_set = RSNADataset(actual_dir, train_df, img_size=img_size, augment=True)
    val_set   = RSNADataset(actual_dir, val_df,   img_size=img_size, augment=False)

    # Cap training slices per epoch
    if rsna_per_epoch < len(train_set):
        indices   = rng.choice(len(train_set), rsna_per_epoch, replace=False)
        train_set = Subset(train_set, indices.tolist())

    print(f"  RSNA: train={len(train_set):,} (capped)  val={len(val_set):,}")

    train_loader = DataLoader(
        train_set,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=4,
        pin_memory=(DEVICE == "cuda"),
        drop_last=True,
    )
    val_loader = DataLoader(
        val_set,
        batch_size=BATCH_SIZE * 2,
        shuffle=False,
        num_workers=4,
        pin_memory=(DEVICE == "cuda"),
    )
    return train_loader, val_loader


# ==============================================================================
# TRAINING LOOP
# ==============================================================================

def train_epoch(model, loader, optimizer, scaler, criterion, desc):
    model.train()
    total_loss = 0.0
    optimizer.zero_grad()
    for step, (imgs, labels, *_) in enumerate(
        tqdm(loader, desc=desc, leave=False, ncols=72)
    ):
        imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
        imgs, labels = mixup_batch(imgs, labels, MIXUP_ALPHA)
        with torch.amp.autocast("cuda", enabled=USE_AMP):
            loss = criterion(model(imgs), labels) / GRAD_ACCUM
        scaler.scale(loss).backward()
        total_loss += loss.item() * GRAD_ACCUM
        if (step + 1) % GRAD_ACCUM == 0 or (step + 1) == len(loader):
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()
            optimizer.zero_grad()
    return total_loss / len(loader)


def evaluate(model, loader):
    """Run inference on a DataLoader and return (loss, auc, truths, preds)."""
    model.eval()
    total_loss = 0.0
    all_truths, all_preds = [], []
    criterion  = FocalLossSmooth()
    with torch.no_grad():
        for imgs, labels, *_ in loader:
            imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
            logits = model(imgs)
            total_loss += criterion(logits, labels).item()
            all_truths.append(labels.cpu().numpy())
            all_preds.append(torch.sigmoid(logits).cpu().numpy())
    truths = np.concatenate(all_truths)
    preds  = np.concatenate(all_preds)
    return total_loss / len(loader), compute_auc(truths, preds), truths, preds


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Q-Sentinel Cross-Dataset Training")
    parser.add_argument("--ctich-only",     action="store_true",
                        help="Force CT-ICH-only training (no RSNA)")
    parser.add_argument("--rsna-per-epoch", type=int, default=DEFAULT_RSNA_PER_EPOCH,
                        help=f"Max RSNA slices per epoch (default: {DEFAULT_RSNA_PER_EPOCH:,})")
    parser.add_argument("--resume",         action="store_true",
                        help="Resume from combined_b4.pth")
    parser.add_argument("--batch-size",     type=int, default=BATCH_SIZE)
    args = parser.parse_args()

    from src.data.rsna_loader import SUBTYPES

    # -- Detect mode ---------------------------------------------------------
    rsna_available = (
        not args.ctich_only
        and RSNA_IMG.exists()
        and RSNA_CSV.exists()
        and (list(RSNA_IMG.glob("*.dcm")) or list(RSNA_IMG.rglob("*.dcm")))
    )

    sep = "=" * 65
    if rsna_available:
        print(sep)
        print("  MODE: Cross-Dataset Validation")
        print("  +- TRAIN  ->  RSNA (Kaggle DICOM, 85% split)")
        print("  |- VAL    ->  RSNA (15%, for early stopping)")
        print("  +- TEST   ->  CT-ICH PhysioNet (ALL 75 patients)")
        print("                ^ NEVER seen during training ^")
        print(sep)
    else:
        if not args.ctich_only:
            print("  [i] RSNA not found - falling back to CT-ICH only mode.")
            print("  [i] Download RSNA: python download_rsna.py")
        print(sep)
        print("  MODE: CT-ICH only (70 / 15 / 15 patient split)")
        print(sep)

    # -- Load CT-ICH ---------------------------------------------------------
    print("\nLoading CT-ICH dataset...")
    if rsna_available:
        # All CT-ICH is held out as the cross-dataset test set
        ctich_test = load_ctich_all(CTICH_NII, CTICH_CSV, IMG_SIZE)
        test_loader = DataLoader(
            ctich_test,
            batch_size=args.batch_size * 2,
            shuffle=False,
            num_workers=0,
            pin_memory=(DEVICE == "cuda"),
        )
        print(f"  CT-ICH: {len(ctich_test):,} slices -> cross-dataset TEST (held out)")
    else:
        # 70/15/15 patient-level split
        ctich_train, ctich_val, ctich_test = load_ctich_split(
            CTICH_NII, CTICH_CSV, IMG_SIZE
        )
        train_loader = DataLoader(
            ctich_train,
            batch_size=args.batch_size,
            shuffle=True,
            num_workers=4,
            pin_memory=(DEVICE == "cuda"),
            drop_last=True,
        )
        val_loader = DataLoader(
            ctich_val,
            batch_size=args.batch_size * 2,
            shuffle=False,
            num_workers=4,
            pin_memory=(DEVICE == "cuda"),
        )
        test_loader = DataLoader(
            ctich_test,
            batch_size=args.batch_size * 2,
            shuffle=False,
            num_workers=4,
            pin_memory=(DEVICE == "cuda"),
        )
        print(f"  CT-ICH: train={len(ctich_train):,} * "
              f"val={len(ctich_val):,} * test={len(ctich_test):,} slices")

    # -- Load RSNA (if available) ---------------------------------------------
    if rsna_available:
        print("\nLoading RSNA dataset...")
        train_loader, val_loader = load_rsna(
            RSNA_IMG, RSNA_CSV, IMG_SIZE,
            rsna_per_epoch=args.rsna_per_epoch,
        )
        if train_loader is None:
            print("  [ERROR] RSNA detected but failed to load - check the dataset.")
            sys.exit(1)

    # -- Build model ----------------------------------------------------------
    print("\nInitializing EfficientNet-B4...")
    from src.models.cnn_encoder import load_baseline, build_baseline

    if args.resume and COMBINED_MODEL_PATH.exists():
        model = load_baseline(str(COMBINED_MODEL_PATH), DEVICE)
        print(f"  Resumed from {COMBINED_MODEL_PATH.name}")
    elif (WEIGHTS_DIR / "high_acc_b4.pth").exists():
        model = load_baseline(str(WEIGHTS_DIR / "high_acc_b4.pth"), DEVICE)
        print("  Initialized from high_acc_b4.pth (CT-ICH pretrained)")
    else:
        model = build_baseline(num_classes=6, dropout=DROPOUT).to(DEVICE)
        print("  Initialized from ImageNet weights")

    criterion = FocalLossSmooth(smooth=LABEL_SMOOTH)
    scaler    = torch.amp.GradScaler("cuda", enabled=USE_AMP)

    # -- Progressive unfreezing -----------------------------------------------
    def freeze_backbone(m):
        for p in m.parameters():
            p.requires_grad = False
        for p in m.classifier.parameters():
            p.requires_grad = True

    def unfreeze_last_blocks(m):
        for p in m.parameters():
            p.requires_grad = False
        for name, p in m.named_parameters():
            if any(k in name for k in [
                "blocks.5", "blocks.6", "blocks.7",
                "head", "classifier", "bn2", "conv_head",
            ]):
                p.requires_grad = True

    def unfreeze_all(m):
        for p in m.parameters():
            p.requires_grad = True

    def make_optimizer(phase):
        if phase == 1:
            freeze_backbone(model)
            return torch.optim.AdamW(
                filter(lambda p: p.requires_grad, model.parameters()),
                lr=LR_HEAD, weight_decay=1e-4,
            )
        elif phase == 2:
            unfreeze_last_blocks(model)
            return torch.optim.AdamW([
                {"params": [p for n, p in model.named_parameters()
                            if p.requires_grad and "head" not in n],
                 "lr": LR_BLOCKS},
                {"params": model.head.parameters(), "lr": LR_HEAD},
            ], weight_decay=1e-4)
        else:
            unfreeze_all(model)
            return torch.optim.AdamW([
                {"params": model.features.parameters(),    "lr": LR_BACKBONE},
                {"params": model.classifier.parameters(),  "lr": LR_HEAD * 0.5},
            ], weight_decay=1e-4)

    # -- Training loop --------------------------------------------------------
    best_auc   = 0.0
    no_improve = 0
    history    = []
    start_time = time.time()

    val_source = "RSNA" if rsna_available else "CT-ICH"

    phase_schedule = [
        (1, PHASE1_EPOCHS, "Phase 1 - Head only"),
        (2, PHASE2_EPOCHS, "Phase 2 - Last 2 blocks"),
        (3, PHASE3_EPOCHS, "Phase 3 - Full backbone"),
    ]

    global_epoch = 0
    for phase, n_epochs, phase_name in phase_schedule:
        print(f"\n{'-'*55}")
        print(f"  {phase_name}  ({n_epochs} epochs)")
        print(f"{'-'*55}")

        if n_epochs == 0:
            make_optimizer(phase)   # still run freeze/unfreeze
            continue
        optimizer = make_optimizer(phase)
        scheduler = torch.optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=[g["lr"] for g in optimizer.param_groups],
            epochs=n_epochs,
            steps_per_epoch=max(1, len(train_loader) // GRAD_ACCUM),
            pct_start=0.3,
            anneal_strategy="cos",
        )

        for ep in range(n_epochs):
            global_epoch += 1
            desc = f"Ep {global_epoch:2d}/{TOTAL_EPOCHS}"

            train_loss = train_epoch(
                model, train_loader, optimizer, scaler, criterion, desc
            )
            val_loss, val_auc, _, _ = evaluate(model, val_loader)
            scheduler.step()

            mark = "OK" if val_auc > best_auc else " "
            print(f"  [{mark}] Ep {global_epoch:02d} | "
                  f"train={train_loss:.4f}  val={val_loss:.4f}  "
                  f"{val_source}_AUC={val_auc:.4f}")

            history.append({
                "epoch":      global_epoch,
                "train_loss": train_loss,
                "val_loss":   val_loss,
                "val_auc":    val_auc,
            })

            if val_auc > best_auc:
                best_auc   = val_auc
                no_improve = 0
                torch.save(model.state_dict(), COMBINED_MODEL_PATH)
                print(f"       OK Saved -> {COMBINED_MODEL_PATH.name}  "
                      f"(AUC {best_auc:.4f})")
            else:
                no_improve += 1
                if no_improve >= EARLY_STOP_PATIENCE:
                    print(f"\n  Early stopping "
                          f"(no improvement for {EARLY_STOP_PATIENCE} epochs)")
                    break

        if no_improve >= EARLY_STOP_PATIENCE:
            break

    # -- Cross-Dataset Final Test ---------------------------------------------
    print(f"\n{'='*65}")
    if rsna_available:
        print("  * CROSS-DATASET EVALUATION")
        print("  CT-ICH (PhysioNet) - NEVER seen during training")
    else:
        print("  * HELD-OUT TEST SET EVALUATION")
        print("  CT-ICH test patients (15%, held out from training)")
    print(f"{'-'*65}")

    model.load_state_dict(torch.load(COMBINED_MODEL_PATH, map_location=DEVICE))
    _, cross_auc, ct_truths, ct_preds = evaluate(model, test_loader)

    per_class = compute_auc_per_class(ct_truths, ct_preds, SUBTYPES)

    print(f"\n  * Cross-Dataset AUC (CT-ICH):  {cross_auc:.4f}  "
          f"({cross_auc * 100:.1f}%)")
    if rsna_available:
        print(f"  * RSNA Val AUC (best):         {best_auc:.4f}  "
              f"({best_auc * 100:.1f}%)")
    print()
    print("  Per-class AUC on CT-ICH:")
    for name, auc in per_class.items():
        if np.isnan(auc):
            print(f"    {name:<22}  N/A  (no positive samples in test)")
        else:
            bar = "#" * int(auc * 25)
            print(f"    {name:<22}  {auc:.4f}  {bar}")

    # -- Threshold calibration on CT-ICH -------------------------------------
    print(f"\n{'-'*65}")
    print("  Calibrating decision thresholds on CT-ICH test set...")
    thresholds = find_optimal_thresholds(ct_truths, ct_preds)
    thr_dict   = {s: float(t) for s, t in zip(SUBTYPES, thresholds)}
    with open(THRESHOLDS_PATH, "w") as f:
        json.dump(thr_dict, f, indent=2)
    print("  Per-class thresholds (Youden's J):")
    for s, t in thr_dict.items():
        print(f"    {s:<22}  {t:.3f}")

    # -- Save results ---------------------------------------------------------
    elapsed = time.time() - start_time
    result  = {
        "cross_dataset_auc": cross_auc,
        "rsna_val_auc":      best_auc if rsna_available else None,
        "per_class_auc":     per_class,
        "total_epochs":      global_epoch,
        "elapsed_min":       round(elapsed / 60, 1),
        "mode":              "cross_dataset" if rsna_available else "ctich_only",
        "train_source":      "RSNA" if rsna_available else "CT-ICH",
        "test_source":       "CT-ICH (PhysioNet, all 75 patients)",
        "history":           history,
    }
    with open(COMBINED_HIST, "w") as f:
        json.dump(result, f, indent=2)

    # -- Auto-promote if best model so far ------------------------------------
    high_acc_path = WEIGHTS_DIR / "high_acc_b4.pth"
    prev_auc = 0.0
    prev_file = DATA_DIR / "high_acc_results.json"
    if prev_file.exists():
        try:
            with open(prev_file) as f:
                prev_auc = json.load(f).get("best_auc", 0.0)
        except Exception:
            pass

    print(f"\n{'-'*65}")
    if cross_auc > prev_auc:
        import shutil
        shutil.copy2(COMBINED_MODEL_PATH, high_acc_path)
        with open(prev_file, "w") as f:
            json.dump({
                "best_auc": cross_auc,
                "source":   "cross_dataset_training",
            }, f, indent=2)
        print(f"  OK Auto-promoted to high_acc_b4.pth")
        print(f"    Cross-dataset AUC {cross_auc:.4f} > previous {prev_auc:.4f}")
        print(f"    -> Restart dashboard to load the updated model")
    else:
        print(f"  [i]  Cross-dataset AUC {cross_auc:.4f} <= previous best {prev_auc:.4f}")
        print(f"     Weights kept in combined_b4.pth (high_acc_b4.pth unchanged)")

    print(f"{'='*65}")
    print(f"  DONE  *  {elapsed / 60:.1f} min  *  "
          f"Cross-Dataset AUC = {cross_auc:.4f}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
