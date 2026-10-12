"""Historical Incident Similarity Engine: Structured feature vector extraction and distance-based similarity matching."""

from __future__ import annotations

from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from datareliant.common.models import HistoricalIncidentModel
from datareliant.common.types import RootCauseType, Severity
from datareliant.incidents.models import Incident


def extract_incident_features(incident: Incident) -> dict[str, float]:
    """Convert an incident into a fixed-dimensional structured numerical feature vector."""
    sev_map = {
        Severity.INFO: 0.0,
        Severity.LOW: 1.0,
        Severity.MEDIUM: 2.0,
        Severity.HIGH: 3.0,
        Severity.CRITICAL: 4.0,
    }

    metrics_lower = [a.metric.lower() for a in incident.anomalies]
    dets_lower = [a.detector.lower() for a in incident.anomalies]

    has_null = float(any("null" in m for m in metrics_lower))
    has_dup = float(any("duplicate" in m or "dup" in m for m in metrics_lower))
    has_rows = float(any("row_count" in m or "missing" in m for m in metrics_lower))
    has_schema = float(any("schema" in m or "drift" in m for m in metrics_lower))
    has_shift = float(any("shift" in m or "ks" in d or "psi" in d for m, d in zip(metrics_lower, dets_lower, strict=False)))
    has_temporal = float(any("freshness" in m or "timestamp" in m for m in metrics_lower))

    max_score = max([a.anomaly_score for a in incident.anomalies], default=0.0)

    return {
        "anomaly_count": float(len(incident.anomalies)),
        "affected_nodes_count": float(len(incident.affected_nodes)),
        "severity": sev_map.get(incident.severity, 2.0),
        "has_null": has_null,
        "has_dup": has_dup,
        "has_rows": has_rows,
        "has_schema": has_schema,
        "has_shift": has_shift,
        "has_temporal": has_temporal,
        "max_score": float(max_score),
    }


def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Compute normalized cosine similarity in [0, 1]."""
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 < 1e-9 or norm2 < 1e-9:
        return 0.0
    dot = np.dot(vec1, vec2)
    cos = dot / (norm1 * norm2)
    return float(max(0.0, min(1.0, (cos + 1.0) / 2.0)))  # rescale [-1, 1] to [0, 1]


class IncidentSimilarityEngine:
    """Retrieves historically similar incidents using vector distance metrics without requiring an LLM."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session

    def match_against_archive(
        self,
        current_incident: Incident,
        historical_records: list[dict[str, Any]],
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """Compare current incident with in-memory historical incident records."""
        curr_feat = extract_incident_features(current_incident)
        curr_keys = sorted(curr_feat.keys())
        curr_vec = np.array([curr_feat[k] for k in curr_keys], dtype=float)

        scored_matches = []
        for rec in historical_records:
            h_feat = rec.get("feature_vector", {})
            h_vec = np.array([h_feat.get(k, 0.0) for k in curr_keys], dtype=float)
            sim = _cosine_similarity(curr_vec, h_vec)

            scored_matches.append(
                {
                    "incident_id": rec.get("original_incident_id", rec.get("id", "past_001")),
                    "similarity": round(sim, 4),
                    "root_cause_type": rec.get("root_cause_type", "TRANSFORMATION_ERROR"),
                    "severity": rec.get("severity", "MEDIUM"),
                    "evidence_summary": rec.get("evidence_summary", {}),
                }
            )

        scored_matches.sort(key=lambda x: x["similarity"], reverse=True)
        return scored_matches[:top_k]

    async def find_similar_incidents(
        self,
        current_incident: Incident,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """Query database for stored historical incidents and return top-K most similar."""
        if self.session is None:
            return []

        stmt = select(HistoricalIncidentModel).order_by(HistoricalIncidentModel.created_at.desc()).limit(100)
        res = await self.session.execute(stmt)
        models = res.scalars().all()

        records = [
            {
                "original_incident_id": m.original_incident_id,
                "feature_vector": m.feature_vector,
                "root_cause_type": m.root_cause_type,
                "severity": m.severity,
                "evidence_summary": m.evidence_summary,
            }
            for m in models
        ]
        return self.match_against_archive(current_incident, records, top_k=top_k)

    async def archive_incident(
        self,
        incident: Incident,
        root_cause: RootCauseType,
    ) -> HistoricalIncidentModel | None:
        """Archive a resolved incident with its feature vector for future similarity queries."""
        if self.session is None:
            return None

        feat = extract_incident_features(incident)
        model = HistoricalIncidentModel(
            original_incident_id=incident.id,
            feature_vector=feat,
            root_cause_type=root_cause.value,
            severity=incident.severity.value,
            affected_nodes=incident.affected_nodes,
            evidence_summary={"anomaly_count": len(incident.anomalies)},
        )
        self.session.add(model)
        await self.session.flush()
        return model
