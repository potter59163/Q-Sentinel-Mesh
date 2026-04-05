"""Smoke tests for all Q-Sentinel Mesh modules."""
import sys
sys.path.insert(0, ".")

errors = []

# Test 1: Mock volume
try:
    from src.data.mock_data import generate_mock_volume
    vol = generate_mock_volume("epidural", depth=10, size=64, seed=42)
    assert vol.shape == (10, 64, 64), f"Bad shape: {vol.shape}"
    print(f"[OK] Mock volume: shape={vol.shape}, HU=[{vol.min():.0f}, {vol.max():.0f}]")
except Exception as e:
    errors.append(f"[FAIL] Mock volume: {e}")

# Test 2: RSNA loader functions
try:
    import numpy as np
    from src.data.rsna_loader import apply_window, SUBTYPES
    dummy_hu = np.random.uniform(-200, 200, (64, 64)).astype("float32")
    windowed = apply_window(dummy_hu, center=40, width=80)
    assert windowed.min() >= 0.0 and windowed.max() <= 1.0
    print(f"[OK] RSNA loader: windowing OK, subtypes={SUBTYPES}")
except Exception as e:
    errors.append(f"[FAIL] RSNA loader: {e}")

# Test 3: CNN Encoder
try:
    import torch
    from src.models.cnn_encoder import build_efficientnet_b4
    model = build_efficientnet_b4(pretrained=False)
    x = torch.randn(1, 3, 224, 224)
    with torch.no_grad():
        out = model(x)
    assert out.shape == (1, 6), f"Bad output shape: {out.shape}"
    print(f"[OK] CNN Encoder: output shape={out.shape}")
except Exception as e:
    errors.append(f"[FAIL] CNN Encoder: {e}")

# Test 4: VQC Layer
try:
    import torch
    from src.models.vqc_layer import VQCModule
    vqc = VQCModule(feature_dim=32)
    x = torch.randn(2, 32)
    out = vqc(x)
    assert out.shape == (2, 4), f"Bad VQC output: {out.shape}"
    print(f"[OK] VQC Layer: output shape={out.shape}")
except Exception as e:
    errors.append(f"[FAIL] VQC Layer: {e}")

# Test 5: Benchmark metrics
try:
    from src.utils.metrics import generate_benchmark_data
    bm = generate_benchmark_data()
    assert len(bm["nodes"]) == 3
    print(f"[OK] Metrics: nodes={bm['nodes']}, Q-AUC={[round(x,3) for x in bm['qsentinel_auc']]}")
except Exception as e:
    errors.append(f"[FAIL] Metrics: {e}")

# Test 6: PQC Encryption
try:
    import numpy as np
    from src.federated.pqc_crypto import (
        generate_pqc_keypair,
        encrypt_weights,
        decrypt_weights,
        pqc_backend_name,
        pqc_backend_is_real,
    )
    if not pqc_backend_is_real():
        print(f"[SKIP] PQC Crypto: real backend unavailable ({pqc_backend_name()})")
    else:
        kp = generate_pqc_keypair()
        dummy = np.random.randn(16).astype("float32").tobytes()
        payload = encrypt_weights(dummy, kp.public_key)
        recovered = decrypt_weights(payload, kp.secret_key)
        assert recovered == dummy, "Decryption mismatch!"
        print(f"[OK] PQC Crypto: encrypt/decrypt verified, pubkey={len(kp.public_key)} bytes")
except Exception as e:
    errors.append(f"[FAIL] PQC Crypto: {e}")

# Test 7: Mock Dataset
try:
    import torch
    from src.data.mock_data import MockCTDataset
    ds = MockCTDataset(n_samples=10, img_size=64)
    img, label, uid = ds[0]
    assert img.shape == (3, 64, 64)
    assert label.shape == (6,)
    print(f"[OK] MockCTDataset: img={img.shape}, label={label.shape}, uid={uid}")
except Exception as e:
    errors.append(f"[FAIL] MockCTDataset: {e}")

# Test 8: NIfTI Loader (Real CT-ICH Dataset)
try:
    from pathlib import Path
    _dataset_dir = Path(__file__).parent.parent / "computed-tomography-images-for-intracranial-hemorrhage-detection-and-segmentation-1.3.1"
    _nii_dir  = _dataset_dir / "ct_scans"
    _csv_path = _dataset_dir / "hemorrhage_diagnosis_raw_ct.csv"
    if _nii_dir.exists() and _csv_path.exists():
        from src.data.nifti_loader import parse_ich_labels, load_nifti_volume, ICHDataset
        labels_df = parse_ich_labels(_csv_path)
        assert "epidural" in labels_df.columns
        n_slices = len(labels_df)
        n_hemorrhage = int((labels_df["any"] == 1).sum())
        # Load one volume
        first_nii = sorted(_nii_dir.glob("*.nii"))[0]
        vol = load_nifti_volume(first_nii)
        assert vol.ndim == 3
        print(f"[OK] NIfTI Loader: {n_slices} slices, {n_hemorrhage} hemorrhage, vol={vol.shape}")
        # Test full dataset
        import torch
        ds = ICHDataset(_nii_dir, _csv_path, img_size=64, patients=[int(first_nii.stem)])
        if len(ds) > 0:
            img, label, uid = ds[0]
            assert img.shape == (3, 64, 64)
            assert label.shape == (6,)
            print(f"[OK] ICHDataset: img={img.shape}, label={label.tolist()}, uid={uid}")
        else:
            print(f"[OK] ICHDataset: created (no slices for test patient, ok)")
    else:
        print(f"[SKIP] NIfTI Loader: dataset not found at {_dataset_dir}")
except Exception as e:
    errors.append(f"[FAIL] NIfTI Loader: {e}")

# Summary
print()
if errors:
    print(f"{'='*50}")
    print(f"FAILED ({len(errors)} errors):")
    for err in errors:
        print(f"  {err}")
else:
    print("=" * 50)
    print("ALL SMOKE TESTS PASSED!")
    print("Run: streamlit run dashboard/app.py")
