from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user
from app.services.results_service import results_service

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/benchmark")
async def get_benchmark(_: str = Depends(get_current_user)):
    return results_service.get_benchmark()
