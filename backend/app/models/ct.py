from pydantic import BaseModel
from typing import Dict, Optional, Tuple
from typing import Literal

WindowPreset = Literal["brain", "blood", "subdural", "bone", "wide"]
ModelType = Literal["baseline", "hybrid"]


class CTUploadResponse(BaseModel):
    s3_key: str
    slice_count: int
    shape: Tuple[int, int, int]
    min_hu: float
    max_hu: float
    filename: str


class CTWindowRequest(BaseModel):
    s3_key: str
    slice_idx: int
    window: WindowPreset = "brain"


class HUStats(BaseModel):
    mean: float
    std: float
    min: float
    max: float


class CTWindowResponse(BaseModel):
    image_b64: str
    hu_stats: HUStats


class PredictRequest(BaseModel):
    s3_key: str
    slice_idx: int = 0
    model_type: ModelType = "hybrid"
    threshold: Optional[float] = 0.15
    auto_triage: bool = True


class PredictResponse(BaseModel):
    probabilities: Dict[str, float]
    heatmap_b64: str
    top_class: str
    confidence: float
    slice_used: int
    baseline_probs: Optional[Dict[str, float]] = None
    quantum_gain: Optional[float] = None
