"""Health check endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from datareliant import __version__

router = APIRouter()


@router.get("/health", summary="Health check")
async def health_check() -> dict:
    """Return service health status."""
    return {
        "status": "healthy",
        "healthy": True,
        "ok": True,
        "version": __version__,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "datareliant-api",
    }


@router.get("/ready", summary="Readiness check")
async def readiness_check() -> dict:
    """Return service readiness status.

    In future phases, this will verify database connectivity
    and other critical dependencies.
    """
    return {
        "status": "ready",
        "checks": {
            "database": "ok",
        },
    }
