"""FastAPI application entry point for DataReliant API.

Configures middleware, exception handlers, and route mounting.
All business logic lives in the ``datareliant`` package — routes are thin.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.api.routes import anomalies, datasets, evaluations, health, incidents, pipelines, quality
from datareliant import __version__
from datareliant.common.config import get_settings
from datareliant.common.exceptions import DataReliantError
from datareliant.common.logging import setup_logging

logger = structlog.get_logger(__name__)


# ── Lifespan ─────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown hooks."""
    settings = get_settings()
    setup_logging(
        log_level=settings.log_level,
        json_output=settings.is_production,
    )
    logger.info(
        "datareliant.startup",
        version=__version__,
        env=settings.app_env.value,
    )
    yield
    logger.info("datareliant.shutdown")


# ── Application factory ─────────────────────────────────────────────


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="DataReliant API",
        description=(
            "Autonomous Data Quality, Anomaly Detection & Root-Cause Intelligence Platform"
        ),
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ── CORS ─────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request-ID middleware ────────────────────────────────────────
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # ── Exception handlers ───────────────────────────────────────────
    @app.exception_handler(DataReliantError)
    async def domain_exception_handler(request: Request, exc: DataReliantError) -> JSONResponse:
        """Convert domain exceptions into structured JSON error responses."""
        request_id = request.headers.get("X-Request-ID", "unknown")
        logger.warning(
            "domain_error",
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
        )
        body: dict[str, Any] = {
            **exc.to_dict(),
            "request_id": request_id,
        }
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Catch-all handler — never expose raw stack traces in production."""
        request_id = request.headers.get("X-Request-ID", "unknown")
        logger.exception("unhandled_error", request_id=request_id)
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred.",
                "details": {},
                "request_id": request_id,
            },
        )

    # ── Routes ───────────────────────────────────────────────────────
    app.include_router(health.router, tags=["Health"])
    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(datasets.router, prefix="/api/v1", tags=["Datasets"])
    app.include_router(quality.router, prefix="/api/v1", tags=["Quality"])
    app.include_router(anomalies.router, prefix="/api/v1", tags=["Anomalies"])
    app.include_router(pipelines.router, prefix="/api/v1", tags=["Pipelines"])
    app.include_router(incidents.router, prefix="/api/v1", tags=["Incidents"])
    app.include_router(evaluations.router, prefix="/api/v1", tags=["Evaluations"])

    return app


app = create_app()
