"""Base interfaces and data structures for the Data Ingestion Engine."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import polars as pl
from pydantic import BaseModel, Field


class DataSourceMetadata(BaseModel):
    """Metadata describing an ingested data source."""

    source_type: str
    location: str
    file_size_bytes: int = 0
    file_hash: str | None = None
    format: str
    encoding: str | None = None
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    extra: dict[str, Any] = Field(default_factory=dict)


class IngestionResult(BaseModel):
    """Container holding ingestion output and metadata."""

    dataset_name: str
    version: int
    row_count: int
    column_count: int
    schema_map: dict[str, str]
    file_hash: str
    metadata: DataSourceMetadata


class DataSource(ABC):
    """Abstract base class for all data source adapters."""

    @abstractmethod
    def load(self) -> pl.DataFrame:
        """Load the dataset into a Polars DataFrame."""
        raise NotImplementedError

    @abstractmethod
    def schema(self) -> dict[str, str]:
        """Return the schema as a mapping of column name to data type string."""
        raise NotImplementedError

    @abstractmethod
    def metadata(self) -> DataSourceMetadata:
        """Return metadata regarding the data source."""
        raise NotImplementedError
