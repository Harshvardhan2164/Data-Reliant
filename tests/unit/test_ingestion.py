"""Unit tests for the Data Ingestion Engine."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from datareliant.common.database import Base
from datareliant.common.exceptions import (
    FileTooLargeError,
    IngestionError,
    UnsupportedFormatError,
)
from datareliant.ingestion.service import IngestionService
from datareliant.ingestion.sources import CSVSource, ParquetSource
from datareliant.ingestion.validator import (
    compute_file_hash,
    detect_file_encoding,
    validate_file_format,
    validate_file_path,
    validate_file_size,
)


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    """Create a temporary valid CSV file."""
    csv_file = tmp_path / "orders.csv"
    df = pl.DataFrame(
        {
            "order_id": [101, 102, 103, 104],
            "customer_id": ["C1", "C2", "C1", "C3"],
            "amount": [99.50, 150.00, 25.20, 310.00],
            "status": ["completed", "completed", "pending", "failed"],
        }
    )
    df.write_csv(csv_file)
    return csv_file


@pytest.fixture
def sample_parquet(tmp_path: Path) -> Path:
    """Create a temporary valid Parquet file."""
    pq_file = tmp_path / "transactions.parquet"
    df = pl.DataFrame(
        {
            "tx_id": ["T1", "T2", "T3"],
            "val": [10.5, 20.0, 30.5],
        }
    )
    df.write_parquet(pq_file)
    return pq_file


@pytest.fixture
async def in_memory_session():
    """Create an in-memory SQLite database session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


class TestValidators:
    """Tests for file and metadata validation functions."""

    def test_validate_file_path(self, sample_csv: Path):
        path = validate_file_path(sample_csv)
        assert path.exists()

    def test_validate_nonexistent_file(self, tmp_path: Path):
        with pytest.raises(IngestionError, match="does not exist"):
            validate_file_path(tmp_path / "missing.csv")

    def test_validate_file_format(self, sample_csv: Path, sample_parquet: Path):
        assert validate_file_format(sample_csv) == "csv"
        assert validate_file_format(sample_parquet) == "parquet"

    def test_validate_unsupported_format(self, tmp_path: Path):
        bad_file = tmp_path / "data.docx"
        bad_file.write_text("dummy")
        with pytest.raises(UnsupportedFormatError):
            validate_file_format(bad_file)

    def test_validate_file_size_limit(self, sample_csv: Path):
        with pytest.raises(FileTooLargeError):
            validate_file_size(sample_csv, max_bytes=10)  # very small threshold

    def test_compute_file_hash(self, sample_csv: Path):
        h1 = compute_file_hash(sample_csv)
        assert len(h1) == 64  # sha256 hex string
        h2 = compute_file_hash(sample_csv)
        assert h1 == h2

    def test_detect_encoding(self, sample_csv: Path):
        enc = detect_file_encoding(sample_csv)
        assert enc.lower() in ("utf-8", "ascii")


class TestDataSources:
    """Tests for CSV and Parquet DataSource adapters."""

    def test_csv_source_load(self, sample_csv: Path):
        source = CSVSource(sample_csv)
        df = source.load()
        assert df.height == 4
        assert df.width == 4
        assert "order_id" in df.columns

    def test_csv_source_schema(self, sample_csv: Path):
        source = CSVSource(sample_csv)
        schema = source.schema()
        assert "order_id" in schema
        assert "amount" in schema

    def test_csv_source_metadata(self, sample_csv: Path):
        source = CSVSource(sample_csv)
        meta = source.metadata()
        assert meta.source_type == "csv"
        assert meta.format == "csv"
        assert meta.file_hash is not None

    def test_parquet_source_load(self, sample_parquet: Path):
        source = ParquetSource(sample_parquet)
        df = source.load()
        assert df.height == 3
        assert df.width == 2

    def test_parquet_source_schema(self, sample_parquet: Path):
        source = ParquetSource(sample_parquet)
        schema = source.schema()
        assert "tx_id" in schema
        assert "val" in schema


class TestIngestionService:
    """Tests for IngestionService using in-memory database."""

    @pytest.mark.asyncio
    async def test_ingest_file_creates_dataset_and_version(
        self, sample_csv: Path, in_memory_session: AsyncSession
    ):
        service = IngestionService(in_memory_session)
        dataset, ver, df = await service.ingest_file(
            file_path=sample_csv,
            dataset_name="test_orders",
            description="Test customer orders",
        )

        assert dataset.name == "test_orders"
        assert ver.version == 1
        assert ver.row_count == 4
        assert ver.column_count == 4
        assert df.height == 4

    @pytest.mark.asyncio
    async def test_ingest_auto_increment_version(
        self, sample_csv: Path, in_memory_session: AsyncSession
    ):
        service = IngestionService(in_memory_session)
        _, ver1, _ = await service.ingest_file(sample_csv, "orders_v")
        assert ver1.version == 1

        _, ver2, _ = await service.ingest_file(sample_csv, "orders_v")
        assert ver2.version == 2
