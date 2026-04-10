from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.services.model_service import model_service

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health():
    readiness = model_service.get_readiness()
    return {
        "status": "ok",
        "model_loaded": readiness["baseline_loaded"] or readiness["hybrid_loaded"],
        "device": model_service.device,
    }


@router.get("/health/ready")
async def health_ready():
    readiness = model_service.get_readiness()
    status_code = 200 if readiness["ready"] else 503
    return JSONResponse(status_code=status_code, content=readiness)
