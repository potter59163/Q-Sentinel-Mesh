from fastapi import APIRouter
from app.services.model_service import model_service

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "model_loaded": model_service.baseline_loaded or model_service.hybrid_loaded,
        "device": model_service.device,
    }
