"""Structured domain exceptions for DataReliant.

Every public exception carries a machine-readable ``error_code`` so that
API error responses are consistent and clients can programmatically react.
Raw stack traces are never exposed through the production API.
"""

from __future__ import annotations

from typing import Any


class DataReliantError(Exception):
    """Base exception for all DataReliant domain errors."""

    error_code: str = "INTERNAL_ERROR"
    status_code: int = 500

    def __init__(
        self,
        message: str = "An internal error occurred.",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dictionary."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


# ── Ingestion ────────────────────────────────────────────────────────


class IngestionError(DataReliantError):
    """Raised when data ingestion fails."""

    error_code = "INGESTION_ERROR"
    status_code = 400


class UnsupportedFormatError(IngestionError):
    """Raised when the uploaded file format is not supported."""

    error_code = "UNSUPPORTED_FORMAT"


class FileTooLargeError(IngestionError):
    """Raised when the uploaded file exceeds the size limit."""

    error_code = "FILE_TOO_LARGE"
    status_code = 413


class SchemaValidationError(IngestionError):
    """Raised when the dataset schema fails validation."""

    error_code = "DATASET_SCHEMA_INVALID"


# ── Dataset ──────────────────────────────────────────────────────────


class DatasetNotFoundError(DataReliantError):
    """Raised when a requested dataset does not exist."""

    error_code = "DATASET_NOT_FOUND"
    status_code = 404


class DatasetVersionConflictError(DataReliantError):
    """Raised when a dataset version already exists."""

    error_code = "DATASET_VERSION_CONFLICT"
    status_code = 409


# ── Profiling ────────────────────────────────────────────────────────


class ProfilingError(DataReliantError):
    """Raised when profiling fails."""

    error_code = "PROFILING_ERROR"


# ── Quality ──────────────────────────────────────────────────────────


class QualityRuleError(DataReliantError):
    """Raised when a quality rule configuration is invalid."""

    error_code = "QUALITY_RULE_INVALID"
    status_code = 400


class QualityRunNotFoundError(DataReliantError):
    """Raised when a quality run does not exist."""

    error_code = "QUALITY_RUN_NOT_FOUND"
    status_code = 404


# ── Anomaly ──────────────────────────────────────────────────────────


class AnomalyDetectionError(DataReliantError):
    """Raised when anomaly detection fails."""

    error_code = "ANOMALY_DETECTION_ERROR"


class DetectorNotFoundError(DataReliantError):
    """Raised when a requested detector type is not registered."""

    error_code = "DETECTOR_NOT_FOUND"
    status_code = 404


# ── Pipeline / Lineage ───────────────────────────────────────────────


class PipelineNotFoundError(DataReliantError):
    """Raised when a pipeline definition is not found."""

    error_code = "PIPELINE_NOT_FOUND"
    status_code = 404


class LineageError(DataReliantError):
    """Raised when a lineage query fails."""

    error_code = "LINEAGE_ERROR"


# ── Incidents ────────────────────────────────────────────────────────


class IncidentNotFoundError(DataReliantError):
    """Raised when an incident is not found."""

    error_code = "INCIDENT_NOT_FOUND"
    status_code = 404


# ── Root Cause ───────────────────────────────────────────────────────


class RootCauseError(DataReliantError):
    """Raised when root-cause analysis fails."""

    error_code = "ROOT_CAUSE_ERROR"


# ── Evaluation ───────────────────────────────────────────────────────


class EvaluationError(DataReliantError):
    """Raised when the evaluation framework encounters an error."""

    error_code = "EVALUATION_ERROR"


class ScenarioNotFoundError(EvaluationError):
    """Raised when a test scenario is not found."""

    error_code = "SCENARIO_NOT_FOUND"
    status_code = 404


# ── Configuration ────────────────────────────────────────────────────


class ConfigurationError(DataReliantError):
    """Raised when configuration is invalid or missing."""

    error_code = "CONFIGURATION_ERROR"
    status_code = 500
