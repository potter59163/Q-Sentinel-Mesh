"""
Post-Quantum Cryptography (PQC) — ML-KEM-512 Weight Encryption

Uses CRYSTALS-Kyber (NIST FIPS 203 standardized as ML-KEM-512)
for key encapsulation, combined with AES-256-GCM for symmetric
encryption of model weight bytes.

Flow:
    Sender (Hospital Node):
        1. Encapsulate shared secret using server's ML-KEM public key
        2. Derive AES-256 key from shared secret (HKDF-SHA256)
        3. Encrypt weights with AES-256-GCM
        4. Send: {kem_ciphertext, aes_ciphertext, nonce, tag}

    Receiver (Central Server):
        1. Decapsulate shared secret using ML-KEM secret key
        2. Derive same AES-256 key
        3. Decrypt weights
"""

from __future__ import annotations

import os
import struct
from dataclasses import dataclass

import numpy as np

# ML-KEM-512 (NIST FIPS 203 / CRYSTALS-Kyber)
from pqcrypto.kem.ml_kem_512 import generate_keypair, encrypt as kem_encrypt, decrypt as kem_decrypt

# AES-256-GCM symmetric encryption
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes


# ─── Key Pair ─────────────────────────────────────────────────────────────────

@dataclass
class PQCKeyPair:
    public_key: bytes
    secret_key: bytes


def generate_pqc_keypair() -> PQCKeyPair:
    """Generate a fresh ML-KEM-512 key pair."""
    public_key, secret_key = generate_keypair()
    return PQCKeyPair(public_key=public_key, secret_key=secret_key)


# ─── Key Derivation ───────────────────────────────────────────────────────────

def _derive_aes_key(shared_secret: bytes, salt: bytes = b"q-sentinel-mesh") -> bytes:
    """
    Derive a 256-bit AES key from the ML-KEM shared secret using HKDF-SHA256.
    """
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=b"pqc-weight-encryption",
    )
    return hkdf.derive(shared_secret)


# ─── Encryption ───────────────────────────────────────────────────────────────

@dataclass
class EncryptedPayload:
    """Encrypted model update payload for transmission over network."""
    kem_ciphertext: bytes    # from ML-KEM encapsulation
    aes_ciphertext: bytes    # AES-256-GCM encrypted weights
    nonce: bytes             # 12-byte AES-GCM nonce
    salt: bytes              # HKDF salt


def encrypt_weights(
    weights_bytes: bytes,
    public_key: bytes,
) -> EncryptedPayload:
    """
    Encrypt model weight bytes using ML-KEM-512 + AES-256-GCM.

    Args:
        weights_bytes: Serialized model weights (numpy bytes or torch state_dict bytes)
        public_key:    Server's ML-KEM-512 public key

    Returns:
        EncryptedPayload ready for transmission
    """
    # 1. Key Encapsulation: generate shared secret
    kem_ciphertext, shared_secret = kem_encrypt(public_key)

    # 2. Random salt and nonce for each transmission
    salt = os.urandom(16)
    nonce = os.urandom(12)

    # 3. Derive AES key
    aes_key = _derive_aes_key(shared_secret, salt)

    # 4. Encrypt with AES-256-GCM (authenticated encryption)
    aesgcm = AESGCM(aes_key)
    aes_ciphertext = aesgcm.encrypt(nonce, weights_bytes, associated_data=None)

    return EncryptedPayload(
        kem_ciphertext=kem_ciphertext,
        aes_ciphertext=aes_ciphertext,
        nonce=nonce,
        salt=salt,
    )


def decrypt_weights(
    payload: EncryptedPayload,
    secret_key: bytes,
) -> bytes:
    """
    Decrypt model weight bytes using ML-KEM-512 + AES-256-GCM.

    Args:
        payload:    EncryptedPayload from transmitting node
        secret_key: Server's ML-KEM-512 secret key

    Returns:
        Decrypted weight bytes
    """
    # 1. Key Decapsulation: recover shared secret
    shared_secret = kem_decrypt(secret_key, payload.kem_ciphertext)

    # 2. Derive same AES key
    aes_key = _derive_aes_key(shared_secret, payload.salt)

    # 3. Decrypt
    aesgcm = AESGCM(aes_key)
    return aesgcm.decrypt(payload.nonce, payload.aes_ciphertext, associated_data=None)


# ─── NumPy Weight Serialization ───────────────────────────────────────────────

def numpy_weights_to_bytes(weights: list[np.ndarray]) -> bytes:
    """Serialize a list of numpy arrays (model weights) to bytes."""
    import io
    buf = io.BytesIO()
    np.savez(buf, *weights)
    return buf.getvalue()


def bytes_to_numpy_weights(data: bytes) -> list[np.ndarray]:
    """Deserialize bytes back to a list of numpy arrays."""
    import io
    buf = io.BytesIO(data)
    npz = np.load(buf, allow_pickle=False)
    return [npz[k] for k in sorted(npz.keys())]


# ─── Payload Serialization (for Flower transmission) ─────────────────────────

def payload_to_bytes(payload: EncryptedPayload) -> bytes:
    """Serialize EncryptedPayload to bytes for embedding in numpy array."""
    kem_ct = payload.kem_ciphertext
    aes_ct = payload.aes_ciphertext
    return (
        struct.pack(">I", len(kem_ct)) + kem_ct
        + struct.pack(">I", len(aes_ct)) + aes_ct
        + payload.nonce   # always 12 bytes
        + payload.salt    # always 16 bytes
    )


def bytes_to_payload(data: bytes) -> EncryptedPayload:
    """Deserialize bytes back to EncryptedPayload."""
    offset = 0
    kem_len = struct.unpack(">I", data[offset:offset + 4])[0]; offset += 4
    kem_ct = data[offset:offset + kem_len]; offset += kem_len
    aes_len = struct.unpack(">I", data[offset:offset + 4])[0]; offset += 4
    aes_ct = data[offset:offset + aes_len]; offset += aes_len
    nonce = data[offset:offset + 12]; offset += 12
    salt = data[offset:offset + 16]
    return EncryptedPayload(kem_ciphertext=kem_ct, aes_ciphertext=aes_ct, nonce=nonce, salt=salt)


def payload_to_ndarray(payload: EncryptedPayload) -> np.ndarray:
    """Encode EncryptedPayload as uint8 numpy array (Flower-compatible)."""
    return np.frombuffer(payload_to_bytes(payload), dtype=np.uint8).copy()


def ndarray_to_payload(arr: np.ndarray) -> EncryptedPayload:
    """Decode uint8 numpy array back to EncryptedPayload."""
    return bytes_to_payload(arr.tobytes())


# ─── High-Level Helpers for Flower Integration ────────────────────────────────

def pqc_encrypt_flwr_params(
    parameters: list[np.ndarray],
    public_key: bytes,
) -> EncryptedPayload:
    """Encrypt Flower NumPy parameter list for PQC-protected transmission."""
    weight_bytes = numpy_weights_to_bytes(parameters)
    return encrypt_weights(weight_bytes, public_key)


def pqc_decrypt_flwr_params(
    payload: EncryptedPayload,
    secret_key: bytes,
) -> list[np.ndarray]:
    """Decrypt PQC-protected payload back to Flower NumPy parameter list."""
    weight_bytes = decrypt_weights(payload, secret_key)
    return bytes_to_numpy_weights(weight_bytes)
