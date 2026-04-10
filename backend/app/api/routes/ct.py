import re
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from app.core.dependencies import get_current_user
from app.core.rate_limit import limiter
from app.models.ct import CTUploadResponse, CTWindowRequest, CTWindowResponse, HUStats
from app.services.ct_service import ct_service

# ct.py is at backend/app/api/routes/ct.py → go up 5 levels to repo root
REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent

router = APIRouter(prefix="/api/ct", tags=["ct"])

S3_KEY_PATTERN = re.compile(r"^ct-uploads/[0-9a-f\-]{36}/[\w.\-]+$")
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200 MB


@router.post("/upload", response_model=CTUploadResponse)
@limiter.limit("10/minute")
async def upload_ct(
    request: Request,
    file: UploadFile = File(...),
    _: str = Depends(get_current_user),
):
    filename = file.filename or "upload"
    ext = filename.lower().split(".")[-1]
    if ext not in ("nii", "dcm"):
        raise HTTPException(status_code=422, detail="Only .nii and .dcm files are supported")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 200 MB)")

    s3_key = f"ct-uploads/{uuid.uuid4()}/{filename}"
    meta = ct_service.load_ct(content, filename, s3_key)
    return meta


@router.post("/window", response_model=CTWindowResponse)
@limiter.limit("60/minute")
async def window_slice(
    request: Request,
    body: CTWindowRequest,
    _: str = Depends(get_current_user),
):
    if not S3_KEY_PATTERN.match(body.s3_key):
        raise HTTPException(status_code=422, detail="Invalid s3_key format")

    result = ct_service.get_windowed_slice(body.s3_key, body.slice_idx, body.window)
    if result is None:
        raise HTTPException(status_code=404, detail="CT volume not found. Please upload again.")
    return result


@router.get("/demo")
@limiter.limit("20/minute")
async def list_demo_patients(
    request: Request,
    _: str = Depends(get_current_user),
):
    samples_dir = REPO_ROOT / "data" / "samples"
    if not samples_dir.is_dir():
        return {"patients": []}
    patients = sorted(p.stem for p in samples_dir.glob("*.nii"))
    return {"patients": patients}


@router.get("/demo/{patient_id}", response_model=CTUploadResponse)
@limiter.limit("20/minute")
async def get_demo_patient(
    patient_id: str,
    request: Request,
    _: str = Depends(get_current_user),
):
    nii_path = REPO_ROOT / "data" / "samples" / f"{patient_id}.nii"
    if not nii_path.is_file():
        raise HTTPException(status_code=404, detail="Demo patient not found")

    content = nii_path.read_bytes()
    filename = f"{patient_id}.nii"
    s3_key = f"ct-uploads/{uuid.uuid4()}/demo-{patient_id}.nii"
    meta = ct_service.load_ct(content, filename, s3_key)
    return meta
