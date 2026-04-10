from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.core.rate_limit import limiter
from app.services.model_service import model_service

# Routes
from app.api.routes import auth, health, metrics, federated, thresholds, ct, predict, pqc


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load ML models on startup
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

# ── Rate limiting ─────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=False,
)

# ── Trusted host (production only) ────────────────────────────────────────────
# app.add_middleware(TrustedHostMiddleware, allowed_hosts=["api.yourdomain.com"])

# ── Global error handler ──────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(metrics.router)
app.include_router(federated.router)
app.include_router(thresholds.router)
app.include_router(ct.router)
app.include_router(predict.router)
app.include_router(pqc.router)
