"""Quality monitoring and rule execution API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from datareliant.common.database import get_db_session
from datareliant.quality.base import RuleRegistry
from datareliant.quality.models import QualitySuiteConfig
from datareliant.quality.service import QualityService

router = APIRouter()


class QualityRunRequest(BaseModel):
    dataset_id: str
    version: int | None = None
    suite: QualitySuiteConfig | None = None


@router.post("/quality/runs", summary="Execute data quality checks")
async def create_quality_run(
    req: QualityRunRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Execute quality rules on a dataset version and return results."""
    service = QualityService(session)
    summary = await service.execute_quality_run(
        dataset_id=req.dataset_id,
        version=req.version,
        suite=req.suite,
    )
    return {
        "status": "success",
        "run_id": summary.run_id,
        "dataset": summary.dataset,
        "version": summary.version,
        "overall_status": summary.overall_status.value,
        "total_rules": summary.total_rules,
        "passed_rules": summary.passed_rules,
        "failed_rules": summary.failed_rules,
        "error_rules": summary.error_rules,
        "critical_failures": summary.critical_failures,
        "high_failures": summary.high_failures,
        "duration_ms": summary.total_duration_ms,
        "results": [r.to_dict() for r in summary.results],
    }


@router.get("/quality/runs/{run_id}", summary="Get quality run results")
async def get_quality_run(
    run_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Return results for a completed quality check run."""
    service = QualityService(session)
    return await service.get_run_results(run_id)


@router.get("/quality/rules/available", summary="List available quality rule types")
async def list_available_rules() -> dict[str, Any]:
    """List all registered rule types in the plugin registry."""
    return {"available_rules": RuleRegistry.available_rules()}
