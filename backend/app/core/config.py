"""
Centralized application configuration, loaded from environment variables
(see .env.example). Every other module reads settings from here rather
than calling os.environ directly, so there is exactly one place that
knows how configuration is sourced.
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "AIVOA Deviation Intake API"
    ENVIRONMENT: str = "development"  # development | staging | production
    DEBUG: bool = True

    # --- CORS ---
    # Comma-separated list of allowed origins, e.g.
    # "http://localhost:5173,https://app.aivoa.ai"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # --- Database ---
    # Required (assignment spec): PostgreSQL, via
    #   DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:PORT/DATABASE
    # There is deliberately no SQLite default: the final application must
    # be explicitly configured against the required relational database.
    DATABASE_URL: str

    # --- File uploads ---
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_UPLOAD_EXTENSIONS: str = ".pdf,.txt"

    # --- AI service (LangGraph + Groq) ---
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    AI_SERVICE_ENABLED: bool = True  # False => use the deterministic stub service for offline/local testing
    AI_REQUEST_TIMEOUT_SECONDS: int = 60

    # --- Logging ---
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def allowed_upload_extensions_list(self) -> List[str]:
        return [ext.strip().lower() for ext in self.ALLOWED_UPLOAD_EXTENSIONS.split(",") if ext.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — env is read once per process."""
    return Settings()
