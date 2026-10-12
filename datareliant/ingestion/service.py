"""Ingestion service managing dataset registration, versioning, and storage."""

from __future__ import annotations

import shutil
from pathlib import Path

import polars as pl
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from datareliant.common.config import get_settings
from datareliant.common.exceptions import (
    DatasetNotFoundError,
    DatasetVersionConflictError,
    IngestionError,
)
from datareliant.common.models import DatasetModel, DatasetVersionModel
from datareliant.ingestion.base import DataSource
from datareliant.ingestion.sources import CSVSource, ParquetSource
from datareliant.ingestion.validator import (
    validate_file_format,
    validate_file_path,
)


class IngestionService:
    """Service orchestrating dataset registration, storage, and versioning."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session
        self.settings = get_settings()
        self.storage_root = Path(self.settings.local_storage_path)
        self.storage_root.mkdir(parents=True, exist_ok=True)

    def create_source_from_file(self, file_path: Path | str) -> DataSource:
        """Factory method to instantiate the correct DataSource based on extension."""
        path = validate_file_path(file_path)
        fmt = validate_file_format(path)
        if fmt in ("csv", "tsv"):
            return CSVSource(path)
        elif fmt == "parquet":
            return ParquetSource(path)
        raise IngestionError(f"Unsupported format '{fmt}' for file {path}")

    async def ingest_file(
        self,
        file_path: Path | str,
        dataset_name: str,
        description: str | None = None,
        version: int | None = None,
    ) -> tuple[DatasetModel, DatasetVersionModel, pl.DataFrame]:
        """Ingest a file into DataReliant, creating or updating dataset and version.

        Args:
            file_path: Path to the local file to ingest.
            dataset_name: Unique logical identifier for the dataset.
            description: Optional textual description.
            version: Explicit version number, or None to auto-increment.

        Returns:
            Tuple of (DatasetModel, DatasetVersionModel, pl.DataFrame)
        """
        if self.session is None:
            raise IngestionError("Database session required for persistent ingestion")

        source = self.create_source_from_file(file_path)
        df = source.load()
        metadata = source.metadata()
        schema_map = source.schema()

        # Find or create DatasetModel
        stmt = (
            select(DatasetModel)
            .where(DatasetModel.name == dataset_name)
            .options(selectinload(DatasetModel.versions))
        )
        res = await self.session.execute(stmt)
        dataset = res.scalar_one_or_none()

        if dataset is None:
            dataset = DatasetModel(
                name=dataset_name,
                description=description,
                source_type=metadata.source_type,
                metadata_={
                    "format": metadata.format,
                    "created_from": str(file_path),
                },
            )
            self.session.add(dataset)
            await self.session.flush()
            next_version = version or 1
        else:
            if version is not None:
                next_version = version
            else:
                # auto-increment version
                v_stmt = select(func.max(DatasetVersionModel.version)).where(
                    DatasetVersionModel.dataset_id == dataset.id
                )
                v_res = await self.session.execute(v_stmt)
                max_v = v_res.scalar_one_or_none() or 0
                next_version = max_v + 1

        # Check for version collision
        chk_stmt = select(DatasetVersionModel).where(
            DatasetVersionModel.dataset_id == dataset.id,
            DatasetVersionModel.version == next_version,
        )
        chk_res = await self.session.execute(chk_stmt)
        if chk_res.scalar_one_or_none() is not None:
            raise DatasetVersionConflictError(
                f"Version {next_version} already exists for dataset '{dataset_name}'",
                details={"dataset_name": dataset_name, "version": next_version},
            )

        # Store a copy in managed local storage
        target_dir = self.storage_root / dataset_name / f"v{next_version}"
        target_dir.mkdir(parents=True, exist_ok=True)
        source_path = Path(file_path)
        target_path = target_dir / source_path.name
        shutil.copy2(source_path, target_path)

        dataset_version = DatasetVersionModel(
            dataset_id=dataset.id,
            version=next_version,
            row_count=df.height,
            column_count=df.width,
            file_path=str(target_path.resolve()),
            file_hash=metadata.file_hash,
            schema_snapshot=schema_map,
        )
        self.session.add(dataset_version)
        await self.session.flush()

        return dataset, dataset_version, df

    async def get_dataset(self, dataset_id: str) -> DatasetModel:
        """Fetch a dataset by ID along with its versions."""
        if self.session is None:
            raise IngestionError("Database session required")

        stmt = (
            select(DatasetModel)
            .where(DatasetModel.id == dataset_id)
            .options(selectinload(DatasetModel.versions))
        )
        res = await self.session.execute(stmt)
        dataset = res.scalar_one_or_none()
        if dataset is None:
            raise DatasetNotFoundError(f"Dataset with ID '{dataset_id}' not found")
        return dataset

    async def list_datasets(self) -> list[DatasetModel]:
        """List all registered datasets."""
        if self.session is None:
            return []
        stmt = select(DatasetModel).options(selectinload(DatasetModel.versions))
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def load_version_dataframe(
        self, dataset_id: str, version: int | None = None
    ) -> tuple[DatasetVersionModel, pl.DataFrame]:
        """Load the Polars DataFrame for a dataset version."""
        if self.session is None:
            raise IngestionError("Database session required")

        if version is not None:
            stmt = select(DatasetVersionModel).where(
                DatasetVersionModel.dataset_id == dataset_id,
                DatasetVersionModel.version == version,
            )
        else:
            # Get latest version
            stmt = (
                select(DatasetVersionModel)
                .where(DatasetVersionModel.dataset_id == dataset_id)
                .order_by(DatasetVersionModel.version.desc())
            )
        res = await self.session.execute(stmt)
        ver = res.scalars().first()
        if ver is None:
            raise DatasetNotFoundError(
                f"Dataset version not found for ID '{dataset_id}', version '{version}'"
            )

        if not ver.file_path or not Path(ver.file_path).exists():
            raise IngestionError(
                f"Data file for version {ver.version} not found at {ver.file_path}"
            )

        source = self.create_source_from_file(ver.file_path)
        df = source.load()
        return ver, df
