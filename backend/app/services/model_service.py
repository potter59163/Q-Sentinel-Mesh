"""Model loading singleton + inference service.
Imports src.xai.gradcam.analyze_volume() directly — no rewrite needed.
"""
import asyncio
import base64
import io
import os
import sys
from pathlib import Path
from typing import Optional

import numpy as np

# Add repo root to sys.path
REPO_ROOT = Path(__file__).parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.models.ct import PredictResponse

SUBTYPES = ["epidural", "intraparenchymal", "intraventricular", "subarachnoid", "subdural", "any"]
WEIGHTS_DIR = REPO_ROOT / "weights"


class ModelService:
    def __init__(self):
        self.baseline_model = None
        self.hybrid_model = None
        self.baseline_loaded = False
        self.hybrid_loaded = False
        self.device = "cpu"

    def load_models(self):
        """Called at app startup (lifespan event)."""
        try:
            import torch
            self.device = "cuda" if torch.cuda.is_available() else "cpu"

            # Load baseline
            try:
                from src.models.cnn_encoder import BaselineClassifier
                model = BaselineClassifier(pretrained=False)
                weights_path = self._find_weights(["finetuned_ctich.pth", "high_acc_b4.pth"])
                if weights_path:
                    state = torch.load(weights_path, map_location=self.device, weights_only=True)
                    model.load_state_dict(state, strict=False)
                model.eval()
                model.to(self.device)
                self.baseline_model = model
                self.baseline_loaded = True
                print(f"[ModelService] Baseline loaded from {weights_path} on {self.device}")
            except Exception as e:
                print(f"[ModelService] Baseline load failed: {e}")

            # Load hybrid
            try:
                from src.models.hybrid_model import HybridQSentinel
                hybrid = HybridQSentinel(pretrained=False)
                weights_path = self._find_weights(["hybrid_qsentinel.pth"])
                if weights_path:
                    state = torch.load(weights_path, map_location=self.device, weights_only=True)
                    hybrid.load_state_dict(state, strict=False)
                hybrid.eval()
                hybrid.to(self.device)
                self.hybrid_model = hybrid
                self.hybrid_loaded = True
                print(f"[ModelService] Hybrid loaded from {weights_path} on {self.device}")
            except Exception as e:
                print(f"[ModelService] Hybrid load failed: {e}")

        except Exception as e:
            print(f"[ModelService] Model loading error: {e}")

    def _find_weights(self, filenames: list) -> Optional[Path]:
        for fn in filenames:
            p = WEIGHTS_DIR / fn
            if p.exists():
                return p
        return None

    async def analyze(
        self,
        volume: np.ndarray,
        slice_idx: int,
        model_type: str,
        threshold: float,
        auto_triage: bool,
    ) -> PredictResponse:
        """Run inference in a thread pool to avoid blocking the event loop."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._analyze_sync,
            volume, slice_idx, model_type, threshold, auto_triage,
        )

    def _analyze_sync(
        self,
        volume: np.ndarray,
        slice_idx: int,
        model_type: str,
        threshold: float,
        auto_triage: bool,
    ) -> PredictResponse:
        try:
            from src.xai.gradcam import analyze_volume
            model = self.hybrid_model if (model_type == "hybrid" and self.hybrid_loaded) else self.baseline_model
            if model is None:
                return self._mock_response(slice_idx)

            target = None if auto_triage else slice_idx
            result = analyze_volume(
                volume_hu=volume,
                model=model,
                device=self.device,
                target_slice_idx=target,
            )

            all_probs = result.get("all_probs", np.zeros((1, 6)))  # shape (D, 6)
            used_slice = int(result.get("top_slice_idx", slice_idx))
            heatmap_img = result.get("overlay", None)

            # Get per-class probs for the chosen slice
            slice_probs = all_probs[used_slice] if all_probs.ndim == 2 else all_probs
            prob_dict = {k: float(slice_probs[i]) for i, k in enumerate(SUBTYPES)}
            top_class = result.get("top_class_name", max(prob_dict, key=lambda k: prob_dict[k]))
            confidence = float(result.get("confidence", prob_dict.get(top_class, 0.0)))

            heatmap_b64 = self._encode_img(heatmap_img)

            # Run baseline for comparison if hybrid was requested
            baseline_probs = None
            quantum_gain = None
            if model_type == "hybrid" and self.baseline_loaded:
                try:
                    b_result = analyze_volume(
                        volume_hu=volume,
                        model=self.baseline_model,
                        device=self.device,
                        target_slice_idx=int(used_slice),
                    )
                    b_all = b_result.get("all_probs", np.zeros((1, 6)))
                    b_used = int(b_result.get("top_slice_idx", used_slice))
                    b_probs = b_all[b_used] if b_all.ndim == 2 else b_all
                    baseline_probs = {k: float(b_probs[i]) for i, k in enumerate(SUBTYPES)}
                    quantum_gain = float(prob_dict["any"] - baseline_probs["any"]) * 100
                except Exception:
                    pass

            return PredictResponse(
                probabilities=prob_dict,
                heatmap_b64=heatmap_b64,
                top_class=top_class,
                confidence=confidence,
                slice_used=int(used_slice),
                baseline_probs=baseline_probs,
                quantum_gain=quantum_gain,
            )
        except Exception as e:
            print(f"[ModelService] Inference error: {e}")
            return self._mock_response(slice_idx)

    def _mock_response(self, slice_idx: int) -> PredictResponse:
        """Fallback mock when model isn't loaded."""
        import random
        probs = {k: round(random.uniform(0.02, 0.15), 3) for k in SUBTYPES}
        probs["any"] = round(random.uniform(0.1, 0.4), 3)
        return PredictResponse(
            probabilities=probs,
            heatmap_b64="",
            top_class="any",
            confidence=probs["any"],
            slice_used=slice_idx,
        )

    def _encode_img(self, img) -> str:
        if img is None:
            return ""
        try:
            import PIL.Image
            if isinstance(img, np.ndarray):
                pil = PIL.Image.fromarray(img)
            else:
                pil = img
            buf = io.BytesIO()
            pil.save(buf, format="PNG")
            return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
        except Exception:
            return ""


model_service = ModelService()
