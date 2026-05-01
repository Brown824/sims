"""
SIMS /health Endpoint
Returns service status, model version, and uptime.
Used by mobile app to decide online vs offline inference mode.
"""

import time
from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings
from app.ml.model import get_model

router = APIRouter()

# Track server start time
_START_TIME = time.time()
_request_count = 0


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    environment: str
    uptime_seconds: float
    model_version: str
    model_loaded: bool
    db_backend: str
    db_configured: bool
    vt_configured: bool
    timestamp: str


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    Mobile app calls this before deciding which inference path to use.
    Returns 200 if online mode is available.
    """
    global _request_count
    _request_count += 1

    model_loaded = get_model().is_loaded

    return HealthResponse(
        status="ok",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        uptime_seconds=round(time.time() - _START_TIME, 2),
        model_version=settings.MODEL_VERSION,
        model_loaded=model_loaded,
        db_backend=settings.DB_BACKEND,
        db_configured=settings.db_configured,
        vt_configured=settings.vt_configured,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
