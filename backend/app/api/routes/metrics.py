from fastapi import APIRouter
from app.services.results_service import results_service

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/benchmark")
async def get_benchmark():
    return results_service.get_benchmark()
