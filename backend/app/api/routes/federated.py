from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user
from app.services.results_service import results_service

router = APIRouter(prefix="/api/federated", tags=["federated"])


@router.get("/rounds")
async def get_rounds(_: str = Depends(get_current_user)):
    return results_service.get_fed_rounds()
