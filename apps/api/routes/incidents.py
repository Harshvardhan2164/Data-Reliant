"""Incident investigation and Root-Cause Analysis REST API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from datareliant.anomaly.models import AnomalyResult
from datareliant.common.database import get_db_session
from datareliant.incidents.service import IncidentService
from datareliant.lineage.service import LineageService

router = APIRouter()


class CorrelationRequest(BaseModel):
    anomalies: list[AnomalyResult]
    pipeline_id: str | None = None


@router.get("/incidents", summary="List correlated incidents")
async def list_incidents(
    limit: int = 50,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Return all correlated incidents with top root-cause candidates."""
    service = IncidentService(session)
    incidents = await service.list_incidents(limit=limit)
    return {"incidents": incidents, "total": len(incidents)}


@router.get("/incidents/{incident_id}", summary="Get incident details")
async def get_incident(
    incident_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Return complete incident details including anomaly IDs and candidate causes."""
    service = IncidentService(session)
    return await service.get_incident(incident_id)


@router.get("/incidents/{incident_id}/root-cause", summary="Get root-cause analysis with evidence")
async def get_incident_root_cause(
    incident_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Return ranked root-cause candidates and explainable evidence breakdown for an incident."""
    service = IncidentService(session)
    inc = await service.get_incident(incident_id)
    return {
        "incident_id": incident_id,
        "title": inc["title"],
        "severity": inc["severity"],
        "candidate_causes": inc["candidate_causes"],
    }


@router.post("/incidents/correlate", summary="Correlate anomalies into incidents")
async def correlate_anomalies(
    req: CorrelationRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Correlate a batch of anomalies, rank root causes, and persist resulting incidents."""
    lineage_graph = None
    if req.pipeline_id:
        lineage_service = LineageService(session)
        try:
            lineage_graph = await lineage_service.get_pipeline_graph(req.pipeline_id)
        except Exception:
            pass

    service = IncidentService(session)
    incidents = await service.correlate_and_analyze(
        anomalies=req.anomalies,
        lineage_graph=lineage_graph,
        pipeline_id=req.pipeline_id,
    )
    return {
        "status": "success",
        "incidents_created": len(incidents),
        "incidents": [i.to_dict() for i in incidents],
    }
