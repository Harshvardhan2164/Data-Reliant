"""Evaluation benchmark models and metric summaries."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class EvaluationBenchmarkResult(BaseModel):
    """Result of running benchmark on a single failure scenario."""

    scenario_id: str
    scenario_type: str
    true_root_cause: str
    predicted_top_1: str
    predicted_top_3: list[str] = Field(default_factory=list)
    top_1_correct: bool
    top_3_correct: bool
    detected: bool
    anomaly_count: int
    compressed_incident_count: int
    compression_ratio: float
    time_to_detect_ms: float
    evidence: dict[str, Any] = Field(default_factory=dict)


class BenchmarkSummary(BaseModel):
    """Comprehensive benchmark metrics across all evaluated scenarios."""

    benchmark_name: str = "datareliant_research_benchmark"
    total_scenarios: int
    detection_recall: float
    top_1_accuracy: float
    top_3_accuracy: float
    mean_compression_ratio: float
    mean_time_to_detect_ms: float
    results: list[EvaluationBenchmarkResult] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return self.model_dump(mode="json")
