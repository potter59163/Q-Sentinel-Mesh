from contextlib import asynccontextmanager
import json
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.routes import ct, export, federated, feedback, health, metrics, pqc, predict, thresholds
from app.core.config import settings
from app.core.rate_limit import limiter
from app.services.model_service import model_service
from app.services.runtime_assets import runtime_assets_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    runtime_assets_service.ensure_runtime_assets()
    print("[Startup] Loading ML models...")
    model_service.load_models()
    print("[Startup] Ready.")
    yield
    print("[Shutdown] Bye.")


app = FastAPI(
    title="Q-Sentinel Mesh API",
    version="1.0.0",
    description="Quantum-Enhanced Federated Learning for CT Hemorrhage Detection",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        duration_ms = int((time.perf_counter() - start) * 1000)
        print(json.dumps({
            "level": "error",
            "event": "request_failed",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "duration_ms": duration_ms,
            "error": str(exc),
        }))
        raise

    duration_ms = int((time.perf_counter() - start) * 1000)
    response.headers["x-request-id"] = request_id
    response.headers["x-response-time-ms"] = str(duration_ms)
    response.headers["x-content-type-options"] = "nosniff"
    print(json.dumps({
        "level": "info",
        "event": "request_complete",
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": duration_ms,
    }))
    return response


# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    allow_credentials=False,
)

# Trusted host (production only)
# app.add_middleware(TrustedHostMiddleware, allowed_hosts=["api.yourdomain.com"])


# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(status_code=500, content={"detail": str(exc), "request_id": request_id})


# Routers
app.include_router(health.router)
app.include_router(metrics.router)
app.include_router(federated.router)
app.include_router(thresholds.router)
app.include_router(ct.router)
app.include_router(predict.router)
app.include_router(pqc.router)
app.include_router(feedback.router)
app.include_router(export.router)
