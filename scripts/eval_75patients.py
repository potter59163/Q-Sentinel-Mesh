"""
Evaluate CNN Baseline vs Hybrid Quantum on CT-ICH 75 patients
Reports: correct / wrong per patient, per class
"""
import sys, os
sys.path.insert(0, str(Path(__file__).parent.parent))

import torch
import numpy as np
import pandas as pd
from pathlib import Path
from torch.utils.data import DataLoader

NII_DIR  = r"C:\Users\parip\Downloads\CEDT hack\computed-tomography-images-for-intracranial-hemorrhage-detection-and-segmentation-1.3.1\ct_scans"
CSV_PATH = r"C:\Users\parip\Downloads\CEDT hack\computed-tomography-images-for-intracranial-hemorrhage-detection-and-segmentation-1.3.1\hemorrhage_diagnosis_raw_ct.csv"
WEIGHTS  = Path(__file__).parent.parent / "weights"
DEVICE   = "cuda" if torch.cuda.is_available() else "cpu"
SUBTYPES = ["epidural", "intraparenchymal", "intraventricular", "subarachnoid", "subdural", "any"]
THRESHOLD = 0.3   # patient-level threshold (90th percentile of slices)

def load_models():
    from src.models.cnn_encoder import load_baseline
    from src.models.hybrid_model import HybridQSentinel

    cnn = load_baseline(str(WEIGHTS / "high_acc_b4.pth"), DEVICE)
    cnn.eval()

    hybrid = HybridQSentinel()
    hybrid.load_state_dict(torch.load(str(WEIGHTS / "hybrid_qsentinel.pth"), map_location=DEVICE))
    hybrid.to(DEVICE)
    hybrid.eval()
    return cnn, hybrid

def get_patient_gt(csv_path):
    """Return dict {patient_num: np.array([6 classes])} patient-level GT"""
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()
    # columns: PatientNumber, SliceNumber, Intraventricular, Intraparenchymal,
    #          Subarachnoid, Epidural, Subdural, No_Hemorrhage, Fracture_Yes_No
    col_map = {
        "epidural":        "Epidural",
        "intraparenchymal":"Intraparenchymal",
        "intraventricular":"Intraventricular",
        "subarachnoid":    "Subarachnoid",
        "subdural":        "Subdural",
    }
    gt = {}
    for pid, group in df.groupby("PatientNumber"):
        row = []
        for sub in SUBTYPES[:5]:
            col = col_map[sub]
            row.append(int(group[col].max()))  # 1 if ANY slice has it
        row.append(1 if any(row) else 0)       # "any" class
        gt[int(pid)] = np.array(row, dtype=np.float32)
    return gt

def predict_patient(model, nii_path, batch_size=32):
    """Run model on all slices of a .nii volume, return max prob per class"""
    from src.data.nifti_loader import load_nifti_volume
    from src.data.rsna_loader import get_volume_slice_tensor

    vol = load_nifti_volume(nii_path)          # (D, H, W)
    depth = vol.shape[0]
    all_probs = []

    with torch.no_grad():
        for start in range(0, depth, batch_size):
            end = min(start + batch_size, depth)
            batch = torch.cat([
                get_volume_slice_tensor(vol, i) for i in range(start, end)
            ], dim=0).to(DEVICE)
            probs = torch.sigmoid(model(batch)).cpu().numpy()
            all_probs.append(probs)

    all_probs = np.concatenate(all_probs, axis=0)  # (D, 6)
    return np.percentile(all_probs, 90, axis=0)    # (6,) 90th percentile per class

def evaluate_model(model, gt_dict, nii_dir, name):
    nii_dir = Path(nii_dir)
    results = []

    patients = sorted(gt_dict.keys())
    print(f"\n{'='*55}")
    print(f"  {name} — {len(patients)} patients")
    print(f"{'='*55}")

    for pid in patients:
        nii_path = nii_dir / f"{pid:03d}.nii"
        if not nii_path.exists():
            continue

        max_probs = predict_patient(model, nii_path)
        pred      = (max_probs >= THRESHOLD).astype(int)
        gt        = gt_dict[pid].astype(int)

        correct_classes = int((pred == gt).all())   # 1 if ALL 6 classes correct
        any_correct     = int(pred[5] == gt[5])     # "any hemorrhage" correct

        results.append({
            "patient": pid,
            "gt":      gt,
            "pred":    pred,
            "all_correct": correct_classes,
            "any_correct": any_correct,
        })
        status = "✅" if correct_classes else "❌"
        print(f"  Patient {pid:03d} {status}  GT={gt[:5]}  Pred={pred[:5]}")

    # Summary
    n = len(results)
    all_correct  = sum(r["all_correct"] for r in results)
    any_correct  = sum(r["any_correct"] for r in results)

    # Per-class accuracy
    gts   = np.array([r["gt"]   for r in results])
    preds = np.array([r["pred"] for r in results])

    print(f"\n  {'─'*50}")
    print(f"  All-class correct : {all_correct}/{n}  ({100*all_correct/n:.1f}%)")
    print(f"  Any-hem correct   : {any_correct}/{n}  ({100*any_correct/n:.1f}%)")
    print(f"\n  Per-class accuracy:")
    for i, sub in enumerate(SUBTYPES):
        acc = (preds[:, i] == gts[:, i]).mean() * 100
        print(f"    {sub:<20} {acc:.1f}%")

    return results

def main():
    print("Loading models...")
    cnn, hybrid = load_models()

    print("Loading ground truth...")
    gt = get_patient_gt(CSV_PATH)
    print(f"  {len(gt)} patients in CSV")

    r_cnn    = evaluate_model(cnn,    gt, NII_DIR, "CNN Baseline (high_acc_b4)")
    r_hybrid = evaluate_model(hybrid, gt, NII_DIR, "Hybrid Quantum (VQC)")

    # Side-by-side comparison
    print(f"\n{'='*55}")
    print("  COMPARISON SUMMARY")
    print(f"{'='*55}")
    n = min(len(r_cnn), len(r_hybrid))
    cnn_all    = sum(r["all_correct"] for r in r_cnn)
    hybrid_all = sum(r["all_correct"] for r in r_hybrid)
    cnn_any    = sum(r["any_correct"] for r in r_cnn)
    hybrid_any = sum(r["any_correct"] for r in r_hybrid)
    print(f"  {'Metric':<30} {'CNN':>8}  {'Hybrid':>8}")
    print(f"  {'─'*48}")
    print(f"  {'All-class correct':<30} {cnn_all:>5}/{n}   {hybrid_all:>5}/{n}")
    print(f"  {'Any-hemorrhage correct':<30} {cnn_any:>5}/{n}   {hybrid_any:>5}/{n}")

if __name__ == "__main__":
    main()
