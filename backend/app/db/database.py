"""
SIMS Database — Real aiosqlite Implementation
Stores predictions and feedback for model retraining and analytics.
"""

import aiosqlite
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from loguru import logger
from app.config import settings

DB_PATH = settings.SQLITE_PATH

CREATE_PREDICTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS predictions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id      TEXT    NOT NULL UNIQUE,
    sms_text        TEXT    NOT NULL,
    phone_number    TEXT,
    spam_score      REAL    NOT NULL,
    verdict         TEXT    NOT NULL,
    confidence      TEXT    NOT NULL,
    url_threat      INTEGER NOT NULL DEFAULT 0,
    urls_found      TEXT,           -- JSON array
    model_version   TEXT,
    inference_mode  TEXT,
    created_at      TEXT    NOT NULL
);
"""

CREATE_FEEDBACK_TABLE = """
CREATE TABLE IF NOT EXISTS feedback (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id      TEXT    NOT NULL,
    reported_verdict TEXT   NOT NULL,
    original_verdict TEXT,
    user_comment    TEXT,
    created_at      TEXT    NOT NULL,
    FOREIGN KEY (request_id) REFERENCES predictions(request_id)
);
"""

CREATE_URL_CACHE_TABLE = """
CREATE TABLE IF NOT EXISTS url_cache (
    url_hash        TEXT    PRIMARY KEY,
    url             TEXT    NOT NULL,
    is_malicious    INTEGER NOT NULL DEFAULT 0,
    malicious_count INTEGER NOT NULL DEFAULT 0,
    total_engines   INTEGER NOT NULL DEFAULT 0,
    cached_at       TEXT    NOT NULL
);
"""

_db: Optional[aiosqlite.Connection] = None


async def get_db() -> aiosqlite.Connection:
    """Return (and initialise) the global SQLite connection."""
    global _db
    if _db is None:
        _db = await aiosqlite.connect(DB_PATH)
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL;")
        await _db.execute("PRAGMA foreign_keys=ON;")
        await _db.execute(CREATE_PREDICTIONS_TABLE)
        await _db.execute(CREATE_FEEDBACK_TABLE)
        await _db.execute(CREATE_URL_CACHE_TABLE)
        await _db.commit()
        logger.info(f"✅ SQLite connected: {DB_PATH}")
    return _db


async def close_db() -> None:
    global _db
    if _db:
        await _db.close()
        _db = None
        logger.info("SQLite connection closed.")


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
    db = await get_db()
    try:
        await db.execute(
            """INSERT OR IGNORE INTO predictions
               (request_id, sms_text, phone_number, spam_score, verdict,
                confidence, url_threat, urls_found, model_version,
                inference_mode, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                request_id, sms_text, phone_number, spam_score, verdict,
                confidence, int(url_threat), json.dumps(urls_found),
                model_version, inference_mode,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to save prediction {request_id}: {e}")


async def get_recent_predictions(limit: int = 50) -> List[Dict[str, Any]]:
    db = await get_db()
    async with db.execute(
        "SELECT * FROM predictions ORDER BY created_at DESC LIMIT ?", (limit,)
    ) as cursor:
        rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_stats() -> Dict[str, Any]:
    db = await get_db()
    async with db.execute(
        "SELECT COUNT(*) as total, SUM(verdict='SPAM') as spam, "
        "SUM(verdict='HAM') as ham, SUM(verdict='SUSPICIOUS') as suspicious "
        "FROM predictions"
    ) as cursor:
        row = await cursor.fetchone()
    return dict(row) if row else {}


# ── Feedback ──────────────────────────────────────────────────────────────────

async def save_feedback(
    request_id: str,
    reported_verdict: str,
    original_verdict: Optional[str] = None,
    user_comment: Optional[str] = None,
) -> None:
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO feedback
               (request_id, reported_verdict, original_verdict, user_comment, created_at)
               VALUES (?,?,?,?,?)""",
            (
                request_id, reported_verdict, original_verdict, user_comment,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to save feedback for {request_id}: {e}")


# ── URL Cache ─────────────────────────────────────────────────────────────────

async def get_cached_url(url_hash: str) -> Optional[Dict[str, Any]]:
    db = await get_db()
    async with db.execute(
        "SELECT * FROM url_cache WHERE url_hash=?", (url_hash,)
    ) as cursor:
        row = await cursor.fetchone()
    return dict(row) if row else None


async def cache_url_result(
    url_hash: str,
    url: str,
    is_malicious: bool,
    malicious_count: int,
    total_engines: int,
) -> None:
    db = await get_db()
    try:
        await db.execute(
            """INSERT OR REPLACE INTO url_cache
               (url_hash, url, is_malicious, malicious_count, total_engines, cached_at)
               VALUES (?,?,?,?,?,?)""",
            (
                url_hash, url, int(is_malicious), malicious_count,
                total_engines, datetime.now(timezone.utc).isoformat(),
            ),
        )
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to cache URL result: {e}")


# ── Legacy compat shims ───────────────────────────────────────────────────────

class SQLiteClient:
    """Legacy compat wrapper — used by main.py lifespan."""
    async def connect(self): await get_db()
    async def close(self): await close_db()


_db_client = None

async def get_db_client():
    global _db_client
    if _db_client is None:
        _db_client = SQLiteClient()
        await _db_client.connect()
    return _db_client

async def close_db_legacy():
    await close_db()
