"""Concrete DataSource adapters for CSV, Parquet, and PostgreSQL."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl

from datareliant.common.exceptions import IngestionError
from datareliant.ingestion.base import DataSource, DataSourceMetadata
from datareliant.ingestion.validator import (
    compute_file_hash,
    detect_file_encoding,
    validate_file_format,
    validate_file_path,
    validate_file_size,
)


def _polars_schema_to_str_dict(schema: pl.Schema) -> dict[str, str]:
    """Convert a Polars Schema into a clean string representation."""
    return {col: str(dtype) for col, dtype in schema.items()}


class CSVSource(DataSource):
    """Adapter for CSV and TSV files."""

    def __init__(
        self,
        file_path: Path | str,
        separator: str | None = None,
        encoding: str | None = None,
        has_header: bool = True,
        max_bytes: int | None = None,
    ) -> None:
        self.path = validate_file_path(file_path)
        validate_file_format(self.path)
        self.file_size = validate_file_size(self.path, max_bytes=max_bytes)
        self.encoding = encoding or detect_file_encoding(self.path)
        self.separator = separator or ("\t" if self.path.suffix.lower() == ".tsv" else ",")
        self.has_header = has_header
        self._cached_df: pl.DataFrame | None = None
        self._hash: str | None = None

    def load(self) -> pl.DataFrame:
        """Load CSV content into a Polars DataFrame."""
        if self._cached_df is not None:
            return self._cached_df

        try:
            df = pl.read_csv(
                self.path,
                separator=self.separator,
                has_header=self.has_header,
                encoding=self.encoding,
                ignore_errors=False,
                infer_schema_length=10000,
                null_values=["", "NA", "null", "NULL", "None", "NaN"],
            )
            self._cached_df = df
            return df
        except Exception as exc:
            raise IngestionError(
                f"Failed to parse CSV file '{self.path.name}': {exc}",
                details={"file_path": str(self.path), "error": str(exc)},
            ) from exc

    def schema(self) -> dict[str, str]:
        """Return the schema dictionary without necessarily loading full table."""
        if self._cached_df is not None:
            return _polars_schema_to_str_dict(self._cached_df.schema)
        try:
            scan = pl.scan_csv(
                self.path,
                separator=self.separator,
                has_header=self.has_header,
                encoding=self.encoding,
            )
            return _polars_schema_to_str_dict(scan.collect_schema())
        except Exception:
            # Fall back to load if scanning fails
            return _polars_schema_to_str_dict(self.load().schema)

    def metadata(self) -> DataSourceMetadata:
        """Return metadata for the CSV source."""
        if self._hash is None:
            self._hash = compute_file_hash(self.path)
        return DataSourceMetadata(
            source_type="csv",
            location=str(self.path.resolve()),
            file_size_bytes=self.file_size,
            file_hash=self._hash,
            format="csv",
            encoding=self.encoding,
            extra={"separator": self.separator, "has_header": self.has_header},
        )


class ParquetSource(DataSource):
    """Adapter for Apache Parquet files."""

    def __init__(
        self,
        file_path: Path | str,
        max_bytes: int | None = None,
    ) -> None:
        self.path = validate_file_path(file_path)
        validate_file_format(self.path)
        self.file_size = validate_file_size(self.path, max_bytes=max_bytes)
        self._cached_df: pl.DataFrame | None = None
        self._hash: str | None = None

    def load(self) -> pl.DataFrame:
        """Load Parquet file into a Polars DataFrame."""
        if self._cached_df is not None:
            return self._cached_df

        try:
            df = pl.read_parquet(self.path)
            self._cached_df = df
            return df
        except Exception as exc:
            raise IngestionError(
                f"Failed to parse Parquet file '{self.path.name}': {exc}",
                details={"file_path": str(self.path), "error": str(exc)},
            ) from exc

    def schema(self) -> dict[str, str]:
        """Return the schema dictionary."""
        if self._cached_df is not None:
            return _polars_schema_to_str_dict(self._cached_df.schema)
        try:
            scan = pl.scan_parquet(self.path)
            return _polars_schema_to_str_dict(scan.collect_schema())
        except Exception:
            return _polars_schema_to_str_dict(self.load().schema)

    def metadata(self) -> DataSourceMetadata:
        """Return metadata for the Parquet source."""
        if self._hash is None:
            self._hash = compute_file_hash(self.path)
        return DataSourceMetadata(
            source_type="parquet",
            location=str(self.path.resolve()),
            file_size_bytes=self.file_size,
            file_hash=self._hash,
            format="parquet",
            encoding="binary",
        )


class PostgreSQLSource(DataSource):
    """Adapter for loading data from PostgreSQL via connection URI."""

    def __init__(
        self,
        connection_uri: str,
        table_name: str | None = None,
        query: str | None = None,
    ) -> None:
        if not table_name and not query:
            raise IngestionError("Either table_name or query must be provided for PostgreSQLSource")
        self.connection_uri = connection_uri
        self.table_name = table_name
        self.query = query or f"SELECT * FROM {table_name}"
        self._cached_df: pl.DataFrame | None = None

    def load(self) -> pl.DataFrame:
        """Load table or query result from PostgreSQL."""
        if self._cached_df is not None:
            return self._cached_df

        try:
            df = pl.read_database_uri(
                query=self.query,
                uri=self.connection_uri,
            )
            self._cached_df = df
            return df
        except Exception as exc:
            raise IngestionError(
                f"Failed to query PostgreSQL: {exc}",
                details={"query": self.query, "error": str(exc)},
            ) from exc

    def schema(self) -> dict[str, str]:
        """Return schema dictionary."""
        return _polars_schema_to_str_dict(self.load().schema)

    def metadata(self) -> DataSourceMetadata:
        """Return metadata for the PostgreSQL source."""
        return DataSourceMetadata(
            source_type="postgresql",
            location=f"postgresql://{self.table_name or 'query'}",
            format="relational",
            extra={"query": self.query, "table_name": self.table_name},
        )
