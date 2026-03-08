"""
infer_ct.py — Q-Sentinel CT Inference with Test-Time Augmentation (TTA)

รับ CT image (NIfTI .nii หรือ DICOM .dcm) แล้ว predict hemorrhage subtypes
พร้อม TTA (5 augmented predictions averaged) เพื่อความแม่นยำสูงสุด

Usage:
    # NIfTI volume (all slices)
    python infer_ct.py --input path/to/scan.nii

    # NIfTI with specific slice
    python infer_ct.py --input path/to/scan.nii --slice 15

    # DICOM file
    python infer_ct.py --input path/to/slice.dcm

    # Use custom model weights
    python infer_ct.py --input scan.nii --weights weights/high_acc_b4.pth
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn.functional as F
from torchvision import transforms

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

SUBTYPES = ["epidural", "intraparenchymal", "intraventricular",
            "subarachnoid", "subdural", "any"]

# CT Window presets (center, width)
WINDOWS = {
    "brain":    (40,  80),
    "blood":    (60,  120),
    "subdural": (75,  215),
}

# Default thresholds (used if optimal_thresholds.json not found)
DEFAULT_THRESHOLDS = {
    "epidural":          0.35,
    "intraparenchymal":  0.40,
    "intraventricular":  0.40,
    "subarachnoid":      0.40,
    "subdural":          0.40,
    "any":               0.45,
}

IMG_SIZE = 224

# ImageNet normalization
_MEAN = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
_STD  = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)

# Risk levels (ASCII-safe for Windows cp1252 terminals)
RISK_COLORS = {
    "critical":  "[CRITICAL]",
    "high":      "[HIGH]    ",
    "moderate":  "[MODERATE]",
    "low":       "[LOW]     ",
    "none":      "[NONE]    ",
}


# ══════════════════════════════════════════════════════════════════════════════
# IMAGE LOADING
# ══════════════════════════════════════════════════════════════════════════════

def apply_window(hu: np.ndarray, center: float, width: float) -> np.ndarray:
    """Apply CT windowing → [0, 1]."""
    lo = center - width / 2.0
    hi = center + width / 2.0
    return np.clip((hu - lo) / (hi - lo), 0.0, 1.0)


def hu_to_tensor(hu_slice: np.ndarray, img_size: int = IMG_SIZE) -> torch.Tensor:
    """
    Convert 2D HU slice → 3-channel tensor (brain/blood/subdural windows).
    Returns (3, img_size, img_size) float32, NOT normalized.
    """
    channels = [
        apply_window(hu_slice, *WINDOWS["brain"]),
        apply_window(hu_slice, *WINDOWS["blood"]),
        apply_window(hu_slice, *WINDOWS["subdural"]),
    ]
    img = np.stack(channels, axis=-1).astype(np.float32)   # (H, W, 3)
    t   = torch.from_numpy(img).permute(2, 0, 1)           # (3, H, W)
    t   = transforms.functional.resize(
        t, [img_size, img_size],
        interpolation=transforms.InterpolationMode.BILINEAR,
        antialias=True,
    )
    return t  # (3, H, W) in [0, 1]


def normalize(t: torch.Tensor) -> torch.Tensor:
    """Apply ImageNet normalization."""
    return (t - _MEAN) / _STD


def load_nifti(path: Path, slice_idx: Optional[int] = None):
    """Load NIfTI volume → list of (slice_idx, hu_array) tuples."""
    import nibabel as nib
    img  = nib.load(str(path))
    data = img.get_fdata(dtype=np.float32)
    if data.ndim == 4:
        data = data[..., 0]
    data = np.transpose(data, (2, 0, 1))   # (D, H, W)

    if slice_idx is not None:
        if 0 <= slice_idx < data.shape[0]:
            return [(slice_idx, data[slice_idx])]
        else:
            raise ValueError(f"slice_idx {slice_idx} out of range [0, {data.shape[0]-1}]")
    # Return all slices
    return [(i, data[i]) for i in range(data.shape[0])]


def load_dicom(path: Path):
    """Load single DICOM slice → list of (0, hu_array)."""
    import pydicom
    ds  = pydicom.dcmread(str(path))
    arr = ds.pixel_array.astype(np.float32)
    # Apply RescaleSlope / RescaleIntercept if present
    slope     = float(getattr(ds, "RescaleSlope",     1))
    intercept = float(getattr(ds, "RescaleIntercept", 0))
    arr = arr * slope + intercept
    return [(0, arr)]


def load_ct(path: Path, slice_idx: Optional[int] = None):
    """Auto-detect format and load CT slices."""
    suffix = path.suffix.lower()
    if suffix in (".nii", ".gz"):
        return load_nifti(path, slice_idx)
    elif suffix == ".dcm":
        return load_dicom(path)
    else:
        # Try NIfTI first, then DICOM
        try:
            return load_nifti(path, slice_idx)
        except Exception:
            return load_dicom(path)


# ══════════════════════════════════════════════════════════════════════════════
# MODEL LOADING
# ══════════════════════════════════════════════════════════════════════════════

def load_model(weights_path: Path):
    """Load EfficientNet-B4 model from weights file."""
    from src.models.cnn_encoder import build_efficientnet_b4
    model = build_efficientnet_b4(pretrained=False, dropout=0.0)
    state = torch.load(str(weights_path), map_location=DEVICE)
    model.load_state_dict(state, strict=True)
    model.to(DEVICE)
    model.eval()
    print(f"  Model loaded: {weights_path}")
    return model


def load_thresholds() -> dict:
    """Load per-class optimal thresholds (from training calibration)."""
    thr_path = ROOT / "results" / "optimal_thresholds.json"
    if thr_path.exists():
        with open(thr_path) as f:
            thr = json.load(f)
        print(f"  Loaded calibrated thresholds from {thr_path}")
        return thr
    print("  Using default thresholds (run train_high_acc.py for calibrated thresholds)")
    return DEFAULT_THRESHOLDS.copy()


# ══════════════════════════════════════════════════════════════════════════════
# TEST-TIME AUGMENTATION (TTA)
# ══════════════════════════════════════════════════════════════════════════════

def predict_tta(model, tensor_raw: torch.Tensor, n_tta: int = 7) -> np.ndarray:
    """
    Apply TTA: run N augmented versions → average sigmoid probabilities.

    tensor_raw: (3, H, W) float32 in [0, 1] — NOT normalized yet
    Returns: (6,) numpy array of probabilities
    """
    TTA_FNS = [
        None,                                                          # original
        transforms.functional.hflip,                                   # horizontal flip
        transforms.functional.vflip,                                   # vertical flip
        lambda x: transforms.functional.rotate(x, 10),                # rotate +10°
        lambda x: transforms.functional.rotate(x, -10),               # rotate -10°
        lambda x: transforms.functional.affine(x, 0, [0,0], 0.9, 0), # zoom out
        lambda x: transforms.functional.affine(x, 0, [0,0], 1.1, 0), # zoom in
    ]

    preds = []
    with torch.no_grad():
        for fn in TTA_FNS[:n_tta]:
            t = tensor_raw.clone()
            if fn is not None:
                t = fn(t)
            t = normalize(t)
            t = t.unsqueeze(0).to(DEVICE)   # (1, 3, H, W)
            with torch.amp.autocast(device_type=DEVICE, enabled=(DEVICE == "cuda")):
                logits = model(t)
            probs = torch.sigmoid(logits.float()).squeeze(0).cpu().numpy()
            preds.append(probs)

    return np.mean(preds, axis=0)   # (6,) averaged


# ══════════════════════════════════════════════════════════════════════════════
# PREDICTION & REPORT
# ══════════════════════════════════════════════════════════════════════════════

def predict_volume(model, slices: list, thresholds: dict, n_tta: int = 7):
    """
    Predict all slices in volume. Returns per-slice results and volume-level summary.
    """
    all_probs  = []
    slice_results = []

    print(f"\n  Analyzing {len(slices)} slice(s) with TTA (n={n_tta})...")

    for i, (slice_idx, hu) in enumerate(slices):
        tensor_raw = hu_to_tensor(hu)        # (3, H, W) in [0,1]
        probs = predict_tta(model, tensor_raw, n_tta)  # (6,)
        all_probs.append(probs)

        # Classify per slice
        detected = {}
        for j, subtype in enumerate(SUBTYPES):
            thr = thresholds.get(subtype, 0.5)
            detected[subtype] = {
                "prob": float(probs[j]),
                "positive": bool(probs[j] >= thr),
                "threshold": thr,
            }

        slice_results.append({
            "slice_idx": slice_idx,
            "probs": {s: float(probs[j]) for j, s in enumerate(SUBTYPES)},
            "detected": detected,
        })

    # Volume-level: max probability across all slices per class
    all_probs_arr = np.stack(all_probs)  # (N_slices, 6)
    vol_probs = all_probs_arr.max(axis=0)   # max-pooling across slices

    vol_detected = {}
    for j, subtype in enumerate(SUBTYPES):
        thr = thresholds.get(subtype, 0.5)
        vol_detected[subtype] = {
            "prob":     float(vol_probs[j]),
            "positive": bool(vol_probs[j] >= thr),
            "threshold": thr,
        }

    return slice_results, vol_detected, vol_probs


def get_risk_level(prob: float) -> str:
    if prob >= 0.75:  return "critical"
    if prob >= 0.55:  return "high"
    if prob >= 0.40:  return "moderate"
    if prob >= 0.20:  return "low"
    return "none"


def print_report(input_path: Path, vol_detected: dict, slice_results: list, vol_probs: np.ndarray):
    """Print formatted diagnostic report."""
    print(f"\n{'='*60}")
    print(f"  Q-SENTINEL CT HEMORRHAGE DETECTION REPORT")
    print(f"  Input: {input_path.name}")
    print(f"  Slices analyzed: {len(slice_results)}")
    print(f"{'='*60}\n")

    # Overall status
    any_hemorrhage = vol_detected["any"]["positive"]
    any_prob = vol_detected["any"]["prob"]

    if any_hemorrhage:
        risk = get_risk_level(any_prob)
        icon = RISK_COLORS[risk]
        print(f"  {icon} HEMORRHAGE DETECTED (confidence: {any_prob*100:.1f}%)")
    else:
        print(f"  [OK] NO HEMORRHAGE DETECTED (confidence: {(1-any_prob)*100:.1f}%)")

    print(f"\n  Per-Subtype Analysis:")
    print(f"  {'Subtype':<26} {'Probability':>12} {'Status':>12}")
    print(f"  {'-'*54}")

    subtypes_detail = [s for s in SUBTYPES if s != "any"]
    for subtype in subtypes_detail:
        d = vol_detected[subtype]
        prob = d["prob"]
        thr  = d["threshold"]
        risk = get_risk_level(prob) if d["positive"] else "none"
        icon = RISK_COLORS[risk]
        status = "POSITIVE" if d["positive"] else "negative"
        bar = "#" * int(prob * 20) + "." * (20 - int(prob * 20))
        print(f"  {subtype:<22} {icon}  {prob*100:5.1f}%  [{bar}]  {status}")

    print(f"\n  Thresholds used (calibrated on validation set):")
    for subtype in subtypes_detail:
        thr = vol_detected[subtype]["threshold"]
        print(f"    {subtype:<24}: {thr:.3f}")

    # Most suspicious slices
    if len(slice_results) > 1:
        print(f"\n  Top 3 Most Suspicious Slices:")
        sorted_slices = sorted(slice_results, key=lambda x: x["probs"]["any"], reverse=True)[:3]
        for sr in sorted_slices:
            p = sr["probs"]["any"]
            print(f"    Slice {sr['slice_idx']:3d}: any={p*100:.1f}%", end="")
            for sub in subtypes_detail:
                if sr["probs"][sub] >= vol_detected[sub]["threshold"]:
                    print(f" | {sub}={sr['probs'][sub]*100:.0f}%", end="")
            print()

    print(f"\n{'='*60}")

    # Clinical note
    print("  [!] NOTE: This is an AI-assisted screening tool.")
    print("      All findings must be confirmed by a radiologist.")
    print(f"{'='*60}\n")


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Q-Sentinel CT Hemorrhage Inference")
    parser.add_argument("--input",   required=True, type=Path, help="CT file (.nii or .dcm)")
    parser.add_argument("--slice",   type=int, default=None,   help="Specific slice index (NIfTI only)")
    parser.add_argument("--weights", type=Path,
                        default=ROOT / "weights" / "high_acc_b4.pth",
                        help="Model weights path")
    parser.add_argument("--tta",     type=int, default=7,      help="Number of TTA augmentations (1-7)")
    parser.add_argument("--output",  type=Path, default=None,  help="Save JSON results to file")
    args = parser.parse_args()

    # Auto-fallback to baseline weights
    weights_path = args.weights
    if not weights_path.exists():
        fallback = ROOT / "weights" / "baseline_b4.pth"
        if fallback.exists():
            print(f"  ⚠️  {weights_path.name} not found. Using {fallback.name}")
            weights_path = fallback
        else:
            print(f"  ❌ No model weights found. Run train_high_acc.py first.")
            sys.exit(1)

    print(f"\n  Q-Sentinel CT Inference")
    print(f"  Device: {DEVICE.upper()}", end="")
    if torch.cuda.is_available():
        print(f" ({torch.cuda.get_device_name(0)})", end="")
    print()

    # Load model + thresholds
    model      = load_model(weights_path)
    thresholds = load_thresholds()

    # Load CT image
    print(f"  Loading CT: {args.input}")
    slices = load_ct(args.input, args.slice)
    print(f"  Found {len(slices)} slice(s)")

    # Predict
    slice_results, vol_detected, vol_probs = predict_volume(
        model, slices, thresholds, n_tta=args.tta
    )

    # Print report
    print_report(args.input, vol_detected, slice_results, vol_probs)

    # Save JSON results
    if args.output:
        result_data = {
            "input":      str(args.input),
            "weights":    str(weights_path),
            "n_slices":   len(slices),
            "n_tta":      args.tta,
            "volume":     vol_detected,
            "slices":     slice_results,
        }
        with open(args.output, "w") as f:
            json.dump(result_data, f, indent=2)
        print(f"  Results saved → {args.output}")


if __name__ == "__main__":
    main()
