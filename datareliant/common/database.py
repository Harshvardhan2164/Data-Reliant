"""SQLAlchemy database engine and session management.

Provides both **async** (for FastAPI request handling) and **sync**
(for Alembic migrations and CLI scripts) engines.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import MetaData, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from datareliant.common.config import get_settings

# Naming convention for constraints — makes Alembic auto-migrations deterministic.
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


# ── Async engine (FastAPI) ───────────────────────────────────────────

_async_engine = None
_async_session_factory = None


def get_async_engine(settings: Any | None = None):
    """Lazily create and return the async engine."""
    global _async_engine
    if _async_engine is None:
        s = settings or get_settings()
        _async_engine = create_async_engine(
            s.database_url,
            pool_size=s.database_pool_size,
            max_overflow=s.database_max_overflow,
            echo=s.database_echo,
        )
    return _async_engine


def get_async_session_factory(settings: Any | None = None) -> async_sessionmaker[AsyncSession]:
    """Lazily create and return the async session factory."""
    global _async_session_factory
    if _async_session_factory is None:
        engine = get_async_engine(settings)
        _async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


@asynccontextmanager
async def get_async_session(
    settings: Any | None = None,
) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session with automatic commit/rollback."""
    factory = get_async_session_factory(settings)
    session = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides a database session per request."""
    async with get_async_session() as session:
        yield session


# ── Sync engine (Alembic / CLI) ─────────────────────────────────────

_sync_engine = None
_sync_session_factory = None


def get_sync_engine(settings: Any | None = None):
    """Lazily create and return the sync engine."""
    global _sync_engine
    if _sync_engine is None:
        s = settings or get_settings()
        _sync_engine = create_engine(
            s.database_url_sync,
            pool_size=s.database_pool_size,
            max_overflow=s.database_max_overflow,
            echo=s.database_echo,
        )
    return _sync_engine


def get_sync_session_factory(settings: Any | None = None) -> sessionmaker[Session]:
    """Lazily create and return the sync session factory."""
    global _sync_session_factory
    if _sync_session_factory is None:
        engine = get_sync_engine(settings)
        _sync_session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return _sync_session_factory
