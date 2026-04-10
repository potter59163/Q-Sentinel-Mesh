from pydantic import BaseModel
from typing import Optional


class PQCDemoResponse(BaseModel):
    public_key_bytes: int
    secret_key_bytes: int
    kem_ciphertext_bytes: int
    aes_ciphertext_bytes: int
    keygen_ms: float
    encrypt_ms: float
    decrypt_ms: float
    success: bool
    backend: str
    error: Optional[str] = None
