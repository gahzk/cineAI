# -*- coding: utf-8 -*-
"""Application settings loaded from environment variables."""
import tempfile
from pathlib import Path
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- API ---
    TMDB_BEARER_TOKEN: str = Field(
        default="",
        validation_alias=AliasChoices("TMDB_BEARER_TOKEN", "TMDB_TOKEN"),
    )
    TMDB_API_KEY: str = Field(default="", validation_alias="TMDB_API_KEY")
    TMDB_BASE_URL: str = "https://api.themoviedb.org/3"
    TMDB_IMAGE_BASE_URL: str = "https://image.tmdb.org/t/p/w500"

    # --- Database ---
    DATABASE_URL: str = "sqlite+aiosqlite:///./cineai.db"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_DISABLE_PREPARED_STATEMENT_CACHE: bool = False

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
        extra = "ignore"


settings = Settings()
settings.CACHE_DIR.mkdir(parents=True, exist_ok=True)
