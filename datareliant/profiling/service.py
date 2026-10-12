"""Service orchestrating dataset profiling and profile persistence."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from datareliant.common.exceptions import DatasetNotFoundError, ProfilingError
from datareliant.common.models import DatasetVersionModel, ProfileModel
from datareliant.ingestion.service import IngestionService
from datareliant.profiling.models import DataProfile
from datareliant.profiling.profiler import DataProfiler


class ProfilingService:
    """Manages profile computation and persistence."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session
        self.profiler = DataProfiler()
        self.ingestion_service = IngestionService(session)

    async def profile_dataset_version(
        self,
        dataset_id: str,
        version: int | None = None,
    ) -> DataProfile:
        """Compute and persist profile for a specific dataset version."""
        if self.session is None:
            raise ProfilingError("Database session required to profile dataset version")

        # Load dataset metadata
        dataset = await self.ingestion_service.get_dataset(dataset_id)
        ver_model, df = await self.ingestion_service.load_version_dataframe(
            dataset_id, version=version
        )

        profile = self.profiler.profile(
            df=df,
            dataset_name=dataset.name,
            version=ver_model.version,
            dataset_hash=ver_model.file_hash,
        )

        # Persist profile model
        profile_model = ProfileModel(
            dataset_version_id=ver_model.id,
            dataset_stats=profile.dataset_stats.model_dump(mode="json"),
            column_stats={k: v.model_dump(mode="json") for k, v in profile.column_stats.items()},
            temporal_stats={
                k: v.model_dump(mode="json") for k, v in profile.temporal_stats.items()
            },
        )
        self.session.add(profile_model)
        await self.session.flush()

        return profile

    async def get_latest_profile(self, dataset_id: str) -> dict[str, Any] | None:
        """Retrieve the most recent profile for a dataset."""
        if self.session is None:
            return None

        # Find latest version
        v_stmt = (
            select(DatasetVersionModel)
            .where(DatasetVersionModel.dataset_id == dataset_id)
            .order_by(DatasetVersionModel.version.desc())
        )
        v_res = await self.session.execute(v_stmt)
        latest_ver = v_res.scalars().first()
        if latest_ver is None:
            raise DatasetNotFoundError(f"Dataset {dataset_id} has no versions")

        p_stmt = (
            select(ProfileModel)
            .where(ProfileModel.dataset_version_id == latest_ver.id)
            .order_by(ProfileModel.created_at.desc())
        )
        p_res = await self.session.execute(p_stmt)
        profile_model = p_res.scalars().first()
        if profile_model is None:
            return None

        return {
            "id": profile_model.id,
            "dataset_version_id": profile_model.dataset_version_id,
            "dataset_stats": profile_model.dataset_stats,
            "column_stats": profile_model.column_stats,
            "temporal_stats": profile_model.temporal_stats,
            "created_at": profile_model.created_at.isoformat(),
        }
