from fastapi import APIRouter, HTTPException, Request, status
from app.models.auth import LoginRequest, TokenResponse
from app.core.security import verify_password, create_access_token, hash_password
from app.core.config import settings
from app.core.rate_limit import limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Hash the demo password once at import time
_DEMO_HASH = hash_password(settings.DEMO_PASSWORD)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest):
    if not verify_password(body.password, _DEMO_HASH):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
        )
    token = create_access_token()
    return TokenResponse(access_token=token)
