"""
Explainable AI — HiResCAM Heatmap Generation

Uses HiResCAM (provably faithful for CNNs) instead of standard GradCAM.
HiResCAM provides more clinically trustworthy explanations by eliminating
gradient averaging artifacts.
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
from pytorch_grad_cam import HiResCAM
from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
from pytorch_grad_cam.utils.image import show_cam_on_image

from ..data.rsna_loader import SUBTYPES

# ─── Hemorrhage type → class index mapping ────────────────────────────────────
SUBTYPE_TO_IDX = {s: i for i, s in enumerate(SUBTYPES)}


def _get_target_layer(model: nn.Module) -> list:
    """
    Automatically find the correct target layer for HiResCAM.
    Works for both BaselineClassifier and HybridQSentinel (share backbone).
    """
    # timm EfficientNet: last block in backbone.blocks
    if hasattr(model, "backbone"):
        return [list(model.backbone.blocks.children())[-1]]
    # Direct EfficientNet (no wrapper)
    elif hasattr(model, "blocks"):
        return [list(model.blocks.children())[-1]]
    raise ValueError(
        "Cannot locate target layer. Model must have 'backbone.blocks' or 'blocks'."
    )


def generate_heatmap(
    model: nn.Module,
    input_tensor: torch.Tensor,
    class_idx: int,
    device: str = "cuda",
) -> np.ndarray:
    """
    Generate HiResCAM heatmap for a specific hemorrhage class.

    Args:
        model:        BaselineClassifier or HybridQSentinel (eval mode)
        input_tensor: (1, 3, H, W) preprocessed slice tensor
        class_idx:    Target class index (0–5, see SUBTYPES)
        device:       Device to run on

    Returns:
        grayscale_cam: (H, W) float32 heatmap in [0, 1]
    """
    model.eval()
    target_layers = _get_target_layer(model)

    # For HybridQSentinel, we need the forward pass to stop at CNN features
    # Temporarily use backbone only for CAM computation (CAM is CNN-based)
    cam_model = model.backbone if hasattr(model, "backbone") else model

    with HiResCAM(model=cam_model, target_layers=target_layers) as cam:
        targets = [ClassifierOutputTarget(class_idx)]
        grayscale_cam = cam(
            input_tensor=input_tensor.to(device),
            targets=targets,
        )

    return grayscale_cam[0]  # (H, W) float32


def overlay_heatmap(
    slice_np: np.ndarray,
    cam_map: np.ndarray,
    alpha: float = 0.5,
    brain_mask: np.ndarray | None = None,
) -> np.ndarray:
    """
    Overlay heatmap on original CT slice.

    Args:
        slice_np:   (H, W) or (H, W, 3) float32 image in [0, 1]
        cam_map:    (H, W) float32 CAM in [0, 1]
        alpha:      Heatmap blend strength
        brain_mask: Optional bool (H, W) — darken non-brain areas

    Returns:
        overlay: (H, W, 3) uint8 RGB image
    """
    # Ensure (H, W, 3) RGB
    if slice_np.ndim == 2:
        rgb = np.stack([slice_np, slice_np, slice_np], axis=-1)
    else:
        rgb = slice_np.copy()

    rgb = np.clip(rgb, 0.0, 1.0).astype(np.float32)

    # Darken areas outside brain so heatmap focuses on brain tissue
    if brain_mask is not None:
        outside = ~brain_mask
        rgb[outside] *= 0.15          # dim non-brain to near-black
        cam_map = cam_map.copy()
        cam_map[outside] = 0.0        # no heatmap color outside brain

    return show_cam_on_image(rgb, cam_map, use_rgb=True, image_weight=1 - alpha)


def get_top_slice_idx(
    volume_hu: np.ndarray,
    model: nn.Module,
    device: str = "cuda",
    batch_size: int = 16,
) -> tuple[int, torch.Tensor]:
    """
    Find the slice with the highest 'any hemorrhage' prediction score.
    Skips slices with low brain content (intensity thresholding).
    """
    from ..data.rsna_loader import get_volume_slice_tensor

    model.eval()
    all_probs = []
    depth = volume_hu.shape[0]

    with torch.no_grad():
        for start in range(0, depth, batch_size):
            end = min(start + batch_size, depth)
            batch = torch.cat([
                get_volume_slice_tensor(volume_hu, i)
                for i in range(start, end)
            ], dim=0).to(device)

            probs = model.predict_proba(batch)
            all_probs.append(probs.cpu())

    all_probs = torch.cat(all_probs, dim=0)  # (D, 6)
    
    # ── Filter out non-brain slices ─────────────────────────────────
    # We don't want to pick a noise slice from the base of the skull
    any_idx = SUBTYPE_TO_IDX["any"]
    valid_scores = all_probs[:, any_idx].clone()
    
    for i in range(depth):
        hu = volume_hu[i]
        # Relaxed check: just ensure there's SOME variation and soft tissue
        brain_pixels = ((hu > 0) & (hu < 100)).sum()
        if brain_pixels < (hu.size * 0.005): # Less than 0.5% (very permissive)
            valid_scores[i] = -1.0
            
    best_slice = int(valid_scores.argmax().item())
    return best_slice, all_probs


def analyze_volume(
    volume_hu: np.ndarray,
    model: nn.Module,
    device: str = "cuda",
    target_slice_idx: int | None = None,
) -> dict:
    """
    Full XAI analysis of a CT volume.
    If target_slice_idx is None, automatically finds the most relevant slice.
    """
    from ..data.rsna_loader import get_volume_slice_tensor, apply_window, WINDOWS

    # Step 1: Find/Select most relevant slice
    if target_slice_idx is not None:
        # Still need all_probs for the breakdown chart
        _, all_probs = get_top_slice_idx(volume_hu, model, device)
        top_idx = target_slice_idx
    else:
        top_idx, all_probs = get_top_slice_idx(volume_hu, model, device)

    # Step 2: Determine top predicted class with high sensitivity
    slice_probs = all_probs[top_idx]  # (6,)
    any_prob = float(slice_probs[5].item())
    
    # Identify the most likely specific subtype
    subtype_probs = slice_probs[:5]
    max_subtype_prob = float(subtype_probs.max().item())
    top_class_idx = int(subtype_probs.argmax().item())
    
    # Sensitivity Boost: Use the higher of 'any' prob or the most confident subtype
    # This prevents missing a clear focal lesion that the "any" head might under-score
    confidence = max(any_prob, max_subtype_prob) 


    # Step 3: Generate heatmap
    input_tensor = get_volume_slice_tensor(volume_hu, top_idx)  # (1, 3, 224, 224)
    cam_map = generate_heatmap(model, input_tensor, top_class_idx, device)

    # Step 4: Build overlay on brain-window slice
    hu_slice = volume_hu[top_idx]
    brain_slice = apply_window(
        hu_slice,
        center=WINDOWS["brain"][0],
        width=WINDOWS["brain"][1],
    )

    # Resize cam_map to match original slice resolution (cam is 224×224)
    if cam_map.shape != brain_slice.shape:
        from PIL import Image as _PILImage
        cam_pil = _PILImage.fromarray(cam_map).resize(
            (brain_slice.shape[1], brain_slice.shape[0]),
            _PILImage.BILINEAR,
        )
        cam_map = np.array(cam_pil, dtype=np.float32)

    # Mask heatmap to brain-only region so activation outside brain is zero
    from ..data.rsna_loader import get_brain_mask
    brain_mask = get_brain_mask(hu_slice)
    cam_map[~brain_mask] = 0.0

    overlay = overlay_heatmap(brain_slice, cam_map, brain_mask=brain_mask)

    return {
        "top_slice_idx": top_idx,
        "all_probs": all_probs,
        "top_class_idx": top_class_idx,
        "top_class_name": SUBTYPES[top_class_idx],
        "confidence": confidence,
        "heatmap": cam_map,
        "overlay": overlay,
    }
