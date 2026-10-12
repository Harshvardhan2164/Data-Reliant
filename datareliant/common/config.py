"""Application configuration loaded from environment variables.

All settings are defined with sensible local-development defaults.
GCP and LLM settings are optional and the system works without them.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Deployment environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class StorageBackend(str, Enum):
    """Supported storage backends."""

    LOCAL = "local"
    GCS = "gcs"


class Settings(BaseSettings):
    """Central application settings.

    Values are loaded from environment variables first, then ``.env`` file.
    This allows Docker, CI, and production overrides.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── General ──────────────────────────────────────────────────────
    app_env: Environment = Environment.DEVELOPMENT
    debug: bool = True
    log_level: str = "INFO"
    secret_key: str = "change-me-in-production"
    app_name: str = "DataReliant"
    app_version: str = "0.1.0"

    # ── Database ─────────────────────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://datareliant:datareliant@localhost:5432/datareliant"
    )
    database_url_sync: str = (
        "postgresql+psycopg2://datareliant:datareliant@localhost:5432/datareliant"
    )
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_echo: bool = False

    # ── API ──────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # ── Storage ──────────────────────────────────────────────────────
    storage_backend: StorageBackend = StorageBackend.LOCAL
    local_storage_path: Path = Path("./data/storage")
    max_upload_size_mb: int = 500

    # ── DuckDB ───────────────────────────────────────────────────────
    duckdb_path: Path = Path("./data/analytics.duckdb")

    # ── GCP (optional) ───────────────────────────────────────────────
    gcp_project_id: Optional[str] = None
    gcp_region: Optional[str] = None
    gcs_bucket: Optional[str] = None
    bigquery_dataset: Optional[str] = None

    # ── LLM (optional) ──────────────────────────────────────────────
    llm_provider: Optional[str] = None
    llm_model_path: Optional[str] = None

    # ── Derived properties ───────────────────────────────────────────
    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == Environment.PRODUCTION

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            msg = f"log_level must be one of {allowed}, got '{v}'"
            raise ValueError(msg)
        return upper


def get_settings() -> Settings:
    """Factory that returns a cached Settings instance."""
    return Settings()
