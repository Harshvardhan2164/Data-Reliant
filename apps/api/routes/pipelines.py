"""Pipeline topology, lineage graph, and blast-radius REST API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from datareliant.common.database import get_db_session
from datareliant.lineage.models import PipelineMetadata
from datareliant.lineage.service import LineageService

router = APIRouter()


@router.get("/pipelines", summary="List all registered pipelines")
async def list_pipelines(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Return all known data pipelines."""
    service = LineageService(session)
    pipelines = await service.list_pipelines()
    return {"pipelines": pipelines, "total": len(pipelines)}


@router.post("/pipelines/register", summary="Register a pipeline topology")
async def register_pipeline(
    pipeline: PipelineMetadata,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Register pipeline metadata and build its lineage graph."""
    service = LineageService(session)
    graph = await service.register_pipeline(pipeline)
    return {
        "status": "success",
        "pipeline_id": pipeline.id,
        "nodes_count": graph.graph.number_of_nodes(),
        "edges_count": graph.graph.number_of_edges(),
    }


@router.get("/pipelines/{pipeline_id}/lineage", summary="Get lineage graph for visualization")
async def get_pipeline_lineage(
    pipeline_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Return D3-ready nodes and edges for interactive visualization."""
    service = LineageService(session)
    graph = await service.get_pipeline_graph(pipeline_id)
    return {"status": "success", "lineage": graph.to_d3_dict()}


@router.get("/pipelines/{pipeline_id}/blast-radius/{node_id}", summary="Compute blast radius impact")
async def get_blast_radius(
    pipeline_id: str,
    node_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Compute downstream impact, affected dashboards/models, and blast-radius score."""
    service = LineageService(session)
    report = await service.get_blast_radius(pipeline_id, node_id)
    return {"status": "success", "report": report.to_dict()}
