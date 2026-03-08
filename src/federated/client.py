"""
Flower Federated Learning Client

Each client represents a simulated hospital node with:
- Its own partition of the RSNA dataset
- Local EfficientNet-B4 model
- PQC-encrypted weight transmission
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Optional

import flwr as fl
import numpy as np
import torch
import torch.nn as nn
from flwr.common import (
    Code,
    EvaluateIns,
    EvaluateRes,
    FitIns,
    FitRes,
    GetParametersIns,
    GetParametersRes,
    Parameters,
    Status,
    ndarrays_to_parameters,
    parameters_to_ndarrays,
)
from torch.utils.data import DataLoader, Subset
from sklearn.metrics import roc_auc_score

from ..models.cnn_encoder import build_efficientnet_b4, FocalLoss


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_model_params(model: nn.Module) -> list[np.ndarray]:
    """Extract model parameters as list of NumPy arrays."""
    return [val.cpu().numpy() for val in model.state_dict().values()]


def set_model_params(model: nn.Module, params: list[np.ndarray]) -> None:
    """Load parameters from NumPy arrays into model."""
    state_dict = {
        k: torch.tensor(v)
        for k, v in zip(model.state_dict().keys(), params)
    }
    model.load_state_dict(state_dict, strict=True)


# ─── Flower Client ────────────────────────────────────────────────────────────

class QSentinelClient(fl.client.NumPyClient):
    """
    Simulated hospital node client.

    Args:
        partition_id:  0, 1, or 2 (Hospital A, B, C)
        train_loader:  Local training DataLoader
        val_loader:    Local validation DataLoader
        device:        Torch device string
        epochs:        Local training epochs per round
    """

    HOSPITAL_NAMES = ["Hospital A (Bangkok)", "Hospital B (Chiang Mai)", "Hospital C (Khon Kaen)"]

    def __init__(
        self,
        partition_id: int,
        train_loader: DataLoader,
        val_loader: DataLoader,
        device: str = "cuda",
        local_epochs: int = 1,
    ):
        self.partition_id = partition_id
        self.hospital_name = self.HOSPITAL_NAMES[partition_id]
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")
        self.local_epochs = local_epochs

        # Build local model
        self.model = build_efficientnet_b4(pretrained=True)
        self.model.to(self.device)

        self.criterion = FocalLoss(alpha=0.25, gamma=2.0)
        self.optimizer = torch.optim.AdamW(
            self.model.parameters(), lr=1e-4, weight_decay=1e-5
        )

    def get_parameters(self, config: dict) -> list[np.ndarray]:
        return get_model_params(self.model)

    def fit(self, parameters: list[np.ndarray], config: dict) -> tuple:
        """Receive global model, train locally, return updated weights."""
        # Update local model with global parameters
        set_model_params(self.model, parameters)

        # Local training
        self.model.train()
        total_loss = 0.0
        num_batches = 0

        for epoch in range(self.local_epochs):
            for batch_tensors in self.train_loader:
                if len(batch_tensors) == 3:
                    images, labels, _ = batch_tensors
                else:
                    images, labels = batch_tensors

                images = images.to(self.device)
                labels = labels.to(self.device)

                self.optimizer.zero_grad()
                logits = self.model(images)
                loss = self.criterion(logits, labels)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                self.optimizer.step()

                total_loss += loss.item()
                num_batches += 1

        avg_loss = total_loss / max(num_batches, 1)
        print(f"  [{self.hospital_name}] Train loss: {avg_loss:.4f}")

        return (
            get_model_params(self.model),
            len(self.train_loader.dataset),
            {"train_loss": avg_loss, "hospital": self.hospital_name},
        )

    def evaluate(self, parameters: list[np.ndarray], config: dict) -> tuple:
        """Evaluate global model on local validation set."""
        set_model_params(self.model, parameters)
        self.model.eval()

        total_loss = 0.0
        all_preds = []
        all_labels = []

        with torch.no_grad():
            for batch_tensors in self.val_loader:
                if len(batch_tensors) == 3:
                    images, labels, _ = batch_tensors
                else:
                    images, labels = batch_tensors

                images = images.to(self.device)
                labels = labels.to(self.device)

                logits = self.model(images)
                loss = self.criterion(logits, labels)
                probs = torch.sigmoid(logits)

                total_loss += loss.item()
                all_preds.append(probs.cpu().numpy())
                all_labels.append(labels.cpu().numpy())

        avg_loss = total_loss / max(len(self.val_loader), 1)

        # Compute macro-average AUC across all 6 classes
        try:
            all_preds_np = np.concatenate(all_preds, axis=0)
            all_labels_np = np.concatenate(all_labels, axis=0)
            per_class_aucs = []
            for _ci in range(all_labels_np.shape[1]):
                try:
                    per_class_aucs.append(
                        roc_auc_score(all_labels_np[:, _ci], all_preds_np[:, _ci])
                    )
                except ValueError:
                    per_class_aucs.append(0.5)  # class not present in batch
            auc = float(np.mean(per_class_aucs))
        except Exception:
            auc = 0.5

        print(f"  [{self.hospital_name}] Val loss: {avg_loss:.4f}, AUC: {auc:.4f}")

        return (
            avg_loss,
            len(self.val_loader.dataset),
            {"val_loss": avg_loss, "auc": auc, "hospital": self.hospital_name},
        )
