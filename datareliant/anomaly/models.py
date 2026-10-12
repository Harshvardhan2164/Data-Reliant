"""Data models for the Statistical Anomaly and Distribution Shift Engine."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from datareliant.common.types import Severity


class AnomalyResult(BaseModel):
    """Standardized output produced by any anomaly detector."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    detector: str
    dataset_name: str | None = None
    node_id: str | None = None
    metric: str
    baseline: float | None = None
    observed: float
    anomaly_score: float
    threshold: float | None = None
    severity: Severity = Severity.MEDIUM
    is_anomaly: bool = True
    evidence: dict[str, Any] = Field(default_factory=dict)
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return self.model_dump(mode="json")


class DistributionShiftResult(BaseModel):
    """Result of distribution drift analysis between baseline and current data."""

    dataset_name: str | None = None
    metric: str
    method: str  # "ks_test", "jensen_shannon", "psi"
    statistic: float
    p_value: float | None = None
    threshold: float
    is_shift: bool
    severity: Severity = Severity.MEDIUM
    evidence: dict[str, Any] = Field(default_factory=dict)
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return self.model_dump(mode="json")
