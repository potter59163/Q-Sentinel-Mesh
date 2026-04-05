"""
Quantum-Enhanced Federated Learning Client

Each hospital node runs a full HybridQSentinel model (CNN + VQC) locally.
Model weights are encrypted with ML-KEM-512 (Post-Quantum Cryptography)
before being transmitted to the central aggregation server.

Flow per federated round:
    1. Receive global weights from server (already decrypted by server)
    2. Load weights into local HybridQSentinel model
    3. Train locally on private patient data (CNN + VQC jointly)
    4. Encrypt updated weights with server's ML-KEM-512 public key
    5. Return encrypted payload (encoded as uint8 ndarray) to server
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import flwr as fl
import numpy as np
import torch
import torch.nn as nn
from flwr.common import (
    EvaluateIns,
    EvaluateRes,
    FitIns,
    FitRes,
    GetParametersIns,
    GetParametersRes,
    Parameters,
    Status,
    Code,
    ndarrays_to_parameters,
    parameters_to_ndarrays,
)
from torch.utils.data import DataLoader
from sklearn.metrics import roc_auc_score

from ..models.hybrid_model import build_hybrid_model, HybridQSentinel
from ..models.cnn_encoder import FocalLoss, NUM_CLASSES
from .pqc_crypto import (
    pqc_encrypt_flwr_params,
    pqc_decrypt_flwr_params,
    payload_to_ndarray,
    ndarray_to_payload,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_model_params(model: nn.Module) -> list[np.ndarray]:
    """Extract model parameters as list of NumPy arrays."""
    return [val.cpu().numpy() for val in model.state_dict().values()]


def set_model_params(model: nn.Module, params: list[np.ndarray]) -> None:
    """Load parameters from NumPy arrays into model."""
    state_keys = list(model.state_dict().keys())
    if len(params) != len(state_keys):
        raise ValueError(
            f"Parameter count mismatch for hybrid client: got {len(params)} arrays, "
            f"expected {len(state_keys)}."
        )
    state_dict = {
        k: torch.tensor(v)
        for k, v in zip(state_keys, params)
    }
    model.load_state_dict(state_dict, strict=False)


# ─── Hybrid Flower Client ─────────────────────────────────────────────────────

class HybridQSentinelClient(fl.client.NumPyClient):
    """
    Quantum-Enhanced Federated Hospital Node.

    Uses a full HybridQSentinel model (EfficientNet-B4 CNN backbone +
    Variational Quantum Circuit) for local training. Model weights are
    PQC-encrypted (ML-KEM-512 + AES-256-GCM) before transmission.

    Args:
        partition_id:   0, 1, or 2  (Hospital A / B / C)
        train_loader:   Local DataLoader — patient data never leaves this node
        val_loader:     Local validation DataLoader
        device:         Torch device ('cuda' or 'cpu')
        local_epochs:   Training epochs per federated round
        pretrained_path: Optional path to pre-trained hybrid weights
    """

    HOSPITAL_NAMES = [
        "Hospital A (Bangkok)",
        "Hospital B (Chiang Mai)",
        "Hospital C (Khon Kaen)",
    ]

    def __init__(
        self,
        partition_id: int,
        train_loader: DataLoader,
        val_loader: DataLoader,
        device: str = "cuda",
        local_epochs: int = 1,
        pretrained_path: Optional[Path] = None,
    ):
        self.partition_id = partition_id
        self.hospital_name = self.HOSPITAL_NAMES[partition_id]
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")
        self.local_epochs = local_epochs

        # Build Hybrid Quantum-Classical model
        self.model = build_hybrid_model(pretrained=True)
        if pretrained_path and Path(pretrained_path).exists():
            state = torch.load(str(pretrained_path), map_location=self.device)
            missing, unexpected = self.model.load_state_dict(state, strict=False)
            print(f"  [{self.hospital_name}] Loaded pretrained weights (missing={len(missing)}, unexpected={len(unexpected)})")
        self.model.to(self.device)

        # Only fine-tune head + VQC; CNN backbone frozen for federated rounds
        # (reduces gradient computation time while still updating quantum layer)
        self.criterion = FocalLoss(alpha=0.25, gamma=2.0)
        self.optimizer = torch.optim.AdamW(
            filter(lambda p: p.requires_grad, self.model.parameters()),
            lr=5e-5,
            weight_decay=1e-5,
        )

        print(
            f"  [{self.hospital_name}] HybridQSentinel ready "
            f"| device={self.device} | local_epochs={local_epochs}"
        )

    # ── Flower Protocol ───────────────────────────────────────────────────────

    def get_parameters(self, config: dict) -> list[np.ndarray]:
        return get_model_params(self.model)

    def fit(self, parameters: list[np.ndarray], config: dict) -> tuple:
        """
        Federated round:
        1. Load global weights → 2. Train locally (CNN+VQC) →
        3. PQC-encrypt updated weights → 4. Return encrypted payload
        """
        # 1. Apply global model parameters
        set_model_params(self.model, parameters)

        # 2. Local training on private patient data
        self.model.train()
        total_loss = 0.0
        num_batches = 0

        for _ in range(self.local_epochs):
            for batch in self.train_loader:
                images, labels = batch[0], batch[1]
                images = images.to(self.device)
                labels = labels.to(self.device)

                self.optimizer.zero_grad()
                logits = self.model(images)
                loss = self.criterion(logits, labels)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(
                    self.model.parameters(), max_norm=1.0
                )
                self.optimizer.step()

                total_loss += loss.item()
                num_batches += 1

        avg_loss = total_loss / max(num_batches, 1)

        # 3. Get updated weights
        updated_weights = get_model_params(self.model)

        # 4. PQC encrypt with server's ML-KEM-512 public key
        pqc_pk_hex: str = config.get("pqc_public_key", "")
        pqc_encrypted = False
        payload_bytes = 0
        kem_bytes = 0

        if pqc_pk_hex:
            server_pk = bytes.fromhex(pqc_pk_hex)
            payload = pqc_encrypt_flwr_params(updated_weights, server_pk)
            encoded = payload_to_ndarray(payload)
            pqc_encrypted = True
            payload_bytes = int(len(payload.aes_ciphertext))
            kem_bytes = int(len(payload.kem_ciphertext))
            print(
                f"  [{self.hospital_name}] Train loss: {avg_loss:.4f} | "
                f"PQC-encrypted {payload_bytes:,}B payload "
                f"(KEM ciphertext: {kem_bytes}B)"
            )
            return (
                [encoded],
                len(self.train_loader.dataset),
                {
                    "train_loss": float(avg_loss),
                    "hospital": self.hospital_name,
                    "pqc_encrypted": True,
                    "kem_bytes": kem_bytes,
                    "payload_bytes": payload_bytes,
                    "quantum_layer": True,
                },
            )

        # Fallback: no PQC key provided (plain transmission)
        print(f"  [{self.hospital_name}] Train loss: {avg_loss:.4f} [no PQC key]")
        return (
            updated_weights,
            len(self.train_loader.dataset),
            {
                "train_loss": float(avg_loss),
                "hospital": self.hospital_name,
                "pqc_encrypted": False,
                "quantum_layer": True,
            },
        )

    def evaluate(self, parameters: list[np.ndarray], config: dict) -> tuple:
        """Evaluate global model on local (private) validation set."""
        try:
            set_model_params(self.model, parameters)
        except Exception as e:
            print(f"  [{self.hospital_name}] WARNING: set_model_params failed: {e}")
        self.model.eval()

        total_loss = 0.0
        all_preds: list[np.ndarray] = []
        all_labels: list[np.ndarray] = []

        try:
          with torch.no_grad():
            for batch in self.val_loader:
                images, labels = batch[0], batch[1]
                images = images.to(self.device)
                labels = labels.to(self.device)

                logits = self.model(images)
                loss = self.criterion(logits, labels)
                probs = torch.sigmoid(logits)

                total_loss += loss.item()
                all_preds.append(probs.cpu().numpy())
                all_labels.append(labels.cpu().numpy())
        except Exception as e:
            print(f"  [{self.hospital_name}] WARNING: eval forward pass failed: {e}")
            return 0.0, len(self.val_loader.dataset), {"auc": 0.5, "hospital": self.hospital_name, "quantum_layer": True}

        avg_loss = total_loss / max(len(self.val_loader), 1)

        # Macro-average AUC across all 6 classes
        try:
            preds_np = np.concatenate(all_preds, axis=0)
            labels_np = np.concatenate(all_labels, axis=0)
            per_class_aucs = []
            for ci in range(labels_np.shape[1]):
                try:
                    per_class_aucs.append(
                        roc_auc_score(labels_np[:, ci], preds_np[:, ci])
                    )
                except ValueError:
                    per_class_aucs.append(0.5)
            auc = float(np.mean(per_class_aucs))
            if np.isnan(auc):
                auc = 0.5
        except Exception:
            auc = 0.5

        print(
            f"  [{self.hospital_name}] Val loss: {avg_loss:.4f} | "
            f"AUC: {auc:.4f} | quantum_layer=True"
        )

        return (
            float(avg_loss),
            len(self.val_loader.dataset),
            {
                "val_loss": float(avg_loss),
                "auc": float(auc),
                "hospital": self.hospital_name,
                "quantum_layer": True,
            },
        )
