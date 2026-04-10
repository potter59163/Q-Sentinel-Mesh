"""
Select 10 best demo cases from inference results already obtained.
Criteria: correct hemorrhage detection (positive), diverse hemorrhage types, high confidence.
Prefer exact subtype matches.
"""
import shutil, json, time
from pathlib import Path

ROOT = Path(__file__).parent.parent
CT_DIR = Path(r"C:\Users\parip\Downloads\CEDT hack\computed-tomography-images-for-intracranial-hemorrhage-detection-and-segmentation-1.3.1\ct_scans")
SAMPLES_DIR = ROOT / "data" / "samples"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

# All correct cases from inference run (hemorrhage-positive, correctly detected as positive)
# Format: (pid, gt_class, pred_class, confidence)
correct_cases = [
    ("049", "epidural",          "epidural",          0.60),
    ("050", "intraparenchymal",  "subarachnoid",      0.74),
    ("051", "subdural",          "subarachnoid",      0.75),
    ("052", "epidural",          "epidural",          0.68),
    ("053", "epidural",          "subarachnoid",      0.71),
    ("058", "intraparenchymal",  "epidural",          0.62),
    ("066", "epidural",          "subarachnoid",      0.72),
    ("067", "epidural",          "subarachnoid",      0.71),
    ("068", "epidural",          "epidural",          0.62),
    ("069", "intraparenchymal",  "subarachnoid",      0.69),
    ("070", "epidural",          "subarachnoid",      0.70),
    ("071", "subdural",          "subdural",          0.68),
    ("072", "intraparenchymal",  "epidural",          0.61),
    ("073", "epidural",          "subarachnoid",      0.70),
    ("074", "epidural",          "subarachnoid",      0.71),
    ("079", "intraparenchymal",  "epidural",          0.68),
    ("080", "subarachnoid",      "subdural",          0.73),
    ("081", "subdural",          "subarachnoid",      0.74),
    ("082", "subarachnoid",      "epidural",          0.61),
    ("083", "epidural",          "epidural",          0.67),
    ("084", "subarachnoid",      "subarachnoid",      0.72),
    ("085", "intraventricular",  "intraparenchymal",  0.70),
    ("086", "epidural",          "subarachnoid",      0.70),
    ("087", "epidural",          "subarachnoid",      0.72),
    ("088", "epidural",          "subarachnoid",      0.74),
    ("093", "epidural",          "intraparenchymal",  0.68),
    ("094", "subarachnoid",      "subdural",          0.75),
    ("097", "epidural",          "subarachnoid",      0.71),
]

# Score each: exact_match gets +0.1 bonus
def score(c):
    bonus = 0.10 if c[1] == c[2] else 0.0
    return c[3] + bonus

cases_scored = sorted(correct_cases, key=score, reverse=True)

# Greedy diverse pick: 1 of each hemorrhage type first, then fill by score
TYPES = ["epidural", "subdural", "subarachnoid", "intraparenchymal", "intraventricular"]
chosen = []
seen_types = set()

# First pass: pick best (highest score) of each type
for t in TYPES:
    for c in cases_scored:
        if c[1] == t and c[0] not in [x[0] for x in chosen]:
            chosen.append(c)
            seen_types.add(t)
            break

# Second pass: fill remaining slots with highest-scoring remaining cases
for c in cases_scored:
    if len(chosen) >= 10:
        break
    if c[0] not in [x[0] for x in chosen]:
        chosen.append(c)

chosen = chosen[:10]

print("Selected 10 demo cases:")
print("-" * 62)
for c in chosen:
    exact = " [EXACT MATCH]" if c[1] == c[2] else ""
    print(f"  P{c[0]}  gt={c[1]:<20}  pred={c[2]:<20}  conf={c[3]:.2f}{exact}")

# Copy files
for f in SAMPLES_DIR.glob("*.nii"):
    f.unlink()

for c in chosen:
    src = CT_DIR / f"{c[0]}.nii"
    dst = SAMPLES_DIR / f"{c[0]}.nii"
    shutil.copy2(src, dst)
    print(f"  copied {c[0]}.nii")

# Save manifest
manifest = {
    "generated": "2026-04-10",
    "note": "10 demo cases — all hemorrhage-positive, correctly detected by Q-Sentinel Hybrid model",
    "cases": [
        {
            "pid": c[0],
            "filename": f"{c[0]}.nii",
            "gt_class": c[1],
            "pred_class": c[2],
            "confidence": c[3],
            "exact_match": c[1] == c[2],
        }
        for c in chosen
    ]
}
(SAMPLES_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))
print(f"\nManifest saved. {len(chosen)} files in data/samples/")
print(json.dumps(manifest, indent=2))
