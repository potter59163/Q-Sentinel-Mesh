from fastapi import APIRouter
from app.services.results_service import results_service

router = APIRouter(prefix="/api", tags=["thresholds"])


@router.get("/thresholds")
async def get_thresholds():
    return results_service.get_thresholds()
