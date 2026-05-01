"""
SIMS Database — Supabase Implementation
Stores predictions and feedback for model retraining and analytics.
"""

from typing import Optional, List, Dict, Any
from loguru import logger
from app.config import settings
from supabase import create_client, Client
import json
from datetime import datetime, timezone

SUPABASE_URL = "https://nfkukvpcrtgqdeoqlesr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5ma3VrdnBjcnRncWRlb3FsZXNyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc2MjUyNTcsImV4cCI6MjA5MzIwMTI1N30.EE3ACs49oYa9VOkcQrha4SPzp4x1qIRa-aXKXe8VU3A"

_supabase: Optional[Client] = None

async def get_db() -> Client:
    """Return the global Supabase client."""
    global _supabase
    if _supabase is None:
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("✅ Supabase client initialized")
    return _supabase

async def close_db() -> None:
    # Supabase HTTP client doesn't need explicit closing in this context
    pass

# ── Predictions ───────────────────────────────────────────────────────────────

async def save_prediction(
    request_id: str,
    sms_text: str,
    phone_number: Optional[str],
    spam_score: float,
    verdict: str,
    confidence: str,
    url_threat: bool,
    urls_found: List[str],
    model_version: str,
    inference_mode: str,
) -> None:
    supabase = await get_db()
    try:
        data = {
            "request_id": request_id,
            "sms_text": sms_text,
            "phone_number": phone_number,
            "spam_score": spam_score,
            "verdict": verdict,
            "confidence": confidence,
            "url_threat": url_threat,
            "urls_found": urls_found, # Supabase handles list to JSONB conversion
            "model_version": model_version,
            "inference_mode": inference_mode,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        # Ignore errors if request_id already exists (duplicate)
        supabase.table("predictions").upsert(data, on_conflict="request_id").execute()
    except Exception as e:
        logger.error(f"Failed to save prediction {request_id} to Supabase: {e}")

async def get_recent_predictions(limit: int = 50) -> List[Dict[str, Any]]:
    supabase = await get_db()
    try:
        response = supabase.table("predictions").select("*").order("created_at", desc=True).limit(limit).execute()
        return response.data
    except Exception as e:
        logger.error(f"Failed to get recent predictions: {e}")
        return []

async def get_stats() -> Dict[str, Any]:
    supabase = await get_db()
    try:
        # Simplistic approach since Supabase client doesn't do complex agg easily in one query
        # For a small dashboard, we fetch all (or limit) and count in memory for now
        response = supabase.table("predictions").select("verdict").execute()
        predictions = response.data
        total = len(predictions)
        spam = sum(1 for p in predictions if p.get("verdict") == "SPAM")
        ham = sum(1 for p in predictions if p.get("verdict") == "HAM")
        suspicious = sum(1 for p in predictions if p.get("verdict") == "SUSPICIOUS")
        return {"total": total, "spam": spam, "ham": ham, "suspicious": suspicious}
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return {"total": 0, "spam": 0, "ham": 0, "suspicious": 0}

# ── Feedback ──────────────────────────────────────────────────────────────────

async def save_feedback(
    request_id: str,
    reported_verdict: str,
    original_verdict: Optional[str] = None,
    user_comment: Optional[str] = None,
) -> None:
    supabase = await get_db()
    try:
        data = {
            "request_id": request_id,
            "reported_verdict": reported_verdict,
            "original_verdict": original_verdict,
            "user_comment": user_comment,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        supabase.table("feedback").insert(data).execute()
    except Exception as e:
        logger.error(f"Failed to save feedback for {request_id}: {e}")

# ── URL Cache ─────────────────────────────────────────────────────────────────

async def get_cached_url(url_hash: str) -> Optional[Dict[str, Any]]:
    supabase = await get_db()
    try:
        response = supabase.table("url_cache").select("*").eq("url_hash", url_hash).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Failed to get cached URL: {e}")
        return None

async def cache_url_result(
    url_hash: str,
    url: str,
    is_malicious: bool,
    malicious_count: int,
    total_engines: int,
) -> None:
    supabase = await get_db()
    try:
        data = {
            "url_hash": url_hash,
            "url": url,
            "is_malicious": is_malicious,
            "malicious_count": malicious_count,
            "total_engines": total_engines,
            "cached_at": datetime.now(timezone.utc).isoformat()
        }
        supabase.table("url_cache").upsert(data, on_conflict="url_hash").execute()
    except Exception as e:
        logger.error(f"Failed to cache URL result: {e}")

# ── Legacy compat shims ───────────────────────────────────────────────────────

class SupabaseClient:
    """Legacy compat wrapper — used by main.py lifespan."""
    async def connect(self): await get_db()
    async def close(self): await close_db()

_db_client = None

async def get_db_client():
    global _db_client
    if _db_client is None:
        _db_client = SupabaseClient()
        await _db_client.connect()
    return _db_client

async def close_db_legacy():
    await close_db()
