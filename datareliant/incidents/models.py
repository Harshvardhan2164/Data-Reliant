from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from datareliant.anomaly.models import AnomalyResult
from datareliant.common.types import IncidentStatus, Severity
from datareliant.rootcause.models import RootCauseCandidate


class Incident(BaseModel):
    """Correlated cluster of anomalies representing a systemic failure or data issue."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    severity: Severity = Severity.MEDIUM
    status: IncidentStatus = IncidentStatus.OPEN
    start_time: datetime
    end_time: datetime | None = None
    pipeline_id: str | None = None
    affected_nodes: list[str] = Field(default_factory=list)
    anomaly_ids: list[str] = Field(default_factory=list)
    anomalies: list[AnomalyResult] = Field(default_factory=list)
    candidate_causes: list[RootCauseCandidate] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def anomaly_count(self) -> int:
        return len(self.anomaly_ids)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return self.model_dump(mode="json")
