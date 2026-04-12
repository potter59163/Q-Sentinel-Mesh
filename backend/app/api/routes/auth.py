"""Authentication - single demo password, role-based JWT."""
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.security import UserRole, create_access_token

router = APIRouter(prefix="/api", tags=["auth"])

VALID_ROLES = {"radiologist", "hospital_operator", "fed_ai_admin", "hospital_it", "dev"}


class LoginRequest(BaseModel):
    role: Literal["radiologist", "hospital_operator", "fed_ai_admin", "hospital_it", "dev"]


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    role: UserRole


@router.post("/auth/login", response_model=LoginResponse)
@limiter.limit("30/minute")
async def login(request: Request, body: LoginRequest):
    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=422, detail="บทบาทที่เลือกไม่ถูกต้อง")

    token = create_access_token(body.role)
    return LoginResponse(access_token=token, token_type="bearer", role=body.role)
