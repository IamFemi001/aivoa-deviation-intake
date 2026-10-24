"""
AIVOA Deviation Intake API — application entrypoint.

Run locally with:
    uvicorn app.main:app --reload

See README.md in this folder for full setup instructions.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deviations import router as deviations_router
from app.api.health import router as health_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging_config import configure_logging
from app.database.session import init_db

configure_logging()
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for the AI-Powered Deviation Intake Module.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# --- CORS: allow the React frontend (Vite dev server / deployed origin) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Stable error envelope for every raised AppError / validation error ---
register_exception_handlers(app)

# --- Routes ---
app.include_router(health_router)
app.include_router(deviations_router)


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("Starting %s (environment=%s)", settings.APP_NAME, settings.ENVIRONMENT)
    init_db()
    if not settings.AI_SERVICE_ENABLED:
        logger.warning(
            "AI_SERVICE_ENABLED is false — using the deterministic stub AI service. "
            "Set AI_SERVICE_ENABLED=true and configure GROQ_API_KEY to use the real pipeline."
        )


@app.get("/")
async def root():
    return {"service": settings.APP_NAME, "docs": "/docs"}
