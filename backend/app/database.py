# -*- coding: utf-8 -*-
"""Async SQLAlchemy engine, session factory and base declarative model."""
from typing import AsyncGenerator

from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


def _normalize_database_url(raw_url: str) -> URL:
    """Return a SQLAlchemy URL suitable for the async engine."""
    url = make_url(raw_url)

    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+asyncpg")

    if url.drivername in {"http", "https"} and (url.host or "").endswith("supabase.co"):
        raise RuntimeError(
            "DATABASE_URL must be the Supabase Postgres connection string, not the "
            "project API URL. Use the value from Supabase Dashboard > Connect > "
            "Session pooler or Direct connection."
        )

    if url.drivername == "postgresql+asyncpg":
        sslmode = url.query.get("sslmode")
        if sslmode and "ssl" not in url.query:
            url = url.difference_update_query(["sslmode"]).update_query_dict({"ssl": sslmode})

        host = url.host or ""
        is_supabase = host.endswith("supabase.co") or "pooler.supabase.com" in host
        if is_supabase and "ssl" not in url.query:
            url = url.update_query_dict({"ssl": "require"})

    return url


def _is_postgres(url: URL) -> bool:
    return url.get_backend_name() == "postgresql"


def _is_supabase_transaction_pooler(url: URL) -> bool:
    host = url.host or ""
    return "pooler.supabase.com" in host and url.port == 6543


def _engine_options(url: URL) -> dict:
    options = {"echo": settings.DB_ECHO, "future": True}

    if _is_postgres(url):
        options.update(
            pool_pre_ping=True,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
        )

        if settings.DB_DISABLE_PREPARED_STATEMENT_CACHE or _is_supabase_transaction_pooler(url):
            options["connect_args"] = {"statement_cache_size": 0}

    return options


database_url = _normalize_database_url(settings.DATABASE_URL)
if (
    _is_postgres(database_url)
    and (settings.DB_DISABLE_PREPARED_STATEMENT_CACHE or _is_supabase_transaction_pooler(database_url))
    and "prepared_statement_cache_size" not in database_url.query
):
    database_url = database_url.update_query_dict({"prepared_statement_cache_size": "0"})

engine = create_async_engine(database_url, **_engine_options(database_url))
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session per request."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """Create all tables on startup (dev/SQLite). Use Alembic for production."""
    from app import models  # noqa: F401  Ensures metadata is registered before create_all.

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
