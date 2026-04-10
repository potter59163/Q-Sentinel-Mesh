import re
from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.models.ct import PredictRequest, PredictResponse
from app.services.ct_service import ct_service
from app.services.model_service import model_service

router = APIRouter(prefix="/api", tags=["predict"])

S3_KEY_PATTERN = re.compile(r"^ct-uploads/[0-9a-f\-]{36}/[\w.\-]+$")


@router.post("/predict", response_model=PredictResponse)
@limiter.limit("20/minute")
async def predict(
    request: Request,
    body: PredictRequest,
    _: str = Depends(get_current_user),
):
    if not S3_KEY_PATTERN.match(body.s3_key):
        raise HTTPException(status_code=422, detail="Invalid s3_key format")

    volume = ct_service.get_volume(body.s3_key)
    if volume is None:
        raise HTTPException(status_code=404, detail="CT volume not found. Please upload again.")

    result = await model_service.analyze(
        volume=volume,
        slice_idx=body.slice_idx,
        model_type=body.model_type,
        threshold=body.threshold or 0.15,
        auto_triage=body.auto_triage,
    )
    return result
