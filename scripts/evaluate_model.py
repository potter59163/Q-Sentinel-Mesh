"""
evaluate_model.py — Q-Sentinel Full Dataset Evaluation

Test model on all 75 CT patients from CT-ICH dataset.
Ground truth: hemorrhage_diagnosis_raw_ct.csv (per-slice labels)
Prediction:   Volume-level max-pool probabilities with TTA

Reports:
  - Per-class AUC, Sensitivity, Specificity, F1
  - Per-patient prediction table
  - Confusion matrix per subtype
  - Overall accuracy

Usage:
    python evaluate_model.py
    python evaluate_model.py --tta 3   # faster, less TTA
    python evaluate_model.py --show-errors  # show mispredicted patients
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from torchvision import transforms

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

SUBTYPES = ["epidural", "intraparenchymal", "intraventricular",
            "subarachnoid", "subdural", "any"]

WINDOWS = {
    "brain":    (40,  80),
    "blood":    (60,  120),
    "subdural": (75,  215),
}

_MEAN = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
_STD  = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)

IMG_SIZE = 224

# ─────────────────────────────────────────────────────────────────────────────
# CT Preprocessing
# ─────────────────────────────────────────────────────────────────────────────

def apply_window(hu, center, width):
    lo = center - width / 2.0
    hi = center + width / 2.0
    return np.clip((hu - lo) / (hi - lo), 0.0, 1.0)


def hu_to_tensor(hu_slice):
    channels = [
        apply_window(hu_slice, *WINDOWS["brain"]),
        apply_window(hu_slice, *WINDOWS["blood"]),
        apply_window(hu_slice, *WINDOWS["subdural"]),
    ]
    img = np.stack(channels, axis=-1).astype(np.float32)
    t   = torch.from_numpy(img).permute(2, 0, 1)
    t   = transforms.functional.resize(
        t, [IMG_SIZE, IMG_SIZE],
        interpolation=transforms.InterpolationMode.BILINEAR,
        antialias=True,
    )
    return t


def normalize(t):
    return (t - _MEAN) / _STD


# ─────────────────────────────────────────────────────────────────────────────
# TTA Inference
# ─────────────────────────────────────────────────────────────────────────────

TTA_FNS = [
    None,
    transforms.functional.hflip,
    transforms.functional.vflip,
    lambda x: transforms.functional.rotate(x, 10),
    lambda x: transforms.functional.rotate(x, -10),
    lambda x: transforms.functional.affine(x, 0, [0,0], 0.9, 0),
    lambda x: transforms.functional.affine(x, 0, [0,0], 1.1, 0),
]


def predict_volume_tta(model, nii_path: Path, n_tta: int = 7) -> np.ndarray:
    """
    Load NIfTI volume, run TTA on all slices, return max-pooled probs (6,).
    """
    import nibabel as nib
    img  = nib.load(str(nii_path))
    data = img.get_fdata(dtype=np.float32)
    if data.ndim == 4:
        data = data[..., 0]
    data = np.transpose(data, (2, 0, 1))   # (D, H, W)
    n_slices = data.shape[0]

    all_probs = []

    with torch.no_grad():
        for s in range(n_slices):
            tensor_raw = hu_to_tensor(data[s])   # (3, H, W) in [0,1]

            preds = []
            for fn in TTA_FNS[:n_tta]:
                t = tensor_raw.clone()
                if fn is not None:
                    t = fn(t)
                t = normalize(t)
                t = t.unsqueeze(0).to(DEVICE)
                with torch.amp.autocast(device_type=DEVICE, enabled=(DEVICE == "cuda")):
                    logits = model(t)
                probs = torch.sigmoid(logits.float()).squeeze(0).cpu().numpy()
                preds.append(probs)

            slice_prob = np.mean(preds, axis=0)   # (6,)
            all_probs.append(slice_prob)

    all_probs_arr = np.stack(all_probs)     # (D, 6)
    vol_probs = all_probs_arr.max(axis=0)   # max-pool across slices → (6,)
    return vol_probs


# ─────────────────────────────────────────────────────────────────────────────
# Ground Truth Loading
# ─────────────────────────────────────────────────────────────────────────────

def load_ground_truth(csv_path: Path) -> pd.DataFrame:
    """
    Load per-slice labels, aggregate to per-patient level.
    Patient is POSITIVE for a subtype if ANY slice is positive.
    Returns DataFrame with columns: patient_num, epidural, ..., subdural, any
    """
    df = pd.read_csv(str(csv_path))
    df.columns = [c.lstrip('\ufeff').strip() for c in df.columns]

    # 'any' = has hemorrhage (not No_Hemorrhage)
    df["any"] = (df["No_Hemorrhage"] == 0).astype(int)

    rename = {
        "PatientNumber":     "patient_num",
        "Epidural":          "epidural",
        "Intraparenchymal":  "intraparenchymal",
        "Intraventricular":  "intraventricular",
        "Subarachnoid":      "subarachnoid",
        "Subdural":          "subdural",
    }
    df = df.rename(columns=rename)

    # Aggregate to patient level: positive if any slice positive
    patient_df = df.groupby("patient_num")[
        ["epidural", "intraparenchymal", "intraventricular",
         "subarachnoid", "subdural", "any"]
    ].max().reset_index()

    return patient_df


# ─────────────────────────────────────────────────────────────────────────────
# Metrics
# ─────────────────────────────────────────────────────────────────────────────

def compute_metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float) -> dict:
    """Compute AUC, Sensitivity (recall), Specificity, Precision, F1."""
    from sklearn.metrics import roc_auc_score, confusion_matrix

    y_pred = (y_prob >= threshold).astype(int)

    # AUC (needs both classes present)
    try:
        auc = roc_auc_score(y_true, y_prob)
    except ValueError:
        auc = float("nan")

    # Confusion matrix
    if len(np.unique(y_true)) > 1:
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    else:
        tn = fp = fn = tp = 0

    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    precision   = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    f1 = 2 * precision * sensitivity / (precision + sensitivity) if (precision + sensitivity) > 0 else 0.0
    accuracy    = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0

    return {
        "auc": auc, "sensitivity": sensitivity, "specificity": specificity,
        "precision": precision, "f1": f1, "accuracy": accuracy,
        "tp": int(tp), "tn": int(tn), "fp": int(fp), "fn": int(fn),
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Q-Sentinel Full Evaluation")
    parser.add_argument("--ct-dir", type=Path,
        default=ROOT.parent / "computed-tomography-images-for-intracranial-hemorrhage-detection-and-segmentation-1.3.1" / "ct_scans")
    parser.add_argument("--csv", type=Path,
        default=ROOT.parent / "computed-tomography-images-for-intracranial-hemorrhage-detection-and-segmentation-1.3.1" / "hemorrhage_diagnosis_raw_ct.csv")
    parser.add_argument("--weights", type=Path,
        default=ROOT / "weights" / "high_acc_b4.pth")
    parser.add_argument("--tta", type=int, default=7, help="TTA augmentations (1-7)")
    parser.add_argument("--show-errors", action="store_true", help="Show mispredicted patients")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "eval_results.json")
    args = parser.parse_args()

    # ── Load model ──────────────────────────────────────────────────────────
    print(f"\n{'='*65}")
    print(f"  Q-SENTINEL MODEL EVALUATION")
    print(f"  Device: {DEVICE.upper()}", end="")
    if torch.cuda.is_available():
        print(f" ({torch.cuda.get_device_name(0)})", end="")
    print(f"\n  TTA: {args.tta} augmentations")
    print(f"{'='*65}\n")

    if not args.weights.exists():
        fallback = ROOT / "weights" / "baseline_b4.pth"
        if fallback.exists():
            print(f"  [!] {args.weights.name} not found → using {fallback.name}")
            args.weights = fallback
        else:
            print("  [X] No weights found. Run train_high_acc.py first.")
            sys.exit(1)

    from src.models.cnn_encoder import build_efficientnet_b4
    model = build_efficientnet_b4(pretrained=False, dropout=0.0)
    state = torch.load(str(args.weights), map_location=DEVICE)
    model.load_state_dict(state, strict=True)
    model.to(DEVICE)
    model.eval()
    print(f"  Model   : {args.weights.name}")

    # ── Load calibrated thresholds ──────────────────────────────────────────
    thr_path = ROOT / "results" / "optimal_thresholds.json"
    if thr_path.exists():
        with open(thr_path) as f:
            thresholds = json.load(f)
        print(f"  Thresholds: calibrated from {thr_path.name}")
    else:
        thresholds = {"epidural": 0.13, "intraparenchymal": 0.11,
                      "intraventricular": 0.09, "subarachnoid": 0.05,
                      "subdural": 0.50, "any": 0.15}
        print(f"  Thresholds: default (no calibration file found)")

    # ── Load ground truth ───────────────────────────────────────────────────
    gt_df = load_ground_truth(args.csv)
    print(f"  Ground truth: {len(gt_df)} patients from {args.csv.name}\n")

    # Distribution summary
    print("  Ground truth distribution (patient-level positives):")
    for s in SUBTYPES:
        n_pos = int(gt_df[s].sum())
        n_neg = len(gt_df) - n_pos
        print(f"    {s:<26}: {n_pos:2d} positive / {n_neg:2d} negative")

    # ── Run inference on all CT scans ────────────────────────────────────────
    nii_files = sorted(args.ct_dir.glob("*.nii"))
    print(f"\n  Found {len(nii_files)} CT scans in {args.ct_dir.name}/")
    print(f"  Running inference with TTA={args.tta}...\n")

    results = []  # list of {patient_num, probs}
    t_start = time.time()

    for i, nii_path in enumerate(nii_files):
        try:
            patient_num = int(nii_path.stem)
        except ValueError:
            continue  # skip non-numeric filenames

        if patient_num not in gt_df["patient_num"].values:
            continue  # skip patients not in ground truth

        t0 = time.time()
        vol_probs = predict_volume_tta(model, nii_path, n_tta=args.tta)
        elapsed = time.time() - t0

        probs_dict = {s: float(vol_probs[j]) for j, s in enumerate(SUBTYPES)}
        results.append({"patient_num": patient_num, "probs": probs_dict})

        # Progress
        pred_any = "POSITIVE" if vol_probs[5] >= thresholds["any"] else "negative"
        gt_row = gt_df[gt_df["patient_num"] == patient_num].iloc[0]
        gt_any  = "POSITIVE" if gt_row["any"] == 1 else "negative"
        match   = "OK" if pred_any == gt_any else "MISS"

        print(f"  [{i+1:2d}/{len(nii_files)}] Patient {patient_num:03d}  "
              f"pred={pred_any:<10} gt={gt_any:<10}  [{match}]  ({elapsed:.1f}s)")

    total_time = time.time() - t_start
    print(f"\n  Total inference time: {total_time:.1f}s  "
          f"({total_time/len(results):.1f}s per patient)\n")

    # ── Build arrays for metric computation ──────────────────────────────────
    result_df = pd.DataFrame([
        {"patient_num": r["patient_num"], **r["probs"]} for r in results
    ])

    # Merge with ground truth
    merged = result_df.merge(
        gt_df, on="patient_num", suffixes=("_pred", "_gt")
    )

    # ── Compute per-class metrics ────────────────────────────────────────────
    print(f"{'='*65}")
    print(f"  EVALUATION RESULTS  ({len(merged)} patients)")
    print(f"{'='*65}\n")

    header = f"  {'Class':<26} {'AUC':>7} {'Sens':>7} {'Spec':>7} {'F1':>7} {'Acc':>7} {'TP':>4} {'FP':>4} {'FN':>4} {'TN':>4}"
    print(header)
    print(f"  {'-'*85}")

    all_metrics = {}
    for s in SUBTYPES:
        y_true = merged[f"{s}_gt"].values
        y_prob  = merged[f"{s}_pred"].values
        thr    = thresholds.get(s, 0.5)
        m = compute_metrics(y_true, y_prob, thr)
        all_metrics[s] = m

        auc_str  = f"{m['auc']:.3f}" if not np.isnan(m['auc']) else "  N/A"
        status   = " *" if m['fn'] > 0 else "  "  # * = has false negatives (dangerous!)
        print(f"  {s:<26} {auc_str:>7} {m['sensitivity']:>7.3f} {m['specificity']:>7.3f} "
              f"{m['f1']:>7.3f} {m['accuracy']:>7.3f} "
              f"{m['tp']:>4} {m['fp']:>4} {m['fn']:>4} {m['tn']:>4}{status}")

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n  {'-'*85}")
    aucs = [m["auc"] for m in all_metrics.values() if not np.isnan(m["auc"])]
    mean_auc = np.mean(aucs)
    any_m = all_metrics["any"]
    print(f"\n  Mean AUC (all classes) : {mean_auc:.4f}")
    print(f"  Any-hemorrhage AUC     : {any_m['auc']:.4f}")
    print(f"  Any-hemorrhage Sens    : {any_m['sensitivity']:.3f}  (recall — must be high!)")
    print(f"  Any-hemorrhage Spec    : {any_m['specificity']:.3f}")
    print(f"  Any-hemorrhage F1      : {any_m['f1']:.3f}")
    print(f"  Any-hemorrhage Acc     : {any_m['accuracy']:.3f}")
    print(f"\n  (*) Classes with False Negatives — missed hemorrhage cases")

    # ── Per-patient error analysis ────────────────────────────────────────────
    if args.show_errors:
        print(f"\n{'='*65}")
        print(f"  MISPREDICTED PATIENTS (any-hemorrhage)")
        print(f"{'='*65}")
        any_thr = thresholds["any"]
        for _, row in merged.iterrows():
            pred = row["any_pred"] >= any_thr
            gt   = row["any_gt"] == 1
            if pred != gt:
                label = "FALSE POS" if (pred and not gt) else "FALSE NEG (DANGEROUS)"
                subtypes_pos = [s for s in SUBTYPES[:5] if row[f"{s}_gt"] == 1]
                print(f"  Patient {int(row['patient_num']):03d}  [{label}]  "
                      f"prob={row['any_pred']:.3f}  gt_subtypes={subtypes_pos}")

    # ── Save results ─────────────────────────────────────────────────────────
    save_data = {
        "n_patients": len(merged),
        "weights": str(args.weights),
        "tta": args.tta,
        "thresholds": thresholds,
        "metrics": {s: {k: (float(v) if not isinstance(v, int) else int(v))
                        for k, v in m.items()}
                    for s, m in all_metrics.items()},
        "summary": {
            "mean_auc": float(mean_auc),
            "any_auc": float(any_m["auc"]),
            "any_sensitivity": float(any_m["sensitivity"]),
            "any_specificity": float(any_m["specificity"]),
            "any_f1": float(any_m["f1"]),
            "any_accuracy": float(any_m["accuracy"]),
        },
        "per_patient": [
            {
                "patient_num": int(row["patient_num"]),
                "gt": {s: int(row[f"{s}_gt"]) for s in SUBTYPES},
                "prob": {s: float(row[f"{s}_pred"]) for s in SUBTYPES},
                "pred": {s: bool(row[f"{s}_pred"] >= thresholds.get(s, 0.5)) for s in SUBTYPES},
            }
            for _, row in merged.iterrows()
        ],
    }

    args.output.parent.mkdir(exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=2, ensure_ascii=False)

    print(f"\n  Results saved -> {args.output}")
    print(f"\n{'='*65}\n")


if __name__ == "__main__":
    main()
