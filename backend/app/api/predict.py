"""
SIMS /predict Endpoint — Real ML Inference + VirusTotal
"""
import re
import time
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Dict

from app.config import settings
from app.ml.model import SIMSModel, get_model
from app.ml.preprocessor import SMSPreprocessor, get_preprocessor
from app.services.virustotal import VirusTotalClient, get_vt_client, URLScanResult
from app.db.database import save_prediction

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────────

class PredictRequest(BaseModel):
    sms_text: str = Field(..., min_length=1, max_length=1600,
        description="The raw SMS message to classify.",
        example="Umeshinda! Bonyeza hapa kupata zawadi: http://scam.link")
    phone_number: Optional[str] = Field(None, example="+255712345678")


class URLThreatDetail(BaseModel):
    url: str
    is_malicious: bool
    vt_positives: Optional[int] = None
    vt_total: Optional[int] = None
    error: Optional[str] = None


class PredictResponse(BaseModel):
    request_id: str
    spam_score: float = Field(..., ge=0.0, le=1.0)
    verdict: str       # SPAM | SUSPICIOUS | HAM
    confidence: str    # HIGH | MEDIUM | LOW
    url_threat: bool
    urls_found: List[str]
    url_details: List[URLThreatDetail]
    model_version: str
    inference_mode: str
    model_loaded: bool
    timestamp: str


# ── Helpers ────────────────────────────────────────────────────────────────────

URL_PATTERN = re.compile(r'https?://\S+', re.IGNORECASE)

def extract_urls(text: str) -> List[str]:
    return URL_PATTERN.findall(text)


def compute_verdict(spam_score: float, url_threat: bool):
    if url_threat:
        return "SPAM", "HIGH"
    if spam_score >= settings.SPAM_BLOCK_THRESHOLD:
        return "SPAM", "HIGH"
    if spam_score >= settings.SPAM_WARN_THRESHOLD:
        return "SUSPICIOUS", "MEDIUM"
    confidence = "HIGH" if spam_score < 0.30 else "LOW"
    return "HAM", confidence


# ── Rate Limiting ─────────────────────────────────────────────────────────────

_rate_limit_store: Dict[str, List[float]] = {}
RATE_LIMIT_WINDOW = 60      # seconds
RATE_LIMIT_MAX = 10         # requests per window

async def rate_limit(request: Request):
    """Lightweight in-memory rate limiter (per client IP)."""
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = _rate_limit_store.setdefault(client_ip, [])
    # drop expired timestamps
    window[:] = [t for t in window if now - t < RATE_LIMIT_WINDOW]
    if len(window) >= RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")
    window.append(now)


# ── Route ──────────────────────────────────────────────────────────────────────

def _heuristic_predict(text: str) -> float:
    """Fallback prediction matching the offline mobile logic."""
    lower = text.lower()
    spam_keywords = [
        "umeshinda", "zawadi", "bonyeza hapa", "tuma pesa", "nambari",
        "akaunti imezuiwa", "thibitisha", "bila malipo", "haraka",
        "winner", "free", "click here", "claim now", "urgent",
        "verify account", "bank suspended", "password reset",
        "lottery", "prize", "send money", "reply now"
    ]
    
    score = 0.1
    for kw in spam_keywords:
        if kw in lower:
            score += 0.15

    if re.search(r'https?://\S+', lower): score += 0.2
    if re.search(r'\+?\d[\d\s\-]{7,}\d', lower): score += 0.1
    if re.search(r'\b(haraka|urgent|sasa hivi|leo tu|immediately)\b', lower): score += 0.1

    return min(score, 0.99)

@router.post("", response_model=PredictResponse)
async def predict(request: PredictRequest, _=Depends(rate_limit)):
    """
    Classify SMS as SPAM / SUSPICIOUS / HAM.
    Flow: URL extraction → VirusTotal scan → CNN-GRU inference → verdict
    """
    request_id = str(uuid.uuid4())
    urls = extract_urls(request.sms_text)

    # 1. VirusTotal URL scan (async, graceful fallback)
    url_threat = False
    url_details: List[URLThreatDetail] = []

    if urls and settings.vt_configured:
        vt_client: VirusTotalClient = get_vt_client()
        try:
            vt_results: List[URLScanResult] = await vt_client.scan_urls(urls)
            for r in vt_results:
                url_details.append(URLThreatDetail(
                    url=r.url,
                    is_malicious=r.is_malicious,
                    vt_positives=r.malicious_count,
                    vt_total=r.total_engines,
                    error=r.error,
                ))
                if r.is_malicious:
                    url_threat = True
        except Exception as e:
            # VT failure is non-fatal — continue with model only
            for url in urls:
                url_details.append(URLThreatDetail(url=url, is_malicious=False, error=str(e)))
    else:
        for url in urls:
            status = "VT_KEY_NOT_CONFIGURED" if not settings.vt_configured else None
            url_details.append(URLThreatDetail(url=url, is_malicious=False, error=status))

    # 2. CNN-GRU inference
    model: SIMSModel = get_model()
    preprocessor: SMSPreprocessor = get_preprocessor()
    model_loaded = model.is_loaded
    spam_score = 0.0

    if model_loaded:
        try:
            token_seq = preprocessor.encode(request.sms_text)
            spam_score = model.predict_single(token_seq)
        except Exception as e:
            # Model error → fallback
            spam_score = _heuristic_predict(request.sms_text)
    else:
        spam_score = _heuristic_predict(request.sms_text)

    # 3. Verdict
    verdict, confidence = compute_verdict(spam_score, url_threat)

    # 4. Persist to DB
    await save_prediction(
        request_id=request_id,
        sms_text=request.sms_text,
        phone_number=request.phone_number,
        spam_score=spam_score,
        verdict=verdict,
        confidence=confidence,
        url_threat=url_threat,
        urls_found=urls,
        model_version=settings.MODEL_VERSION,
        inference_mode="cloud",
    )

    return PredictResponse(
        request_id=request_id,
        spam_score=round(spam_score, 4),
        verdict=verdict,
        confidence=confidence,
        url_threat=url_threat,
        urls_found=urls,
        url_details=url_details,
        model_version=settings.MODEL_VERSION,
        inference_mode="cloud",
        model_loaded=model_loaded,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
