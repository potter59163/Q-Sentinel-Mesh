"""Model loading singleton + inference service.
Imports src.xai.gradcam.analyze_volume() directly — no rewrite needed.
"""
import asyncio
import base64
import importlib.util
import io
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
DEMO_SAMPLES_DIR = REPO_ROOT / "data" / "samples"
REQUIRED_WEIGHTS = ["finetuned_ctich.pth", "high_acc_b4.pth", "hybrid_qsentinel.pth"]
REQUIRED_RUNTIME_MODULES = [
    "torch",
    "numpy",
    "pandas",
    "matplotlib",
    "nibabel",
    "pydicom",
    "gast",
]


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
                if not weights_path:
                    raise FileNotFoundError("Baseline weights not found (finetuned_ctich.pth or high_acc_b4.pth)")
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
                if not weights_path:
                    raise FileNotFoundError("Hybrid weights not found (hybrid_qsentinel.pth)")
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

    def get_readiness(self) -> dict:
        missing_weights = [name for name in REQUIRED_WEIGHTS if not (WEIGHTS_DIR / name).exists()]
        missing_modules = [
            name for name in REQUIRED_RUNTIME_MODULES if importlib.util.find_spec(name) is None
        ]
        demo_case_count = len(list(DEMO_SAMPLES_DIR.glob("*.nii"))) if DEMO_SAMPLES_DIR.exists() else 0

        issues = []
        if missing_weights:
            issues.append("missing_weights")
        if missing_modules:
            issues.append("missing_runtime_modules")
        if not (self.baseline_loaded or self.hybrid_loaded):
            issues.append("no_models_loaded")

        ready = len(issues) == 0
        return {
            "ready": ready,
            "status": "ready" if ready else "degraded",
            "device": self.device,
            "baseline_loaded": self.baseline_loaded,
            "hybrid_loaded": self.hybrid_loaded,
            "missing_weights": missing_weights,
            "missing_modules": missing_modules,
            "demo_case_count": demo_case_count,
            "issues": issues,
        }

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
            if model_type == "hybrid":
                if not self.hybrid_loaded or self.hybrid_model is None:
                    raise RuntimeError("Hybrid model is unavailable on this server")
                model = self.hybrid_model
            else:
                if not self.baseline_loaded or self.baseline_model is None:
                    raise RuntimeError("Baseline model is unavailable on this server")
                model = self.baseline_model

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
            raise RuntimeError(str(e))

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
