"""
EfficientNet-B4 Baseline Classifier for RSNA Hemorrhage Detection.

Architecture:
    timm EfficientNet-B4 (pretrained ImageNet)
    → Global Average Pool
    → Dropout(0.3)
    → Linear(1792 → 6)
    → Sigmoid (multi-label)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import torch
import torch.nn as nn
import timm
from torchvision import transforms


FEATURE_DIM = 1792  # EfficientNet-B4 last stage output dimension
NUM_CLASSES = 6


class BaselineClassifier(nn.Module):
    """
    EfficientNet-B4 multi-label classifier for intracranial hemorrhage.

    Outputs 6 sigmoid probabilities:
        [epidural, intraparenchymal, intraventricular,
         subarachnoid, subdural, any]
    """

    def __init__(
        self,
        pretrained: bool = True,
        dropout: float = 0.3,
        freeze_backbone: bool = False,
    ):
        super().__init__()

        self.backbone = timm.create_model(
            "efficientnet_b4",
            pretrained=pretrained,
            in_chans=3,
            num_classes=0,          # remove default head → raw features
            global_pool="avg",
            drop_rate=dropout,
            drop_path_rate=0.2,
        )

        if freeze_backbone:
            # Freeze all layers except the last 2 blocks for fine-tuning
            blocks = list(self.backbone.blocks.children())
            for block in blocks[:-2]:
                for param in block.parameters():
                    param.requires_grad = False

        self.head = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(FEATURE_DIM, NUM_CLASSES),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (B, 3, H, W) normalized input tensor
        Returns:
            logits: (B, 6) raw logits (apply sigmoid for probabilities)
        """
        features = self.backbone(x)   # (B, 1792)
        return self.head(features)    # (B, 6)

    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        """Return sigmoid probabilities (B, 6)."""
        return torch.sigmoid(self.forward(x))

    def get_features(self, x: torch.Tensor) -> torch.Tensor:
        """Return raw feature vector (B, 1792) for VQC input."""
        return self.backbone(x)

    # Aliases for train_combined.py progressive unfreezing
    @property
    def features(self):
        """Alias for self.backbone (timm EfficientNet)."""
        return self.backbone

    @property
    def classifier(self):
        """Alias for self.head (Linear + Dropout)."""
        return self.head


def build_efficientnet_b4(
    pretrained: bool = True,
    dropout: float = 0.3,
    freeze_backbone: bool = False,
) -> BaselineClassifier:
    """Factory function for EfficientNet-B4 baseline."""
    return BaselineClassifier(
        pretrained=pretrained,
        dropout=dropout,
        freeze_backbone=freeze_backbone,
    )


def load_baseline(weights_path: str | Path, device: str = "cuda") -> BaselineClassifier:
    """Load a saved baseline model from weights file."""
    model = build_efficientnet_b4(pretrained=False)
    model.load_state_dict(
        torch.load(str(weights_path), map_location=device)
    )
    model.to(device)
    model.eval()
    return model


def build_baseline(
    num_classes: int = 6,
    dropout: float = 0.3,
    pretrained: bool = True,
) -> BaselineClassifier:
    """Alias for build_efficientnet_b4 with named num_classes arg."""
    return BaselineClassifier(pretrained=pretrained, dropout=dropout)


# ─── Training Utilities ────────────────────────────────────────────────────────

class FocalLoss(nn.Module):
    """
    Focal Loss for multi-label classification.
    Reduces loss contribution from easy examples, focuses on hard cases.
    Particularly effective for imbalanced hemorrhage datasets.
    """

    def __init__(self, alpha: float = 0.25, gamma: float = 2.0):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        bce = nn.functional.binary_cross_entropy_with_logits(
            logits, targets, reduction="none"
        )
        prob = torch.sigmoid(logits)
        p_t = targets * prob + (1 - targets) * (1 - prob)
        alpha_t = targets * self.alpha + (1 - targets) * (1 - self.alpha)
        focal_weight = alpha_t * (1 - p_t) ** self.gamma
        return (focal_weight * bce).mean()


def get_optimizer_and_scheduler(
    model: BaselineClassifier,
    lr: float = 1e-4,
    weight_decay: float = 1e-5,
    epochs: int = 10,
    steps_per_epoch: int = 1000,
):
    """
    Returns AdamW optimizer + CosineAnnealing scheduler.
    Uses separate learning rates for backbone (lower) and head (higher).
    """
    backbone_params = list(model.backbone.parameters())
    head_params = list(model.head.parameters())

    optimizer = torch.optim.AdamW([
        {"params": backbone_params, "lr": lr * 0.1},
        {"params": head_params,     "lr": lr},
    ], weight_decay=weight_decay)

    scheduler = torch.optim.lr_scheduler.OneCycleLR(
        optimizer,
        max_lr=[lr * 0.1, lr],
        steps_per_epoch=steps_per_epoch,
        epochs=epochs,
        pct_start=0.1,
    )

    return optimizer, scheduler
