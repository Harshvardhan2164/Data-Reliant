"""Unit tests for common modules — config, types, exceptions."""

from __future__ import annotations

import pytest

from datareliant.common.config import Environment, Settings, StorageBackend
from datareliant.common.exceptions import (
    DataReliantError,
    DatasetNotFoundError,
    FileTooLargeError,
    IngestionError,
    SchemaValidationError,
)
from datareliant.common.types import (
    Evidence,
    EvidenceBundle,
    EvidenceCategory,
    RootCauseType,
    Severity,
)

# ── Config Tests ─────────────────────────────────────────────────────


class TestSettings:
    """Test configuration loading and validation."""

    def test_default_settings(self):
        """Default settings should be valid for local development."""
        settings = Settings()
        assert settings.app_env == Environment.DEVELOPMENT
        assert settings.debug is True
        assert "datareliant" in settings.database_url

    def test_cors_origin_list(self):
        """CORS origins should be parsed from comma-separated string."""
        settings = Settings(cors_origins="http://localhost:3000,http://localhost:5173")
        origins = settings.cors_origin_list
        assert len(origins) == 2
        assert "http://localhost:3000" in origins

    def test_is_production(self):
        """is_production should be True only in production."""
        dev = Settings(app_env=Environment.DEVELOPMENT)
        assert dev.is_production is False
        prod = Settings(app_env=Environment.PRODUCTION)
        assert prod.is_production is True

    def test_max_upload_bytes(self):
        """max_upload_bytes should convert MB to bytes."""
        settings = Settings(max_upload_size_mb=100)
        assert settings.max_upload_bytes == 100 * 1024 * 1024

    def test_invalid_log_level(self):
        """Invalid log levels should raise ValueError."""
        with pytest.raises(ValueError, match="log_level"):
            Settings(log_level="VERBOSE")

    def test_storage_backend_enum(self):
        """Storage backend should accept valid values."""
        settings = Settings(storage_backend=StorageBackend.LOCAL)
        assert settings.storage_backend == StorageBackend.LOCAL


# ── Exception Tests ──────────────────────────────────────────────────


class TestExceptions:
    """Test domain exceptions."""

    def test_base_error_to_dict(self):
        """Base error should serialize to dict."""
        err = DataReliantError("something broke", details={"key": "val"})
        d = err.to_dict()
        assert d["error_code"] == "INTERNAL_ERROR"
        assert d["message"] == "something broke"
        assert d["details"] == {"key": "val"}

    def test_error_hierarchy(self):
        """Specific errors should be subclasses of DataReliantError."""
        assert issubclass(IngestionError, DataReliantError)
        assert issubclass(FileTooLargeError, IngestionError)
        assert issubclass(SchemaValidationError, IngestionError)
        assert issubclass(DatasetNotFoundError, DataReliantError)

    def test_status_codes(self):
        """Each error type should have the correct HTTP status code."""
        assert DataReliantError().status_code == 500
        assert IngestionError().status_code == 400
        assert FileTooLargeError().status_code == 413
        assert DatasetNotFoundError().status_code == 404

    def test_error_codes(self):
        """Each error type should have a unique error code."""
        codes = {
            DataReliantError().error_code,
            IngestionError().error_code,
            FileTooLargeError().error_code,
            SchemaValidationError().error_code,
            DatasetNotFoundError().error_code,
        }
        assert len(codes) == 5  # all unique


# ── Types Tests ──────────────────────────────────────────────────────


class TestTypes:
    """Test domain types and enums."""

    def test_severity_values(self):
        """All severity levels should be present."""
        levels = {s.value for s in Severity}
        assert levels == {"INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"}

    def test_root_cause_types(self):
        """All root cause types should be present."""
        types = {t.value for t in RootCauseType}
        assert "UPSTREAM_FAILURE" in types
        assert "SCHEMA_DRIFT" in types
        assert len(types) == 11

    def test_evidence_score_bounds(self):
        """Evidence score must be between 0 and 1."""
        e = Evidence(
            category=EvidenceCategory.TEMPORAL,
            description="Time correlation",
            score=0.8,
        )
        assert 0.0 <= e.score <= 1.0

    def test_evidence_bundle(self):
        """Evidence bundle should calculate totals correctly."""
        bundle = EvidenceBundle()
        bundle.add(
            Evidence(
                category=EvidenceCategory.TEMPORAL,
                description="Time match",
                score=0.9,
            )
        )
        bundle.add(
            Evidence(
                category=EvidenceCategory.GRAPH,
                description="Upstream dep",
                score=0.7,
            )
        )
        assert bundle.total_score == pytest.approx(1.6)
        assert bundle.confidence == pytest.approx(0.8)  # 1.6 / 2
        assert len(bundle.items) == 2
