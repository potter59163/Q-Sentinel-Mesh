from fastapi import APIRouter
from app.services.results_service import results_service

router = APIRouter(prefix="/api/federated", tags=["federated"])


@router.get("/rounds")
async def get_rounds():
    return results_service.get_fed_rounds()
