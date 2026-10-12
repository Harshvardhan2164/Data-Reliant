"""Data Ingestion Engine for DataReliant."""

from datareliant.ingestion.base import DataSource, DataSourceMetadata, IngestionResult
from datareliant.ingestion.service import IngestionService
from datareliant.ingestion.sources import CSVSource, ParquetSource, PostgreSQLSource
from datareliant.ingestion.validator import (
    compute_file_hash,
    detect_file_encoding,
    validate_file_format,
    validate_file_path,
    validate_file_size,
)

__all__ = [
    "CSVSource",
    "DataSource",
    "DataSourceMetadata",
    "IngestionResult",
    "IngestionService",
    "ParquetSource",
    "PostgreSQLSource",
    "compute_file_hash",
    "detect_file_encoding",
    "validate_file_format",
    "validate_file_path",
    "validate_file_size",
]
