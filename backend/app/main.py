# -*- coding: utf-8 -*-
"""
CineAI — FastAPI application entry point.

Startup sequence:
1. Initialize SQLite/PostgreSQL schema (dev uses SQLite via aiosqlite)
2. Pre-warm TMDB genres cache so the first request is fast
3. Register all routers under /api/v1
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.config import settings
from app.database import init_db
from app.routers import auth, recommendations, analytics

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger("cineai")

app = FastAPI(
    title="CineAI API",
    description="RESTful backend for the CineAI movie & series recommendation system.",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(recommendations.router, prefix=API_PREFIX)
app.include_router(analytics.router, prefix=API_PREFIX)

# ---------------------------------------------------------------------------
# Static frontend (served from ../frontend)
# ---------------------------------------------------------------------------
_FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"
if _FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_FRONTEND_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        return FileResponse(str(_FRONTEND_DIR / "index.html"))

    @app.get("/login", include_in_schema=False)
    async def serve_login():
        return FileResponse(str(_FRONTEND_DIR / "login.html"))

    @app.get("/dashboard", include_in_schema=False)
    async def serve_dashboard():
        return FileResponse(str(_FRONTEND_DIR / "dashboard.html"))

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def on_startup():
    log.info("CineAI starting up...")
    await init_db()
    # Pre-warm genres cache (non-blocking — best-effort)
    try:
        from app.services.tmdb import get_genres
        get_genres()
        log.info("TMDB genres cache warmed up.")
    except Exception as exc:
        log.warning("Could not pre-warm genres cache: %s", exc)


@app.get("/api/health", tags=["health"])
async def health():
    return {"status": "ok", "version": "2.0.0"}
