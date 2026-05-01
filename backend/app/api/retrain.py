"""
SIMS /retrain Admin Endpoint
Triggers model retraining pipeline (stub for Phase 6).
Protected by ADMIN_API_KEY header.
"""

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from app.config import settings

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────────

class RetrainResponse(BaseModel):
    status: str
    message: str
    model_version: str


class RetrainRequest(BaseModel):
    force: bool = False
    notify_on_complete: bool = False


# ── Route ──────────────────────────────────────────────────────────────────────

@router.post("", response_model=RetrainResponse)
async def trigger_retrain(
    request: RetrainRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Admin endpoint to trigger model retraining.

    Requires `X-API-Key` header matching `ADMIN_API_KEY` env var.
    Phase 6: Will spawn background training job.
    """
    if not x_api_key or x_api_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin API key",
        )

    if settings.ADMIN_API_KEY in ("", "change_me"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_API_KEY not configured",
        )

    # TODO Phase 6: Spawn background training task
    # e.g. asyncio.create_task(run_training_pipeline(force=request.force))

    return RetrainResponse(
        status="queued",
        message="Retraining pipeline queued successfully.",
        model_version=settings.MODEL_VERSION,
    )

