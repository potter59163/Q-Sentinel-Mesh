"""Radiologist feedback route — human-in-the-loop verdicts."""
import uuid
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, List, Literal, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.core.rate_limit import limiter

router = APIRouter(prefix="/api", tags=["feedback"])

# In-memory store (demo). In production: DynamoDB / RDS.
_store: List[Dict] = []
_lock = Lock()


class FeedbackRequest(BaseModel):
    session_id: str
    verdict: Literal["confirm", "reject", "correct"]
    correction: Optional[str] = None  # corrected class if verdict == "correct"
    hospital: str
    top_class: str
    confidence: float
    filename: Optional[str] = None


class FeedbackResponse(BaseModel):
    feedback_id: str
    saved: bool


class FeedbackStats(BaseModel):
    total: int
    confirm: int
    reject: int
    correct: int
    accuracy_rate: float  # confirm / total


@router.post("/feedback", response_model=FeedbackResponse)
@limiter.limit("30/minute")
async def submit_feedback(request: Request, body: FeedbackRequest):
    feedback_id = str(uuid.uuid4())
    entry = {
        "feedback_id": feedback_id,
        "session_id": body.session_id,
        "verdict": body.verdict,
        "correction": body.correction,
        "hospital": body.hospital,
        "top_class": body.top_class,
        "confidence": body.confidence,
        "filename": body.filename,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with _lock:
        _store.append(entry)
    return FeedbackResponse(feedback_id=feedback_id, saved=True)


@router.get("/feedback/stats", response_model=FeedbackStats)
@limiter.limit("30/minute")
async def get_feedback_stats(request: Request):
    with _lock:
        entries = list(_store)

    total = len(entries)
    if total == 0:
        return FeedbackStats(total=0, confirm=0, reject=0, correct=0, accuracy_rate=0.0)

    confirm = sum(1 for e in entries if e["verdict"] == "confirm")
    reject = sum(1 for e in entries if e["verdict"] == "reject")
    correct = sum(1 for e in entries if e["verdict"] == "correct")
    accuracy_rate = round(confirm / total, 4)

    return FeedbackStats(
        total=total,
        confirm=confirm,
        reject=reject,
        correct=correct,
        accuracy_rate=accuracy_rate,
    )
