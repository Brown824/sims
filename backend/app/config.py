"""
SIMS Configuration — Pydantic BaseSettings
Loads from .env file automatically.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────
    APP_NAME: str = "SIMS"
    APP_ENV: str = "development"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    PORT: int = 8000

    # ── VirusTotal ───────────────────────────
    VIRUSTOTAL_API_KEY: str = ""
    VIRUSTOTAL_BASE_URL: str = "https://www.virustotal.com/api/v3"

    # ── Database ─────────────────────────────
    MONGODB_URI: str = ""
    MONGODB_DB_NAME: str = "sims"
    SQLITE_PATH: str = "./sims.db"
    DB_BACKEND: str = "sqlite"   # "mongodb" | "sqlite"

    # ── ML Model ─────────────────────────────
    MODEL_PATH: str = "./data/models/sims_model.h5"
    TFLITE_MODEL_PATH: str = "./data/models/sims_offline.tflite"
    MODEL_VERSION: str = "1.0.0"

    # ── Thresholds ───────────────────────────
    SPAM_BLOCK_THRESHOLD: float = 0.85
    SPAM_WARN_THRESHOLD: float = 0.60

    # ── Security ─────────────────────────────
    ADMIN_API_KEY: str = "change_me"

    # ── CORS ─────────────────────────────────
    ALLOWED_ORIGINS: List[str] = ["*"]

    # ── Logging ──────────────────────────────
    LOG_LEVEL: str = "INFO"

    # ── Rate Limiting ────────────────────────
    VT_REQUESTS_PER_MINUTE: int = 4
    VT_REQUESTS_PER_DAY: int = 500

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def vt_configured(self) -> bool:
        return bool(self.VIRUSTOTAL_API_KEY and self.VIRUSTOTAL_API_KEY != "your_virustotal_api_key_here")

    @property
    def db_configured(self) -> bool:
        if self.DB_BACKEND == "mongodb":
            return bool(self.MONGODB_URI and "<password>" not in self.MONGODB_URI)
        return True  # SQLite always works


# Singleton instance — import this everywhere
settings = Settings()
