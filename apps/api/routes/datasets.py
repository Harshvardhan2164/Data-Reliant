"""Dataset management and profiling endpoints."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from datareliant.common.database import get_db_session
from datareliant.common.exceptions import IngestionError
from datareliant.ingestion.service import IngestionService
from datareliant.profiling.service import ProfilingService

router = APIRouter()


class DatasetRegistrationRequest(BaseModel):
    name: str
    file_path: str
    description: str | None = None
    version: int | None = None


@router.post("/datasets/upload", summary="Upload and ingest a dataset file")
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str | None = Form(None),
    version: int | None = Form(None),
    auto_profile: bool = Form(True),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Upload a CSV or Parquet file, register it, and optionally profile it."""
    # Save upload to temporary file
    temp_dir = Path(tempfile.mkdtemp(prefix="datareliant_upload_"))
    try:
        temp_file = temp_dir / (file.filename or "uploaded_data")
        with open(temp_file, "wb") as f:
            shutil.copyfileobj(file.file, f)

        ingestion = IngestionService(session)
        dataset, ver, df = await ingestion.ingest_file(
            file_path=temp_file,
            dataset_name=name,
            description=description,
            version=version,
        )

        profile_data = None
        if auto_profile:
            profiler = ProfilingService(session)
            profile = await profiler.profile_dataset_version(
                dataset_id=dataset.id,
                version=ver.version,
            )
            profile_data = profile.to_dict()

        return {
            "status": "success",
            "dataset": {
                "id": dataset.id,
                "name": dataset.name,
                "source_type": dataset.source_type,
                "version": ver.version,
                "row_count": ver.row_count,
                "column_count": ver.column_count,
                "file_hash": ver.file_hash,
                "schema": ver.schema_snapshot,
            },
            "profile": profile_data,
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.post("/datasets/register", summary="Register an existing dataset file")
async def register_dataset(
    req: DatasetRegistrationRequest,
    auto_profile: bool = True,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Register a dataset file already present on disk."""
    ingestion = IngestionService(session)
    dataset, ver, _ = await ingestion.ingest_file(
        file_path=req.file_path,
        dataset_name=req.name,
        description=req.description,
        version=req.version,
    )

    profile_data = None
    if auto_profile:
        profiler = ProfilingService(session)
        profile = await profiler.profile_dataset_version(
            dataset_id=dataset.id,
            version=ver.version,
        )
        profile_data = profile.to_dict()

    return {
        "status": "success",
        "dataset": {
            "id": dataset.id,
            "name": dataset.name,
            "version": ver.version,
            "row_count": ver.row_count,
            "column_count": ver.column_count,
            "file_hash": ver.file_hash,
        },
        "profile": profile_data,
    }


@router.get("/datasets", summary="List all registered datasets")
async def list_datasets(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Return all registered datasets with version summary."""
    ingestion = IngestionService(session)
    datasets = await ingestion.list_datasets()
    result = []
    for d in datasets:
        result.append(
            {
                "id": d.id,
                "name": d.name,
                "description": d.description,
                "source_type": d.source_type,
                "version_count": len(d.versions),
                "versions": [
                    {
                        "version": v.version,
                        "row_count": v.row_count,
                        "column_count": v.column_count,
                        "created_at": v.created_at.isoformat(),
                    }
                    for v in d.versions
                ],
                "created_at": d.created_at.isoformat(),
            }
        )
    return {"datasets": result, "total": len(result)}


@router.get("/datasets/{dataset_id}", summary="Get dataset details")
async def get_dataset(
    dataset_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Return details and version history for a specific dataset."""
    ingestion = IngestionService(session)
    dataset = await ingestion.get_dataset(dataset_id)
    return {
        "id": dataset.id,
        "name": dataset.name,
        "description": dataset.description,
        "source_type": dataset.source_type,
        "metadata": dataset.metadata_,
        "versions": [
            {
                "id": v.id,
                "version": v.version,
                "row_count": v.row_count,
                "column_count": v.column_count,
                "file_path": v.file_path,
                "file_hash": v.file_hash,
                "schema": v.schema_snapshot,
                "created_at": v.created_at.isoformat(),
            }
            for v in dataset.versions
        ],
        "created_at": dataset.created_at.isoformat(),
    }


@router.get("/datasets/{dataset_id}/profile", summary="Get dataset profile")
async def get_dataset_profile(
    dataset_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Return the latest profile for a dataset."""
    profiler = ProfilingService(session)
    profile = await profiler.get_latest_profile(dataset_id)
    if profile is None:
        return {"status": "not_profiled", "dataset_id": dataset_id, "profile": None}
    return {"status": "success", "dataset_id": dataset_id, "profile": profile}


@router.post("/datasets/{dataset_id}/profile", summary="Generate profile for dataset")
async def generate_dataset_profile(
    dataset_id: str,
    version: int | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Trigger profiling computation for a dataset version."""
    profiler = ProfilingService(session)
    profile = await profiler.profile_dataset_version(dataset_id=dataset_id, version=version)
    return {
        "status": "success",
        "dataset_id": dataset_id,
        "version": profile.version,
        "profile": profile.to_dict(),
    }


@router.get("/datasets/{dataset_id}/schema-diff", summary="Get schema drift between two versions")
async def get_schema_diff(
    dataset_id: str,
    base_version: int = 1,
    target_version: int = 2,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Compare schemas of two dataset versions and classify breaking changes."""
    from datareliant.profiling.schema_drift import SchemaDriftEngine

    ingestion = IngestionService(session)
    dataset = await ingestion.get_dataset(dataset_id)

    v_map = {v.version: v for v in dataset.versions}
    if base_version not in v_map:
        raise IngestionError(f"Base version {base_version} not found for dataset {dataset.name}")
    if target_version not in v_map:
        raise IngestionError(f"Target version {target_version} not found for dataset {dataset.name}")

    engine = SchemaDriftEngine()
    diff = engine.compare_schemas(
        base_schema=v_map[base_version].schema_snapshot,
        target_schema=v_map[target_version].schema_snapshot,
        dataset_name=dataset.name,
        base_version=base_version,
        target_version=target_version,
    )
    return {"status": "success", "diff": diff.to_dict()}
