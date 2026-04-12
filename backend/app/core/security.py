"""JWT creation and decoding helpers."""
from datetime import datetime, timedelta, timezone
from typing import Literal

from jose import JWTError, jwt

from app.core.config import settings

UserRole = Literal["radiologist", "hospital_operator", "fed_ai_admin", "hospital_it"]


def create_access_token(role: UserRole) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": role,
        "role": role,
        "iat": now,
        "exp": now + timedelta(hours=settings.JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Raises JWTError if invalid or expired."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
