"""
Q-Sentinel Mesh environment health check.

Use this before running training, dashboard, or multi-machine federated tests.
"""

from __future__ import annotations

import importlib
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore", category=RuntimeWarning, module="src.federated.pqc_crypto")
warnings.filterwarnings("ignore", category=RuntimeWarning)


CHECKS = [
    ("torch", "PyTorch"),
    ("torchvision", "TorchVision"),
    ("timm", "timm"),
    ("pydicom", "pydicom"),
    ("nibabel", "nibabel"),
    ("pennylane", "PennyLane"),
    ("flwr", "Flower"),
    ("sklearn", "scikit-learn"),
    ("cryptography", "cryptography"),
]


def main() -> int:
    failures: list[str] = []

    print("=" * 60)
    print("Q-Sentinel Mesh Health Check")
    print("=" * 60)

    for module_name, label in CHECKS:
        try:
            importlib.import_module(module_name)
            print(f"[OK] {label}")
        except Exception as exc:
            failures.append(f"{label}: {exc}")
            print(f"[FAIL] {label}: {exc}")

    try:
        from src.federated.pqc_crypto import pqc_backend_name, pqc_backend_is_real

        backend = pqc_backend_name()
        if pqc_backend_is_real():
            print(f"[OK] PQC backend: {backend}")
        else:
            failures.append(
                f"PQC backend is not real ({backend}). Install kyber-py or pqcrypto before production federated runs."
            )
            print(f"[FAIL] PQC backend: {backend} (production requires kyber-py or pqcrypto)")
    except Exception as exc:
        failures.append(f"PQC check: {exc}")
        print(f"[FAIL] PQC check: {exc}")

    print()
    if failures:
        print("Environment is NOT production-ready.")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("Environment is production-ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
