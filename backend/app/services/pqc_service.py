"""Thin wrapper around src/federated/pqc_crypto.py for the PQC demo endpoint."""
import os
import sys
import time
from pathlib import Path

# Add repo root to sys.path so src/ is importable
REPO_ROOT = Path(__file__).parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.models.pqc import PQCDemoResponse


class PQCService:
    def run_demo(self) -> PQCDemoResponse:
        os.environ.setdefault("QSENTINEL_ALLOW_INSECURE_PQC_FALLBACK", "1")
        try:
            from src.federated.pqc_crypto import (
                generate_pqc_keypair,
                encrypt_weights,
                decrypt_weights,
            )
            import numpy as np

            # KeyGen
            t0 = time.perf_counter()
            keypair = generate_pqc_keypair()
            pub_key = keypair.public_key if hasattr(keypair, "public_key") else keypair[0]
            sec_key = keypair.secret_key if hasattr(keypair, "secret_key") else keypair[1]
            keygen_ms = (time.perf_counter() - t0) * 1000

            import pickle
            dummy = np.random.randn(10).astype(np.float32)
            dummy_bytes = pickle.dumps({"w": dummy})  # encrypt_weights expects bytes

            # Encrypt
            t1 = time.perf_counter()
            payload = encrypt_weights(dummy_bytes, pub_key)
            encrypt_ms = (time.perf_counter() - t1) * 1000

            # Decrypt
            t2 = time.perf_counter()
            _ = decrypt_weights(payload, sec_key)
            decrypt_ms = (time.perf_counter() - t2) * 1000

            return PQCDemoResponse(
                public_key_bytes=len(pub_key),
                secret_key_bytes=len(sec_key),
                kem_ciphertext_bytes=len(payload.kem_ciphertext),
                aes_ciphertext_bytes=len(payload.aes_ciphertext),
                keygen_ms=round(keygen_ms, 2),
                encrypt_ms=round(encrypt_ms, 2),
                decrypt_ms=round(decrypt_ms, 2),
                success=True,
                backend="kyber-py" if not os.getenv("_PQC_FALLBACK") else "demo-fallback",
            )
        except Exception as e:
            return PQCDemoResponse(
                public_key_bytes=0,
                secret_key_bytes=0,
                kem_ciphertext_bytes=0,
                aes_ciphertext_bytes=0,
                keygen_ms=0,
                encrypt_ms=0,
                decrypt_ms=0,
                success=False,
                backend="error",
                error=str(e),
            )


pqc_service = PQCService()
