"""
Explainable AI — HiResCAM Heatmap Generation

Pure PyTorch / NumPy implementation — NO cv2 / pytorch_grad_cam dependency.
Works in headless cloud environments (Streamlit Cloud, Hugging Face Spaces).

HiResCAM (Draelos & Carin, 2021): element-wise activation x gradient,
provably faithful for CNNs (unlike standard GradCAM).
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from ..data.rsna_loader import SUBTYPES

SUBTYPE_TO_IDX = {s: i for i, s in enumerate(SUBTYPES)}


# ──────────────────────────────────────────────────────────────────────────────
# Minimal HiResCAM — no cv2, no pytorch_grad_cam
# ──────────────────────────────────────────────────────────────────────────────

class _ClassifierOutputTarget:
    """Select a single class output for backward pass."""
    def __init__(self, category: int):
        self.category = category

    def __call__(self, output: torch.Tensor) -> torch.Tensor:
        if output.dim() == 1:
            return output[self.category]
        return output[:, self.category]


class _HiResCAM:
    """
    HiResCAM context manager: element-wise activation x gradient.
    Pure PyTorch — no cv2 required.

    Usage:
        with _HiResCAM(model, target_layers) as cam:
            maps = cam(input_tensor, targets)
    """

    def __init__(self, model: nn.Module, target_layers: list):
        self.model = model
        self.target_layers = target_layers
        self._activations: list = []
        self._gradients: list = []
        self._hooks: list = []

    def __enter__(self):
        for layer in self.target_layers:
            self._hooks.append(
                layer.register_forward_hook(self._save_activation)
            )
            self._hooks.append(
                layer.register_full_backward_hook(self._save_gradient)
            )
        return self

    def __exit__(self, *args):
        for h in self._hooks:
            h.remove()
        self._hooks.clear()

    def _save_activation(self, module, inp, out):
        self._activations.append(out.detach())

    def _save_gradient(self, module, grad_in, grad_out):
        self._gradients.append(grad_out[0].detach())

    def __call__(
        self,
        input_tensor: torch.Tensor,
        targets: list,
    ) -> list:
        self._activations.clear()
        self._gradients.clear()

        self.model.zero_grad()
        output = self.model(input_tensor)

        loss = sum(t(output) for t in targets)
        if hasattr(loss, "dim") and loss.dim() > 0:
            loss = loss.sum()
        loss.backward()

        acts  = self._activations[0]   # (1, C, h, w)
        grads = self._gradients[0]     # (1, C, h, w)

        # HiResCAM: pixel-wise product, sum over channels
        cam = (acts * grads).sum(dim=1, keepdim=True)  # (1, 1, h, w)
        cam = F.relu(cam)

        # Upsample to input resolution
        h, w = input_tensor.shape[-2:]
        cam = F.interpolate(
            cam, size=(h, w), mode="bilinear", align_corners=False
        )
        cam = cam.squeeze().cpu().float().numpy()  # (H, W)

        # Normalize to [0, 1]
        lo, hi = cam.min(), cam.max()
        if hi > lo:
            cam = (cam - lo) / (hi - lo)
        else:
            cam = np.zeros_like(cam)

        return [cam]


# ──────────────────────────────────────────────────────────────────────────────
# Layer selection
# ──────────────────────────────────────────────────────────────────────────────

def _get_target_layer(model: nn.Module) -> list:
    """Auto-detect last convolutional block for EfficientNet-B4."""
    if hasattr(model, "backbone") and hasattr(model.backbone, "blocks"):
        return [list(model.backbone.blocks.children())[-1]]
    if hasattr(model, "blocks"):
        return [list(model.blocks.children())[-1]]
    raise ValueError(
        "Cannot locate target layer. Model must have 'backbone.blocks' or 'blocks'."
    )


# ──────────────────────────────────────────────────────────────────────────────
# Heatmap overlay — pure numpy + matplotlib, no cv2
# ──────────────────────────────────────────────────────────────────────────────

def overlay_heatmap(
    slice_np: np.ndarray,
    cam_map: np.ndarray,
    alpha: float = 0.5,
    brain_mask: np.ndarray | None = None,
) -> np.ndarray:
    """
    Blend jet-colormap heatmap onto a CT slice.

    Args:
        slice_np:   (H, W) or (H, W, 3) float32 image in [0, 1]
        cam_map:    (H, W) float32 activation map in [0, 1]
        alpha:      Heatmap blend strength (0 = CT only, 1 = heatmap only)
        brain_mask: Optional bool mask

    Returns:
        overlay: (H, W, 3) uint8 RGB image
    """
    import matplotlib.cm as _cm

    if slice_np.ndim == 2:
        rgb = np.stack([slice_np, slice_np, slice_np], axis=-1)
    else:
        rgb = slice_np.copy()
    rgb = np.clip(rgb, 0.0, 1.0).astype(np.float32)

    cam_c = cam_map.copy().astype(np.float32)
    if brain_mask is not None:
        outside = ~brain_mask
        rgb[outside] *= 0.15
        cam_c[outside] = 0.0

    # Jet colormap via matplotlib (RGBA float32 in [0,1]) — no cv2 needed
    heat_rgb = _cm.jet(cam_c)[..., :3].astype(np.float32)

    blended = (1.0 - alpha) * rgb + alpha * heat_rgb
    return np.clip(blended * 255, 0, 255).astype(np.uint8)


# ──────────────────────────────────────────────────────────────────────────────
# Core analysis functions
# ──────────────────────────────────────────────────────────────────────────────

def generate_heatmap(
    model: nn.Module,
    input_tensor: torch.Tensor,
    class_idx: int,
    device: str = "cpu",
) -> np.ndarray:
    """
    Generate HiResCAM heatmap for a specific hemorrhage class.

    Returns:
        grayscale_cam: (H, W) float32 in [0, 1]
    """
    model.eval()
    target_layers = _get_target_layer(model)
    cam_model = model.backbone if hasattr(model, "backbone") else model

    with _HiResCAM(model=cam_model, target_layers=target_layers) as cam:
        targets = [_ClassifierOutputTarget(class_idx)]
        grayscale_cam = cam(
            input_tensor=input_tensor.to(device),
            targets=targets,
        )

    return grayscale_cam[0]


def get_top_slice_idx(
    volume_hu: np.ndarray,
    model: nn.Module,
    device: str = "cpu",
    batch_size: int = 8,
    max_slices: int = 24,
) -> tuple:
    """
    Find the slice with the highest 'any hemorrhage' prediction score.
    Samples up to max_slices evenly for speed on CPU cloud.
    """
    from ..data.rsna_loader import get_volume_slice_tensor

    model.eval()
    depth = volume_hu.shape[0]

    # Sample evenly to keep CPU inference fast
    if depth > max_slices:
        indices = np.linspace(0, depth - 1, max_slices, dtype=int).tolist()
    else:
        indices = list(range(depth))

    probs_map: dict = {}
    with torch.no_grad():
        for start in range(0, len(indices), batch_size):
            batch_idx = indices[start: start + batch_size]
            batch = torch.cat([
                get_volume_slice_tensor(volume_hu, i) for i in batch_idx
            ], dim=0).to(device)
            probs = model.predict_proba(batch).cpu()
            for k, i in enumerate(batch_idx):
                probs_map[i] = probs[k]

    # Build full (D, 6) tensor
    all_probs = torch.zeros(depth, 6)
    for i, p in probs_map.items():
        all_probs[i] = p

    any_idx = SUBTYPE_TO_IDX["any"]
    valid_scores = all_probs[:, any_idx].clone()

    for i in probs_map:
        hu = volume_hu[i]
        if ((hu > 0) & (hu < 100)).sum() < hu.size * 0.005:
            valid_scores[i] = -1.0

    best_slice = int(valid_scores.argmax().item())
    return best_slice, all_probs


def analyze_volume(
    volume_hu: np.ndarray,
    model: nn.Module,
    device: str = "cpu",
    target_slice_idx: int | None = None,
) -> dict:
    """
    Full XAI analysis: best slice, per-class scores, HiResCAM heatmap.

    Returns dict with: top_slice_idx, all_probs, top_class_idx,
    top_class_name, confidence, heatmap, overlay.
    """
    from ..data.rsna_loader import (
        get_volume_slice_tensor, apply_window, WINDOWS, get_brain_mask
    )

    if target_slice_idx is not None:
        _, all_probs = get_top_slice_idx(volume_hu, model, device)
        top_idx = target_slice_idx
    else:
        top_idx, all_probs = get_top_slice_idx(volume_hu, model, device)

    slice_probs   = all_probs[top_idx]
    any_prob      = float(slice_probs[5])
    subtype_probs = slice_probs[:5]
    top_class_idx = int(subtype_probs.argmax())
    confidence    = max(any_prob, float(subtype_probs.max()))

    # Generate heatmap
    input_tensor = get_volume_slice_tensor(volume_hu, top_idx)
    cam_map      = generate_heatmap(model, input_tensor, top_class_idx, device)

    # Build overlay on brain-window slice
    hu_slice    = volume_hu[top_idx]
    brain_slice = apply_window(
        hu_slice,
        center=WINDOWS["brain"][0],
        width=WINDOWS["brain"][1],
    )

    # Resize cam_map if resolution differs (cam is 224x224, slice may differ)
    if cam_map.shape != brain_slice.shape:
        from PIL import Image as _PILImage
        cam_pil = _PILImage.fromarray(
            (cam_map * 255).astype(np.uint8)
        ).resize(
            (brain_slice.shape[1], brain_slice.shape[0]),
            _PILImage.BILINEAR,
        )
        cam_map = np.array(cam_pil, dtype=np.float32) / 255.0

    brain_mask      = get_brain_mask(hu_slice)
    cam_map[~brain_mask] = 0.0
    overlay         = overlay_heatmap(brain_slice, cam_map, brain_mask=brain_mask)

    return {
        "top_slice_idx":  top_idx,
        "all_probs":      all_probs,
        "top_class_idx":  top_class_idx,
        "top_class_name": SUBTYPES[top_class_idx],
        "confidence":     confidence,
        "heatmap":        cam_map,
        "overlay":        overlay,
    }
