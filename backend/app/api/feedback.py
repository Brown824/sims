"""
SIMS /feedback Endpoint
Logs user corrections for the future retraining pipeline.
Phase 1: Schema + stub. Phase 4: DB writes wired in.
"""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional

from app.db.database import save_feedback

router = APIRouter()


# ── Request / Response Schemas ───────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    sms_id: str = Field(
        ...,
        description="The request_id returned by /predict for this message.",
        example="550e8400-e29b-41d4-a716-446655440000",
    )
    user_verdict: str = Field(
        ...,
        description="User's correction: 'spam' or 'ham'.",
        example="ham",
    )
    original_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="The spam_score originally returned by /predict.",
        example=0.94,
    )
    comment: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional free-text comment from the user.",
    )


class FeedbackResponse(BaseModel):
    feedback_id: str
    status: str
    message: str
    timestamp: str


# ── Route ─────────────────────────────────────────────────────────────────────

@router.post("", response_model=FeedbackResponse)
async def submit_feedback(feedback: FeedbackRequest):
    """
    Submit a correction to a previous prediction.

    Logged to the feedback database for future retraining.
    Phase 4: This will write to MongoDB/SQLite via app.db.database.
    """
    feedback_id = str(uuid.uuid4())

    # Persist feedback to DB
    await save_feedback(
        request_id=feedback.sms_id,
        reported_verdict=feedback.user_verdict,
        original_verdict=None,  # Could be looked up from predictions table
        user_comment=feedback.comment,
    )

    return FeedbackResponse(
        feedback_id=feedback_id,
        status="logged",
        message="Asante! / Thank you. Your feedback will improve SIMS accuracy.",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
