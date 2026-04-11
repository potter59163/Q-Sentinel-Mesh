import re
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from app.core.rate_limit import limiter
from app.models.ct import CTUploadResponse, CTWindowRequest, CTWindowResponse
from app.services.ct_service import ct_service

# ct.py is at backend/app/api/routes/ct.py -> go up 5 levels to repo root.
REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent

router = APIRouter(prefix="/api/ct", tags=["ct"])

S3_KEY_PATTERN = re.compile(r"^ct-uploads/[0-9a-f\-]{36}/[\w.\-]+$")
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200 MB


@router.post("/upload", response_model=CTUploadResponse)
@limiter.limit("10/minute")
async def upload_ct(
    request: Request,
    file: UploadFile = File(...),
):
    filename = file.filename or "upload"
    lowered = filename.lower()
    ext = "nii.gz" if lowered.endswith(".nii.gz") else lowered.split(".")[-1]
    if ext not in ("nii", "nii.gz", "dcm"):
        raise HTTPException(status_code=422, detail="Only .nii, .nii.gz, and .dcm files are supported")

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
):
    samples_dir = REPO_ROOT / "data" / "samples"
    if not samples_dir.is_dir():
        return {"patients": []}

    patient_ids = {
        path.name[:-7] if path.name.endswith(".nii.gz") else path.stem
        for path in samples_dir.iterdir()
        if path.is_file() and (path.name.endswith(".nii") or path.name.endswith(".nii.gz"))
    }
    return {"patients": sorted(patient_ids)}


@router.get("/demo/{patient_id}", response_model=CTUploadResponse)
@limiter.limit("20/minute")
async def get_demo_patient(
    patient_id: str,
    request: Request,
):
    samples_dir = REPO_ROOT / "data" / "samples"
    nii_path = samples_dir / f"{patient_id}.nii"
    nii_gz_path = samples_dir / f"{patient_id}.nii.gz"
    source_path = nii_path if nii_path.is_file() else nii_gz_path
    if not source_path.is_file():
        raise HTTPException(status_code=404, detail="Demo patient not found")

    content = source_path.read_bytes()
    filename = source_path.name
    s3_key = f"ct-uploads/{uuid.uuid4()}/demo-{filename}"
    meta = ct_service.load_ct(content, filename, s3_key)
    return meta
