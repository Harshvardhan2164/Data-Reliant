"""Shared domain types and enumerations used across DataReliant.

These Pydantic models and enums provide a consistent vocabulary for
severity levels, statuses, evidence categories, and other concepts
referenced by multiple subsystems.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ── Enumerations ─────────────────────────────────────────────────────


class Severity(str, Enum):
    """Severity level for quality failures, anomalies, and incidents."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Status(str, Enum):
    """Execution or lifecycle status."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNING = "WARNING"
    ERROR = "ERROR"
    COMPLETED = "COMPLETED"


class IncidentStatus(str, Enum):
    """Incident lifecycle status."""

    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class SchemaChangeType(str, Enum):
    """Classification of a schema change."""

    NON_BREAKING = "NON_BREAKING"
    WARNING = "WARNING"
    BREAKING = "BREAKING"


class NodeType(str, Enum):
    """Pipeline lineage node type."""

    SOURCE = "source"
    PIPELINE = "pipeline"
    JOB = "job"
    DATASET = "dataset"
    TABLE = "table"
    MODEL = "model"
    DASHBOARD = "dashboard"


class RootCauseType(str, Enum):
    """Known root-cause categories."""

    UPSTREAM_FAILURE = "UPSTREAM_FAILURE"
    MISSING_DATA = "MISSING_DATA"
    DUPLICATE_INGESTION = "DUPLICATE_INGESTION"
    SCHEMA_DRIFT = "SCHEMA_DRIFT"
    TYPE_CHANGE = "TYPE_CHANGE"
    NULL_SPIKE = "NULL_SPIKE"
    DISTRIBUTION_SHIFT = "DISTRIBUTION_SHIFT"
    LATE_ARRIVAL = "LATE_ARRIVAL"
    TIMEZONE_MISMATCH = "TIMEZONE_MISMATCH"
    TRANSFORMATION_ERROR = "TRANSFORMATION_ERROR"
    SOURCE_DATA_CHANGE = "SOURCE_DATA_CHANGE"


class EvidenceCategory(str, Enum):
    """Categories of evidence supporting a root-cause prediction."""

    TEMPORAL = "temporal"
    GRAPH = "graph"
    STATISTICAL = "statistical"
    HISTORICAL = "historical"
    PROPAGATION = "propagation"
    SCHEMA = "schema"


# ── Base Models ──────────────────────────────────────────────────────


class TimestampMixin(BaseModel):
    """Mixin providing created/updated timestamps."""

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class IdentifiableMixin(BaseModel):
    """Mixin providing a UUID identifier."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class Evidence(BaseModel):
    """A single piece of evidence supporting a root-cause prediction."""

    category: EvidenceCategory
    description: str
    score: float = Field(ge=0.0, le=1.0)
    details: dict[str, Any] = Field(default_factory=dict)


class EvidenceBundle(BaseModel):
    """Collection of evidence items with an aggregate confidence score."""

    items: list[Evidence] = Field(default_factory=list)
    total_score: float = Field(ge=0.0, le=1.0, default=0.0)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)

    def add(self, evidence: Evidence) -> None:
        """Add an evidence item and recalculate totals."""
        self.items.append(evidence)
        self._recalculate()

    def _recalculate(self) -> None:
        """Recalculate total score and confidence from items."""
        if not self.items:
            self.total_score = 0.0
            self.confidence = 0.0
            return
        self.total_score = sum(e.score for e in self.items)
        self.confidence = min(1.0, self.total_score / max(len(self.items), 1))
