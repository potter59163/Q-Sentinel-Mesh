from fastapi import APIRouter, Request
from app.core.rate_limit import limiter
from app.models.pqc import PQCDemoResponse
from app.services.pqc_service import pqc_service

router = APIRouter(prefix="/api/pqc", tags=["pqc"])


@router.post("/demo", response_model=PQCDemoResponse)
@limiter.limit("30/minute")
async def pqc_demo(request: Request):
    return pqc_service.run_demo()
