"""
SIMS Backend — FastAPI Application Entry Point
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.config import settings
from app.api.health import router as health_router
from app.api.predict import router as predict_router
from app.api.feedback import router as feedback_router
from app.api.retrain import router as retrain_router

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "SMS Intelligent Monitoring System — Bilingual (Swahili + English) "
        "spam & phishing detector for Tanzanian Android users."
    ),
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(health_router, tags=["Health"])
app.include_router(predict_router, prefix="/predict", tags=["Prediction"])
app.include_router(feedback_router, prefix="/feedback", tags=["Feedback"])
app.include_router(retrain_router, prefix="/retrain", tags=["Admin"])

# ── Global Exception Handler ──────────────────────────────────────────────────

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

# ── Lifecycle ─────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} starting...")
    logger.info(f"   Environment : {settings.APP_ENV}")
    logger.info(f"   DB Backend  : {settings.DB_BACKEND}")
    logger.info(f"   Spam Block  : >= {settings.SPAM_BLOCK_THRESHOLD}")
    logger.info(f"   Spam Warn   : >= {settings.SPAM_WARN_THRESHOLD}")

    # Initialise database
    try:
        from app.db.database import get_db
        await get_db()
        logger.info("✅ Database ready")
    except Exception as e:
        logger.error(f"Database init failed: {e}")

    # Load ML model (non-fatal if model file not yet trained)
    try:
        from app.ml.model import get_model
        model = get_model()
        loaded = model.load()
        if loaded:
            logger.info(f"✅ ML model loaded (v{settings.MODEL_VERSION})")
        else:
            logger.warning(
                "⚠️  ML model file not found. "
                "Run: python scripts/train_model.py to train and export the model."
            )
    except Exception as e:
        logger.error(f"Model load failed: {e}")

    # Log VirusTotal status
    if settings.vt_configured:
        logger.info("✅ VirusTotal API configured")
    else:
        logger.warning("⚠️  VirusTotal API key not set — URL scanning disabled")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 SIMS shutting down...")
    from app.db.database import close_db
    await close_db()


# ── Root ──────────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root():
    from app.ml.model import get_model
    model = get_model()
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "model_loaded": model.is_loaded,
        "vt_configured": settings.vt_configured,
        "docs": "/docs",
    }
