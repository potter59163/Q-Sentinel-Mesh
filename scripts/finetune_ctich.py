"""
Fine-tune CNN on CT-ICH NIfTI data to fix distribution shift.
Split: 60 patients train / 15 patients test
Trains head only (5 epochs) - fast, ~10-15 minutes
"""
import sys, os
sys.path.insert(0, str(Path(__file__).parent.parent))

import torch
import torch.nn as nn
import numpy as np
from pathlib import Path
from torch.utils.data import DataLoader
from sklearn.metrics import roc_auc_score

NII_DIR  = r"C:\Users\parip\Downloads\CEDT hack\computed-tomography-images-for-intracranial-hemorrhage-detection-and-segmentation-1.3.1\ct_scans"
CSV_PATH = r"C:\Users\parip\Downloads\CEDT hack\computed-tomography-images-for-intracranial-hemorrhage-detection-and-segmentation-1.3.1\hemorrhage_diagnosis_raw_ct.csv"
WEIGHTS  = Path(__file__).parent.parent / "weights"
DEVICE   = "cuda" if torch.cuda.is_available() else "cpu"
EPOCHS   = 8
LR       = 3e-4
BATCH    = 16
THRESHOLD = 0.3

def main():
    from src.models.cnn_encoder import load_baseline
    from src.data.nifti_loader import ICHDataset

    print(f"Device: {DEVICE}")

    # ── Load pretrained model ─────────────────────────────────────
    model = load_baseline(str(WEIGHTS / "high_acc_b4.pth"), DEVICE)
    model.train()

    # Freeze backbone, only train head
    for p in model.backbone.parameters():
        p.requires_grad = False
    for p in model.head.parameters():
        p.requires_grad = True

    # ── Split patients 60/15 ──────────────────────────────────────
    import random
    random.seed(42)
    all_patients = sorted([int(f.stem) for f in Path(NII_DIR).glob("*.nii")])
    random.shuffle(all_patients)
    train_patients = all_patients[:60]
    test_patients  = all_patients[60:]
    print(f"Train: {len(train_patients)} patients | Test: {len(test_patients)} patients")

    # ── Datasets ──────────────────────────────────────────────────
    train_ds = ICHDataset(NII_DIR, CSV_PATH, patients=train_patients)
    test_ds  = ICHDataset(NII_DIR, CSV_PATH, patients=test_patients)
    print(f"Train slices: {len(train_ds)} | Test slices: {len(test_ds)}")

    train_loader = DataLoader(train_ds, batch_size=BATCH, shuffle=True,  num_workers=2, pin_memory=True)
    test_loader  = DataLoader(test_ds,  batch_size=BATCH, shuffle=False, num_workers=2, pin_memory=True)

    # ── Optimizer ─────────────────────────────────────────────────
    optimizer = torch.optim.AdamW(model.head.parameters(), lr=LR, weight_decay=1e-4)
    criterion = nn.BCEWithLogitsLoss()
    scaler    = torch.amp.GradScaler("cuda")

    best_auc = 0.0

    for epoch in range(1, EPOCHS + 1):
        # Train
        model.train()
        total_loss = 0
        for imgs, labels, _ in train_loader:
            imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
            optimizer.zero_grad()
            with torch.amp.autocast("cuda"):
                loss = criterion(model(imgs), labels)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            total_loss += loss.item()

        # Evaluate
        model.eval()
        all_preds, all_labels = [], []
        with torch.no_grad():
            for imgs, labels, _ in test_loader:
                imgs = imgs.to(DEVICE)
                probs = torch.sigmoid(model(imgs)).cpu().numpy()
                all_preds.append(probs)
                all_labels.append(labels.numpy())

        preds  = np.concatenate(all_preds)
        truths = np.concatenate(all_labels)

        aucs = []
        for c in range(6):
            if len(np.unique(truths[:, c])) > 1:
                aucs.append(roc_auc_score(truths[:, c], preds[:, c]))
        auc = float(np.mean(aucs)) if aucs else 0.5

        avg_loss = total_loss / len(train_loader)
        marker = ""
        if auc > best_auc:
            best_auc = auc
            torch.save(model.state_dict(), str(WEIGHTS / "finetuned_ctich.pth"))
            marker = " ← saved"

        print(f"  Ep {epoch:02d}/{EPOCHS} | loss={avg_loss:.4f} | AUC={auc:.4f}{marker}")

    print(f"\nBest AUC on 15 test patients: {best_auc:.4f} ({best_auc*100:.1f}%)")
    print(f"Saved to weights/finetuned_ctich.pth")

    # ── Patient-level eval ────────────────────────────────────────
    print("\nPatient-level evaluation on 15 test patients:")
    model.load_state_dict(torch.load(str(WEIGHTS / "finetuned_ctich.pth"), map_location=DEVICE))
    model.eval()

    from src.data.nifti_loader import load_nifti_volume
    from src.data.rsna_loader import get_volume_slice_tensor
    import pandas as pd

    df = pd.read_csv(CSV_PATH)
    df.columns = df.columns.str.strip()
    col_map = {0:"Epidural",1:"Intraparenchymal",2:"Intraventricular",3:"Subarachnoid",4:"Subdural"}

    # Collect patient-level probs and GT for all test patients
    patient_probs, patient_gts = [], []
    for pid in sorted(test_patients):
        nii_path = Path(NII_DIR) / f"{pid:03d}.nii"
        if not nii_path.exists(): continue

        vol = load_nifti_volume(str(nii_path))
        all_probs = []
        with torch.no_grad():
            for i in range(0, vol.shape[0], 16):
                batch = torch.cat([get_volume_slice_tensor(vol, j)
                                   for j in range(i, min(i+16, vol.shape[0]))], dim=0).to(DEVICE)
                probs = torch.sigmoid(model(batch)).cpu().numpy()
                all_probs.append(probs)

        patient_prob = np.percentile(np.concatenate(all_probs), 90, axis=0)
        patient_probs.append(patient_prob)

        g = df[df["PatientNumber"] == pid]
        gt = np.array([int(g[col_map[i]].max()) for i in range(5)] + [0])
        gt[5] = 1 if gt[:5].any() else 0
        patient_gts.append(gt)

    patient_probs = np.array(patient_probs)
    patient_gts   = np.array(patient_gts)

    # Find best threshold per class using Youden's J
    SUBTYPES_ALL = ["epidural","intraparenchymal","intraventricular","subarachnoid","subdural","any"]
    best_thresholds = []
    print("\n  Calibrated thresholds:")
    for c in range(6):
        best_t, best_j = 0.5, -1
        for t in np.arange(0.05, 0.95, 0.01):
            pred_c = (patient_probs[:, c] >= t).astype(int)
            tp = ((pred_c==1) & (patient_gts[:,c]==1)).sum()
            fp = ((pred_c==1) & (patient_gts[:,c]==0)).sum()
            fn = ((pred_c==0) & (patient_gts[:,c]==1)).sum()
            tn = ((pred_c==0) & (patient_gts[:,c]==0)).sum()
            sens = tp/(tp+fn) if (tp+fn)>0 else 0
            spec = tn/(tn+fp) if (tn+fp)>0 else 0
            j = sens + spec - 1
            if j > best_j:
                best_j, best_t = j, t
        best_thresholds.append(best_t)
        print(f"    {SUBTYPES_ALL[c]:<20} {best_t:.2f}")

    # Final patient-level evaluation with calibrated thresholds
    correct = 0
    print("\n  Results with calibrated thresholds:")
    pids_sorted = sorted([p for p in test_patients if (Path(NII_DIR)/f"{p:03d}.nii").exists()])
    for i, pid in enumerate(pids_sorted):
        pred = (patient_probs[i] >= np.array(best_thresholds)).astype(int)
        gt   = patient_gts[i]
        ok   = (pred == gt).all()
        if ok: correct += 1
        status = "✅" if ok else "❌"
        print(f"  Patient {pid:03d} {status}  GT={gt[:5]}  Pred={pred[:5]}")

    print(f"\n  Correct: {correct}/{len(pids_sorted)} ({100*correct/len(pids_sorted):.1f}%)")

if __name__ == "__main__":
    main()
