"""Anomaly detection service managing detection execution and database persistence."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from datareliant.anomaly.engine import AnomalyEngine
from datareliant.anomaly.models import AnomalyResult
from datareliant.common.models import AnomalyModel


class AnomalyService:
    """Orchestrates anomaly runs and persists findings."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session
        self.engine = AnomalyEngine()

    async def record_anomaly(self, result: AnomalyResult) -> AnomalyModel | None:
        """Persist an anomaly result to the database."""
        if self.session is None or not result.is_anomaly:
            return None

        model = AnomalyModel(
            id=result.id,
            detector=result.detector,
            dataset_name=result.dataset_name,
            node_id=result.node_id,
            metric=result.metric,
            baseline=result.baseline,
            observed=result.observed,
            anomaly_score=result.anomaly_score,
            threshold=result.threshold,
            severity=result.severity,
            evidence=result.evidence,
            detected_at=result.detected_at,
        )
        self.session.add(model)
        await self.session.flush()
        return model

    async def list_anomalies(
        self,
        dataset_name: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query detected anomalies from database."""
        if self.session is None:
            return []

        stmt = select(AnomalyModel).order_by(AnomalyModel.detected_at.desc()).limit(limit)
        if dataset_name:
            stmt = stmt.where(AnomalyModel.dataset_name == dataset_name)

        res = await self.session.execute(stmt)
        models = res.scalars().all()
        return [
            {
                "id": m.id,
                "detector": m.detector,
                "dataset_name": m.dataset_name,
                "node_id": m.node_id,
                "metric": m.metric,
                "baseline": m.baseline,
                "observed": m.observed,
                "anomaly_score": m.anomaly_score,
                "threshold": m.threshold,
                "severity": m.severity.value if hasattr(m.severity, "value") else str(m.severity),
                "evidence": m.evidence,
                "detected_at": m.detected_at.isoformat(),
            }
            for m in models
        ]
