"""Unit tests for the Data Profiling Engine."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from datareliant.common.database import Base
from datareliant.ingestion.service import IngestionService
from datareliant.profiling.profiler import DataProfiler
from datareliant.profiling.service import ProfilingService


@pytest.fixture
def rich_dataframe() -> pl.DataFrame:
    """Create a rich DataFrame with numeric, string, boolean, and datetime columns."""
    base_time = datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC)
    timestamps = [base_time + timedelta(hours=i) for i in range(10)]
    # Introduce a gap for testing
    timestamps.append(base_time + timedelta(hours=20))

    return pl.DataFrame(
        {
            "user_id": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
            "score": [85.5, 92.0, 78.5, None, 88.0, 95.5, 60.0, 72.5, 84.0, 91.0, 80.0],
            "role": [
                "admin",
                "user",
                "user",
                "editor",
                "user",
                "admin",
                "user",
                "user",
                "editor",
                "user",
                "user",
            ],
            "is_active": [True, True, False, True, True, False, True, True, False, True, True],
            "created_at": timestamps,
        }
    )


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


class TestDataProfiler:
    """Test statistical, column, and temporal profiling."""

    def test_dataset_level_stats(self, rich_dataframe: pl.DataFrame):
        profiler = DataProfiler()
        profile = profiler.profile(rich_dataframe, dataset_name="users_table")

        ds = profile.dataset_stats
        assert ds.row_count == 11
        assert ds.column_count == 5
        assert ds.memory_estimate_bytes > 0
        assert ds.duplicate_row_count == 0
        assert ds.duplicate_row_percentage == 0.0
        assert ds.temporal_coverage is not None

    def test_duplicate_row_detection(self):
        df_with_dups = pl.DataFrame(
            {
                "a": [1, 1, 2, 2, 3],
                "b": ["x", "x", "y", "y", "z"],
            }
        )
        profiler = DataProfiler()
        profile = profiler.profile(df_with_dups)
        assert profile.dataset_stats.duplicate_row_count == 2
        assert profile.dataset_stats.duplicate_row_percentage == pytest.approx(40.0)

    def test_column_level_stats_numeric(self, rich_dataframe: pl.DataFrame):
        profiler = DataProfiler()
        profile = profiler.profile(rich_dataframe)

        score_col = profile.column_stats["score"]
        assert score_col.name == "score"
        assert score_col.null_count == 1
        assert score_col.null_percentage == pytest.approx(9.09, abs=0.1)
        assert score_col.min_value == 60.0
        assert score_col.max_value == 95.5
        assert score_col.mean is not None and 80.0 <= score_col.mean <= 85.0
        assert score_col.median is not None
        assert score_col.std_dev is not None and score_col.std_dev > 0.0
        assert "p25" in score_col.quantiles
        assert "p50" in score_col.quantiles
        assert "p75" in score_col.quantiles
        assert "p99" in score_col.quantiles

    def test_column_level_stats_categorical(self, rich_dataframe: pl.DataFrame):
        profiler = DataProfiler()
        profile = profiler.profile(rich_dataframe)

        role_col = profile.column_stats["role"]
        assert role_col.name == "role"
        assert role_col.unique_count == 3
        assert len(role_col.categorical_frequencies) == 3
        # Top category should be 'user'
        top_cat = role_col.categorical_frequencies[0]
        assert top_cat["value"] == "user"
        assert top_cat["count"] == 7

    def test_temporal_stats(self, rich_dataframe: pl.DataFrame):
        profiler = DataProfiler()
        profile = profiler.profile(rich_dataframe)

        assert "created_at" in profile.temporal_stats
        t = profile.temporal_stats["created_at"]
        assert t.min_timestamp is not None
        assert t.max_timestamp is not None
        assert t.inferred_frequency == "1h"
        # We injected a 10-hour jump after consecutive 1-hour increments
        assert t.gaps_count >= 1
        assert t.freshness_seconds is not None and t.freshness_seconds >= 0.0


class TestProfilingService:
    """Test ProfilingService end-to-end integration with database."""

    @pytest.mark.asyncio
    async def test_profile_and_persist(self, tmp_path: Path, in_memory_session: AsyncSession):
        csv_file = tmp_path / "customers.csv"
        df = pl.DataFrame(
            {
                "customer_id": [1, 2, 3],
                "country": ["US", "DE", "FR"],
                "spend": [500.0, 1200.0, 300.0],
            }
        )
        df.write_csv(csv_file)

        ingestion = IngestionService(in_memory_session)
        dataset, ver, _ = await ingestion.ingest_file(csv_file, "customers")

        profiler_svc = ProfilingService(in_memory_session)
        profile = await profiler_svc.profile_dataset_version(dataset.id, ver.version)

        assert profile.dataset_name == "customers"
        assert profile.version == 1
        assert profile.dataset_stats.row_count == 3
        assert profile.dataset_stats.column_count == 3

        # Retrieve persisted profile
        latest = await profiler_svc.get_latest_profile(dataset.id)
        assert latest is not None
        assert latest["dataset_stats"]["row_count"] == 3
        assert "country" in latest["column_stats"]
