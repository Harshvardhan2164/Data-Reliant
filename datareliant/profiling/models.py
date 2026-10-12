"""Data models and schemas for the Data Profiling Engine."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class DatasetStats(BaseModel):
    """Dataset-level statistical profile."""

    row_count: int
    column_count: int
    memory_estimate_bytes: int
    duplicate_row_count: int
    duplicate_row_percentage: float
    dataset_hash: str | None = None
    temporal_coverage: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class ColumnStats(BaseModel):
    """Column-level statistical profile."""

    name: str
    datatype: str
    null_count: int
    null_percentage: float
    unique_count: int
    uniqueness_percentage: float
    min_value: Any | None = None
    max_value: Any | None = None
    mean: float | None = None
    median: float | None = None
    std_dev: float | None = None
    quantiles: dict[str, float] = Field(
        default_factory=dict
    )  # e.g., "p25", "p50", "p75", "p90", "p99"
    categorical_frequencies: list[dict[str, Any]] = Field(
        default_factory=list
    )  # top value frequencies
    approximate_cardinality: int | None = None


class TemporalStats(BaseModel):
    """Profiling metrics for a datetime or temporal column."""

    column_name: str
    min_timestamp: str | None = None
    max_timestamp: str | None = None
    inferred_frequency: str | None = None  # e.g. "1D", "1h", "mixed"
    gaps_count: int = 0
    freshness_seconds: float | None = None
    timezone_metadata: str | None = None


class DataProfile(BaseModel):
    """Complete profile snapshot for a dataset version."""

    dataset_name: str
    version: int
    dataset_stats: DatasetStats
    column_stats: dict[str, ColumnStats]
    temporal_stats: dict[str, TemporalStats]
    profiled_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return self.model_dump(mode="json")
