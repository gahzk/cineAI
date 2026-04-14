# -*- coding: utf-8 -*-
"""Application settings loaded from environment variables."""
import tempfile
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- API ---
    TMDB_BEARER_TOKEN: str = ""
    TMDB_BASE_URL: str = "https://api.themoviedb.org/3"

    # --- Database ---
    DATABASE_URL: str = "sqlite+aiosqlite:///./cineai.db"

    # --- Auth / JWT ---
    SECRET_KEY: str = "change-me-in-production-use-secrets"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # --- Cache ---
    CACHE_DIR: Path = Path(tempfile.gettempdir()) / "cineai_cache"
    CACHE_EXPIRATION_DAYS: int = 7
    CATALOG_TARGET: int = 2500

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["*"]

    # --- Rate limiting ---
    MIN_REQUEST_INTERVAL: float = 0.05
    HTTP_WORKERS: int = 10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
settings.CACHE_DIR.mkdir(parents=True, exist_ok=True)
