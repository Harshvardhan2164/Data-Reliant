"""Unit tests for the Data Quality Rule Engine covering all 10 rule types."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from datareliant.common.database import Base
from datareliant.common.types import Severity, Status
from datareliant.ingestion.service import IngestionService
from datareliant.quality.base import QualityContext, RuleRegistry
from datareliant.quality.engine import QualityEngine
from datareliant.quality.models import (
    QualityRuleConfig,
    QualitySuiteConfig,
)
from datareliant.quality.service import QualityService


@pytest.fixture
def test_df() -> pl.DataFrame:
    """Create test dataframe."""
    now = datetime.now(UTC)
    return pl.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "name": ["Alice", "Bob", "Charlie", "David", "Eve"],
            "age": [25, 30, 35, 40, 45],
            "dept": ["HR", "ENG", "ENG", "MKT", "HR"],
            "score": [80.0, None, 95.0, 70.0, 85.0],
            "created_at": [now - timedelta(minutes=10 * i) for i in range(5)],
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


class TestQualityRules:
    """Tests for each of the 10 rule implementations."""

    def test_registry_contains_all_rules(self):
        rules = RuleRegistry.available_rules()
        expected = [
            "categorical_values",
            "custom_expression",
            "duplicate_rows",
            "freshness",
            "not_null",
            "range",
            "referential_integrity",
            "row_count",
            "schema",
            "uniqueness",
        ]
        for r in expected:
            assert r in rules

    def test_not_null_rule_pass_and_fail(self, test_df: pl.DataFrame):
        engine = QualityEngine()
        # id has no nulls -> PASS
        cfg_pass = QualityRuleConfig(
            name="id_not_null",
            type="not_null",
            dataset="test",
            column="id",
        )
        res_pass = engine.run_rule(test_df, cfg_pass)
        assert res_pass.status == Status.PASSED
        assert res_pass.failure_count == 0

        # score has 1 null out of 5 (20%) -> FAIL with 0% allowed
        cfg_fail = QualityRuleConfig(
            name="score_not_null",
            type="not_null",
            dataset="test",
            column="score",
        )
        res_fail = engine.run_rule(test_df, cfg_fail)
        assert res_fail.status == Status.FAILED
        assert res_fail.failure_count == 1
        assert res_fail.failure_percentage == 20.0

    def test_uniqueness_rule_pass_and_fail(self, test_df: pl.DataFrame):
        engine = QualityEngine()
        # id is unique -> PASS
        cfg_pass = QualityRuleConfig(
            name="id_unique",
            type="uniqueness",
            dataset="test",
            column="id",
        )
        assert engine.run_rule(test_df, cfg_pass).status == Status.PASSED

        # dept has duplicates -> FAIL
        cfg_fail = QualityRuleConfig(
            name="dept_unique",
            type="uniqueness",
            dataset="test",
            column="dept",
        )
        res_fail = engine.run_rule(test_df, cfg_fail)
        assert res_fail.status == Status.FAILED
        assert res_fail.failure_count > 0

    def test_duplicate_rows_rule(self, test_df: pl.DataFrame):
        engine = QualityEngine()
        cfg = QualityRuleConfig(
            name="no_dup_rows",
            type="duplicate_rows",
            dataset="test",
        )
        assert engine.run_rule(test_df, cfg).status == Status.PASSED

        # Duplicate a row
        dup_df = pl.concat([test_df, test_df.head(1)])
        res_fail = engine.run_rule(dup_df, cfg)
        assert res_fail.status == Status.FAILED
        assert res_fail.failure_count == 1

    def test_range_rule_pass_and_fail(self, test_df: pl.DataFrame):
        engine = QualityEngine()
        # age 20 to 50 -> PASS
        cfg_pass = QualityRuleConfig(
            name="age_in_range",
            type="range",
            dataset="test",
            column="age",
            parameters={"min": 20, "max": 50},
        )
        assert engine.run_rule(test_df, cfg_pass).status == Status.PASSED

        # age 20 to 30 -> FAIL (has 35, 40, 45)
        cfg_fail = QualityRuleConfig(
            name="age_tight_range",
            type="range",
            dataset="test",
            column="age",
            parameters={"min": 20, "max": 30},
        )
        res_fail = engine.run_rule(test_df, cfg_fail)
        assert res_fail.status == Status.FAILED
        assert res_fail.failure_count == 3

    def test_categorical_values_rule(self, test_df: pl.DataFrame):
        engine = QualityEngine()
        cfg_pass = QualityRuleConfig(
            name="valid_depts",
            type="categorical_values",
            dataset="test",
            column="dept",
            parameters={"allowed_values": ["HR", "ENG", "MKT", "SALES"]},
        )
        assert engine.run_rule(test_df, cfg_pass).status == Status.PASSED

        cfg_fail = QualityRuleConfig(
            name="strict_depts",
            type="categorical_values",
            dataset="test",
            column="dept",
            parameters={"allowed_values": ["HR"]},  # ENG and MKT will fail
        )
        res_fail = engine.run_rule(test_df, cfg_fail)
        assert res_fail.status == Status.FAILED
        assert res_fail.failure_count == 3

    def test_schema_rule(self, test_df: pl.DataFrame):
        engine = QualityEngine()
        cfg_pass = QualityRuleConfig(
            name="valid_schema",
            type="schema",
            dataset="test",
            parameters={"expected_columns": ["id", "name", "age", "dept"]},
        )
        assert engine.run_rule(test_df, cfg_pass).status == Status.PASSED

        cfg_fail = QualityRuleConfig(
            name="missing_col_schema",
            type="schema",
            dataset="test",
            parameters={"expected_columns": ["id", "missing_salary_column"]},
        )
        assert engine.run_rule(test_df, cfg_fail).status == Status.FAILED

    def test_freshness_rule(self, test_df: pl.DataFrame):
        engine = QualityEngine()
        # Created in last hour -> PASS with max_age = 7200 seconds (2h)
        cfg_pass = QualityRuleConfig(
            name="data_fresh",
            type="freshness",
            dataset="test",
            column="created_at",
            parameters={"max_age_seconds": 7200},
        )
        assert engine.run_rule(test_df, cfg_pass).status == Status.PASSED

        # Create older dataframe (10 days old) -> FAIL with max_age = 3600s
        old_time = datetime.now(UTC) - timedelta(days=10)
        old_df = test_df.with_columns(
            pl.Series("created_at", [old_time - timedelta(hours=i) for i in range(5)])
        )
        cfg_fail = QualityRuleConfig(
            name="data_stale",
            type="freshness",
            dataset="test",
            column="created_at",
            parameters={"max_age_seconds": 3600},
        )
        assert engine.run_rule(old_df, cfg_fail).status == Status.FAILED

    def test_row_count_rule(self, test_df: pl.DataFrame):
        engine = QualityEngine()
        cfg_pass = QualityRuleConfig(
            name="row_count_ok",
            type="row_count",
            dataset="test",
            parameters={"min_rows": 1, "max_rows": 10},
        )
        assert engine.run_rule(test_df, cfg_pass).status == Status.PASSED

        cfg_fail = QualityRuleConfig(
            name="row_count_too_small",
            type="row_count",
            dataset="test",
            parameters={"min_rows": 100},
        )
        assert engine.run_rule(test_df, cfg_fail).status == Status.FAILED

    def test_referential_integrity_rule(self, test_df: pl.DataFrame):
        engine = QualityEngine()
        parent_df = pl.DataFrame({"dept_code": ["HR", "ENG", "MKT"]})
        ctx = QualityContext(reference_datasets={"departments": parent_df})

        cfg_pass = QualityRuleConfig(
            name="fk_dept",
            type="referential_integrity",
            dataset="test",
            column="dept",
            parameters={"parent_dataset": "departments", "parent_column": "dept_code"},
        )
        assert engine.run_rule(test_df, cfg_pass, context=ctx).status == Status.PASSED

        # Parent missing 'MKT'
        incomplete_parent = pl.DataFrame({"dept_code": ["HR", "ENG"]})
        ctx_fail = QualityContext(reference_datasets={"departments": incomplete_parent})
        res_fail = engine.run_rule(test_df, cfg_pass, context=ctx_fail)
        assert res_fail.status == Status.FAILED
        assert res_fail.failure_count == 1  # 1 row with MKT

    def test_custom_expression_rule(self, test_df: pl.DataFrame):
        engine = QualityEngine()
        # id > 0 -> PASS
        cfg_pass = QualityRuleConfig(
            name="positive_id",
            type="custom_expression",
            dataset="test",
            parameters={"expression": "id > 0"},
        )
        assert engine.run_rule(test_df, cfg_pass).status == Status.PASSED

        # age > 30 -> FAIL (25 and 30 violate)
        cfg_fail = QualityRuleConfig(
            name="age_over_30",
            type="custom_expression",
            dataset="test",
            parameters={"expression": "age > 30"},
        )
        res_fail = engine.run_rule(test_df, cfg_fail)
        assert res_fail.status == Status.FAILED
        assert res_fail.failure_count == 2


class TestQualitySuiteAndService:
    """Tests for suite execution and database persistence."""

    def test_yaml_suite_loading(self):
        yaml_content = """
name: test_suite
rules:
  - name: id_not_null
    type: not_null
    column: id
    severity: CRITICAL
  - name: positive_age
    type: range
    column: age
    parameters:
      min: 0
      max: 120
"""
        suite = QualityEngine.load_suite_from_yaml(yaml_content)
        assert suite.name == "test_suite"
        assert len(suite.rules) == 2
        assert suite.rules[0].type == "not_null"
        assert suite.rules[0].severity == Severity.CRITICAL

    @pytest.mark.asyncio
    async def test_quality_service_execute_and_persist(
        self, tmp_path: Path, in_memory_session: AsyncSession
    ):
        csv_file = tmp_path / "orders.csv"
        df = pl.DataFrame({"order_id": [1, 2, 3], "amount": [10.0, -5.0, 30.0]})
        df.write_csv(csv_file)

        ingestion = IngestionService(in_memory_session)
        dataset, ver, _ = await ingestion.ingest_file(csv_file, "orders_quality")

        suite = QualitySuiteConfig(
            name="orders_suite",
            rules=[
                QualityRuleConfig(
                    name="order_id_not_null",
                    type="not_null",
                    dataset=dataset.name,
                    column="order_id",
                ),
                QualityRuleConfig(
                    name="positive_amount",
                    type="range",
                    dataset=dataset.name,
                    column="amount",
                    severity=Severity.HIGH,
                    parameters={"min": 0.0},
                ),
            ],
        )

        service = QualityService(in_memory_session)
        summary = await service.execute_quality_run(
            dataset_id=dataset.id,
            version=ver.version,
            suite=suite,
        )

        assert summary.total_rules == 2
        assert summary.passed_rules == 1
        assert summary.failed_rules == 1
        assert summary.high_failures == 1

        # Fetch persisted run
        run_data = await service.get_run_results(summary.run_id)
        assert run_data["total_checks"] == 2
        assert run_data["dataset"] == "orders_quality"
