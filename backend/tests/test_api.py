"""
SIMS Backend API Tests
Run: cd backend && pytest tests/test_api.py -v
"""
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.database import close_db


@pytest.fixture(scope="module")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def async_client():
    """Async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    await close_db()


# ── Health ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_check(async_client):
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "model_version" in data
    assert "model_loaded" in data
    assert "db_configured" in data


# ── Predict ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_predict_ham(async_client):
    payload = {
        "sms_text": "Hi mom, I'll be home by 6pm. Love you!",
        "phone_number": "+255712345678"
    }
    response = await async_client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["verdict"] in ("HAM", "SUSPICIOUS", "SPAM")
    assert 0.0 <= data["spam_score"] <= 1.0
    assert data["model_version"] == "1.0.0"
    assert data["inference_mode"] == "cloud"


@pytest.mark.asyncio
async def test_predict_spam_with_url(async_client):
    payload = {
        "sms_text": "Umeshinda! Bonyeza hapa: http://scam.link",
        "phone_number": "+255712345678"
    }
    response = await async_client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "verdict" in data
    assert len(data["urls_found"]) > 0
    assert data["url_threat"] is False  # VT not configured in tests


@pytest.mark.asyncio
async def test_predict_empty_text(async_client):
    payload = {"sms_text": ""}
    response = await async_client.post("/predict", json=payload)
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_predict_too_long(async_client):
    payload = {"sms_text": "x" * 1601}
    response = await async_client.post("/predict", json=payload)
    assert response.status_code == 422  # Validation error


# ── Feedback ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_feedback_submission(async_client):
    payload = {
        "sms_id": "550e8400-e29b-41d4-a716-446655440000",
        "user_verdict": "ham",
        "original_score": 0.94,
        "comment": "This was actually a real message from my bank."
    }
    response = await async_client.post("/feedback", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "logged"
    assert "feedback_id" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_feedback_missing_sms_id(async_client):
    payload = {"user_verdict": "spam"}
    response = await async_client.post("/feedback", json=payload)
    assert response.status_code == 422


# ── Retrain (Admin) ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_retrain_unauthorized(async_client):
    payload = {"force": False}
    response = await async_client.post("/retrain", json=payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_retrain_with_bad_key(async_client):
    payload = {"force": False}
    response = await async_client.post(
        "/retrain", json=payload, headers={"X-API-Key": "wrong_key"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_retrain_with_valid_key(async_client):
    payload = {"force": False}
    response = await async_client.post(
        "/retrain", json=payload, headers={"X-API-Key": "change_me"}
    )
    # "change_me" is the default key, but the endpoint rejects it as not configured
    assert response.status_code == 503


# ── Root ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_root_endpoint(async_client):
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "SIMS"
    assert "status" in data
    assert "docs" in data

