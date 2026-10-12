"""Statistical anomaly and distribution shift API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from datareliant.anomaly.base import DetectorRegistry
from datareliant.anomaly.service import AnomalyService
from datareliant.common.database import get_db_session

router = APIRouter()


class AnomalyDetectionRequest(BaseModel):
    history: list[float]
    current: float
    detector: str = "robust_zscore"
    metric_name: str = "metric"
    dataset_name: str | None = None
    node_id: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    persist: bool = True


class DistributionShiftRequest(BaseModel):
    baseline: list[float]
    observed: list[float]
    method: str = "ks_test"  # "ks_test", "jensen_shannon", "psi"
    metric_name: str = "metric"
    dataset_name: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


@router.post("/anomalies/detect", summary="Run anomaly detector on metric")
async def detect_anomalies(
    req: AnomalyDetectionRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Execute statistical anomaly detection on a single metric point."""
    service = AnomalyService(session)
    result = service.engine.detect(
        history=req.history,
        current=req.current,
        detector=req.detector,
        metric_name=req.metric_name,
        dataset_name=req.dataset_name,
        node_id=req.node_id,
        **req.parameters,
    )
    if req.persist and result.is_anomaly:
        await service.record_anomaly(result)

    return {"status": "success", "result": result.to_dict()}


@router.post("/anomalies/distribution-shift", summary="Detect distribution shift")
async def detect_distribution_shift(
    req: DistributionShiftRequest,
    session: AsyncSession = Depends(get_db_session),  # noqa: ARG001
) -> dict[str, Any]:
    """Execute KS, JSD, or PSI distribution drift analysis."""
    service = AnomalyService(session)
    shift_res = service.engine.detect_distribution_shift(
        baseline=req.baseline,
        observed=req.observed,
        method=req.method,
        metric_name=req.metric_name,
        dataset_name=req.dataset_name,
        **req.parameters,
    )
    return {"status": "success", "result": shift_res.to_dict()}


@router.get("/anomalies", summary="List detected anomalies")
async def list_anomalies(
    dataset_name: str | None = None,
    limit: int = 100,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Return historical anomalies stored in database."""
    service = AnomalyService(session)
    anomalies = await service.list_anomalies(dataset_name=dataset_name, limit=limit)
    return {"anomalies": anomalies, "total": len(anomalies)}


@router.get("/anomalies/detectors", summary="List available anomaly detectors")
async def list_available_detectors() -> dict[str, Any]:
    """Return all registered anomaly detector algorithms."""
    return {"detectors": DetectorRegistry.available_detectors()}
