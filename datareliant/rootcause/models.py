"""Data models for Root Cause Analysis and Explainable Evidence Scoring."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field

from datareliant.common.types import Evidence, EvidenceCategory, RootCauseType


class RootCauseCandidate(BaseModel):
    """Ranked root cause candidate with explainable evidence breakdown."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    root_cause_type: RootCauseType
    rank: int = 1
    confidence: float = Field(ge=0.0, le=1.0)
    total_score: float = 0.0
    evidence_items: list[Evidence] = Field(default_factory=list)
    evidence_breakdown: dict[str, float] = Field(default_factory=dict)
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return self.model_dump(mode="json")
