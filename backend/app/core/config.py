from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DEMO_PASSWORD: str = "qsentinel2026"
    JWT_SECRET: str = "change-me-in-production-64-chars-minimum-random-string"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24

    AWS_REGION: str = "ap-southeast-7"
    S3_BUCKET: str = ""
    WEIGHTS_S3_PREFIX: str = "weights/"
    DEMO_SAMPLES_S3_PREFIX: str = "data/samples/"
    RESULTS_S3_PREFIX: str = "results/"
    CT_UPLOAD_S3_PREFIX: str = "ct-uploads/"

    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://d3grijenetuyp6.cloudfront.net",
    ]
    RATE_LIMIT_PER_MINUTE: int = 30

    USE_S3: bool = False
    LOCAL_RESULTS_DIR: str = "results"
    LOCAL_WEIGHTS_DIR: str = "weights"

    QSENTINEL_ALLOW_INSECURE_PQC_FALLBACK: str = "1"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
