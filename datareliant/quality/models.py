"""Data models and schemas for the Quality Rule Engine."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from datareliant.common.types import Severity, Status


class QualityRuleConfig(BaseModel):
    """Configuration for an individual data quality rule."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: str  # e.g. "not_null", "uniqueness", "range", etc.
    dataset: str = ""
    column: str | None = None
    severity: Severity = Severity.MEDIUM
    parameters: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    description: str | None = None


class QualitySuiteConfig(BaseModel):
    """A suite of quality rules, typically loaded from YAML or JSON."""

    name: str = "default_suite"
    description: str | None = None
    rules: list[QualityRuleConfig] = Field(default_factory=list)


class QualityResult(BaseModel):
    """Standardized output produced by every quality check execution."""

    rule_id: str
    rule_name: str
    rule_type: str
    dataset: str
    column: str | None = None
    execution_time_ms: float
    status: Status  # PASSED, FAILED, ERROR
    severity: Severity
    expected: str | None = None
    actual: str | None = None
    failure_percentage: float = 0.0
    failure_count: int = 0
    total_evaluated: int = 0
    evidence: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    executed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dictionary."""
        return self.model_dump(mode="json")


class QualityRunSummary(BaseModel):
    """Aggregate report for a quality run."""

    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    dataset: str
    version: int
    total_rules: int
    passed_rules: int
    failed_rules: int
    error_rules: int
    critical_failures: int
    high_failures: int
    total_duration_ms: float
    results: list[QualityResult] = Field(default_factory=list)
    executed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def has_critical_failure(self) -> bool:
        return self.critical_failures > 0

    @property
    def overall_status(self) -> Status:
        if self.critical_failures > 0 or self.failed_rules > 0:
            return Status.FAILED
        if self.error_rules > 0:
            return Status.ERROR
        return Status.PASSED
