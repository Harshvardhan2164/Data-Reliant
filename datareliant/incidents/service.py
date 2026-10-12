"""Incident service managing correlation runs, root-cause enrichment, and persistence."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from datareliant.anomaly.models import AnomalyResult
from datareliant.common.exceptions import IncidentNotFoundError
from datareliant.common.models import (
    IncidentAnomalyModel,
    IncidentModel,
    RootCauseCandidateModel,
)
from datareliant.incidents.correlator import IncidentCorrelator
from datareliant.incidents.models import Incident
from datareliant.incidents.similarity import IncidentSimilarityEngine
from datareliant.lineage.graph import LineageGraph
from datareliant.rootcause.engine import RootCauseEngine


class IncidentService:
    """Orchestrates incident correlation, similarity retrieval, root-cause ranking, and persistence."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session
        self.correlator = IncidentCorrelator()
        self.root_cause_engine = RootCauseEngine()
        self.similarity_engine = IncidentSimilarityEngine(session)

    async def correlate_and_analyze(
        self,
        anomalies: list[AnomalyResult],
        lineage_graph: LineageGraph | None = None,
        pipeline_id: str | None = None,
    ) -> list[Incident]:
        """Group anomalies into incidents, retrieve historical matches, rank root causes, and persist."""
        incidents = self.correlator.correlate(
            anomalies=anomalies,
            lineage_graph=lineage_graph,
            pipeline_id=pipeline_id,
        )

        for inc in incidents:
            # 1. Retrieve similar historical incidents
            history_matches = await self.similarity_engine.find_similar_incidents(inc, top_k=3)
            # 2. Run Root Cause Engine
            candidates = self.root_cause_engine.analyze_incident(
                incident=inc,
                lineage_graph=lineage_graph,
                historical_matches=history_matches,
            )
            inc.candidate_causes = candidates

            # 3. Persist to database if session exists
            if self.session is not None:
                inc_model = IncidentModel(
                    id=inc.id,
                    title=inc.title,
                    severity=inc.severity,
                    status=inc.status,
                    start_time=inc.start_time,
                    end_time=inc.end_time,
                    affected_nodes=inc.affected_nodes,
                    metadata_={"pipeline_id": pipeline_id, "anomaly_count": len(inc.anomalies)},
                )
                self.session.add(inc_model)

                # Link anomalies
                for aid in inc.anomaly_ids:
                    link = IncidentAnomalyModel(
                        incident_id=inc.id,
                        anomaly_id=aid,
                    )
                    self.session.add(link)

                # Save root cause candidates
                for cand in candidates:
                    cand_model = RootCauseCandidateModel(
                        id=cand.id,
                        incident_id=inc.id,
                        root_cause_type=cand.root_cause_type,
                        rank=cand.rank,
                        confidence=cand.confidence,
                        total_score=cand.total_score,
                        evidence=cand.evidence_breakdown,
                        explanation=cand.explanation,
                    )
                    self.session.add(cand_model)

                await self.session.flush()

        return incidents

    async def list_incidents(self, limit: int = 50) -> list[dict[str, Any]]:
        """Query recent incidents with candidate summaries."""
        if self.session is None:
            return []

        stmt = (
            select(IncidentModel)
            .options(
                selectinload(IncidentModel.rootcause_candidates),
                selectinload(IncidentModel.anomaly_links),
            )
            .order_by(IncidentModel.created_at.desc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        models = res.scalars().all()

        results = []
        for m in models:
            top_cause = m.rootcause_candidates[0] if m.rootcause_candidates else None
            results.append(
                {
                    "id": m.id,
                    "title": m.title,
                    "severity": m.severity.value
                    if hasattr(m.severity, "value")
                    else str(m.severity),
                    "status": m.status.value if hasattr(m.status, "value") else str(m.status),
                    "start_time": m.start_time.isoformat(),
                    "end_time": m.end_time.isoformat() if m.end_time else None,
                    "affected_nodes": m.affected_nodes,
                    "anomaly_count": len(m.anomaly_links),
                    "top_root_cause": (
                        {
                            "type": top_cause.root_cause_type.value,
                            "confidence": top_cause.confidence,
                        }
                        if top_cause
                        else None
                    ),
                    "created_at": m.created_at.isoformat(),
                }
            )
        return results

    async def get_incident(self, incident_id: str) -> dict[str, Any]:
        """Fetch full details for an incident."""
        if self.session is None:
            raise IncidentNotFoundError("Database session required")

        stmt = (
            select(IncidentModel)
            .where(IncidentModel.id == incident_id)
            .options(
                selectinload(IncidentModel.rootcause_candidates),
                selectinload(IncidentModel.anomaly_links),
            )
        )
        res = await self.session.execute(stmt)
        m = res.scalar_one_or_none()
        if m is None:
            raise IncidentNotFoundError(f"Incident with ID '{incident_id}' not found")

        candidates = [
            {
                "id": c.id,
                "type": c.root_cause_type.value,
                "rank": c.rank,
                "confidence": c.confidence,
                "total_score": c.total_score,
                "evidence": c.evidence,
                "explanation": c.explanation,
            }
            for c in m.rootcause_candidates
        ]

        return {
            "id": m.id,
            "title": m.title,
            "severity": m.severity.value if hasattr(m.severity, "value") else str(m.severity),
            "status": m.status.value if hasattr(m.status, "value") else str(m.status),
            "start_time": m.start_time.isoformat(),
            "end_time": m.end_time.isoformat() if m.end_time else None,
            "affected_nodes": m.affected_nodes,
            "anomaly_ids": [link.anomaly_id for link in m.anomaly_links],
            "candidate_causes": candidates,
            "metadata": m.metadata_,
            "created_at": m.created_at.isoformat(),
        }
