"""
Find 10 best demo cases where AI predictions match ground truth.
Runs auto-triage inference via backend API, compares to dataset labels.
Copies chosen .nii files to data/samples/.
"""
import sys, shutil, json, time
from pathlib import Path
import requests
import pandas as pd

ROOT = Path(__file__).parent.parent
DATASET = Path(r"C:\Users\parip\Downloads\CEDT hack\computed-tomography-images-for-intracranial-hemorrhage-detection-and-segmentation-1.3.1")
CT_DIR = DATASET / "ct_scans"
SAMPLES_DIR = ROOT / "data" / "samples"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

API = "http://localhost:8001"

# ── Auth ────────────────────────────────────────────────────────────────────
r = requests.post(f"{API}/api/auth/login", json={"password": "qsentinel2026"}, timeout=10)
r.raise_for_status()
TOKEN = r.json()["access_token"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
print(f"[auth] OK")

# ── Ground truth: aggregate per patient ─────────────────────────────────────
df = pd.read_csv(DATASET / "hemorrhage_diagnosis_raw_ct.csv")
agg = df.groupby("PatientNumber").agg(
    iv=("Intraventricular", "max"),
    ip=("Intraparenchymal", "max"),
    sah=("Subarachnoid", "max"),
    edh=("Epidural", "max"),
    sdh=("Subdural", "max"),
    no_hem=("No_Hemorrhage", "min"),
).reset_index()
agg["has_hemorrhage"] = 1 - agg["no_hem"]

def gt_top_class(row):
    """Which hemorrhage type is present? Returns 'any' if positive, 'no_hemorrhage' if negative."""
    if row["has_hemorrhage"] == 0:
        return "no_hemorrhage"
    for col, name in [("edh","epidural"),("sdh","subdural"),("sah","subarachnoid"),
                       ("ip","intraparenchymal"),("iv","intraventricular")]:
        if row[col] == 1:
            return name
    return "any"

agg["gt_class"] = agg.apply(gt_top_class, axis=1)
gt_map = dict(zip(agg["PatientNumber"].astype(str).str.zfill(3), zip(agg["has_hemorrhage"], agg["gt_class"])))

# List all available patient IDs in dataset
all_patients = sorted([p.stem for p in CT_DIR.glob("*.nii")])
print(f"[dataset] {len(all_patients)} patients found")

# ── Run inference on each patient ───────────────────────────────────────────
THRESHOLD = 0.15
results = []

for pid in all_patients:
    nii_path = CT_DIR / f"{pid}.nii"
    # Upload CT
    try:
        with open(nii_path, "rb") as f:
            up = requests.post(
                f"{API}/api/ct/upload",
                files={"file": (f"{pid}.nii", f, "application/octet-stream")},
                headers=HEADERS,
                timeout=60,
            )
        up.raise_for_status()
        meta = up.json()
        s3_key = meta["s3_key"]
        slice_count = meta["slice_count"]
    except Exception as e:
        print(f"  [skip] {pid}: upload failed — {e}")
        continue

    # Predict with auto-triage hybrid
    try:
        pr = requests.post(
            f"{API}/api/predict",
            json={
                "s3_key": s3_key,
                "slice_idx": slice_count // 2,
                "model_type": "hybrid",
                "threshold": THRESHOLD,
                "auto_triage": True,
            },
            headers=HEADERS,
            timeout=120,
        )
        pr.raise_for_status()
        pred = pr.json()
    except Exception as e:
        print(f"  [skip] {pid}: predict failed — {e}")
        continue

    prob_any = pred["probabilities"].get("any", 0)
    pred_positive = prob_any >= THRESHOLD
    pred_class = pred["top_class"]
    confidence = pred["confidence"]

    # Ground truth
    gt_key = pid.zfill(3)
    gt_has_hem, gt_class = gt_map.get(gt_key, (None, None))
    if gt_has_hem is None:
        print(f"  [skip] {pid}: not in labels CSV")
        continue

    gt_positive = bool(gt_has_hem)
    correct = (pred_positive == gt_positive)

    results.append({
        "pid": pid,
        "gt_positive": gt_positive,
        "gt_class": gt_class,
        "pred_positive": pred_positive,
        "pred_class": pred_class,
        "confidence": confidence,
        "prob_any": prob_any,
        "correct": correct,
    })

    status = "OK" if correct else "XX"
    print(f"  {status} P{pid}: gt={gt_class} | pred={pred_class} conf={confidence:.2f} any={prob_any:.2f}")
    time.sleep(0.2)

# ── Select 10 best correct cases with class diversity ───────────────────────
correct_cases = [r for r in results if r["correct"]]
wrong_cases   = [r for r in results if not r["correct"]]

print(f"\n[summary] {len(correct_cases)} correct / {len(results)} total")

# Prefer: mix of positive+negative, sorted by confidence
correct_pos = sorted([r for r in correct_cases if r["gt_positive"]], key=lambda x: -x["confidence"])
correct_neg = sorted([r for r in correct_cases if not r["gt_positive"]], key=lambda x: -x["confidence"])

# Aim for 7 positive + 3 negative (or adjust if not enough)
n_pos = min(7, len(correct_pos))
n_neg = min(10 - n_pos, len(correct_neg))
n_pos = 10 - n_neg  # fill remainder with positive

chosen = correct_pos[:n_pos] + correct_neg[:n_neg]

# Ensure class diversity in positives - prefer different hemorrhage types
seen_classes = set()
diverse = []
rest = []
for r in correct_pos:
    if r["gt_class"] not in seen_classes and len(diverse) < n_pos:
        seen_classes.add(r["gt_class"])
        diverse.append(r)
    else:
        rest.append(r)
# Fill remaining slots from rest
while len(diverse) < n_pos and rest:
    diverse.append(rest.pop(0))

chosen = diverse[:n_pos] + correct_neg[:n_neg]
chosen = chosen[:10]

print(f"\n[chosen] {len(chosen)} demo cases:")
for r in chosen:
    hem_tag = f"({r['gt_class']})" if r["gt_positive"] else "(no hemorrhage)"
    print(f"  P{r['pid']} {hem_tag} -> pred={r['pred_class']} conf={r['confidence']:.2f}")

# ── Copy files to data/samples/ ─────────────────────────────────────────────
# Clear existing samples
for f in SAMPLES_DIR.glob("*.nii"):
    f.unlink()

for r in chosen:
    src = CT_DIR / f"{r['pid']}.nii"
    dst = SAMPLES_DIR / f"{r['pid']}.nii"
    shutil.copy2(src, dst)
    print(f"  copied {r['pid']}.nii → data/samples/")

# Save manifest
manifest = {
    "generated": time.strftime("%Y-%m-%d"),
    "cases": [
        {
            "pid": r["pid"],
            "gt_class": r["gt_class"],
            "gt_positive": r["gt_positive"],
            "pred_class": r["pred_class"],
            "confidence": round(r["confidence"], 4),
            "prob_any": round(r["prob_any"], 4),
        }
        for r in chosen
    ]
}
manifest_path = SAMPLES_DIR / "manifest.json"
manifest_path.write_text(json.dumps(manifest, indent=2))
print(f"\n[done] manifest saved to {manifest_path}")
print(json.dumps(manifest, indent=2))
