"""Unit tests for synthetic data generation and all 13 failure injection scenarios."""

from __future__ import annotations

import polars as pl
import pytest

from datareliant.common.types import RootCauseType, Severity
from generators.anomaly_injection.scenarios import FailureInjector
from generators.normal_data.enterprise import EnterpriseDataGenerator


@pytest.fixture
def enterprise_datasets() -> dict[str, pl.DataFrame]:
    """Generate minimal test enterprise datasets."""
    gen = EnterpriseDataGenerator(seed=123)
    return gen.generate_full_enterprise_dataset(
        n_customers=50,
        n_products=20,
        n_transactions=100,
    )


class TestEnterpriseDataGenerator:
    """Test normal data generation and relational consistency."""

    def test_generate_customers(self):
        gen = EnterpriseDataGenerator(seed=42)
        df = gen.generate_customers(n_rows=50)
        assert df.height == 50
        assert "customer_id" in df.columns
        assert "credit_score" in df.columns
        assert df["customer_id"].n_unique() == 50

    def test_relational_consistency(self, enterprise_datasets: dict[str, pl.DataFrame]):
        cust_df = enterprise_datasets["customers"]
        tx_df = enterprise_datasets["transactions"]
        pay_df = enterprise_datasets["payments"]

        # All transaction customer_ids must exist in customer table
        cust_set = set(cust_df["customer_id"].to_list())
        tx_cust_set = set(tx_df["customer_id"].to_list())
        assert tx_cust_set.issubset(cust_set)

        # All payment tx_ids must exist in transactions
        tx_set = set(tx_df["transaction_id"].to_list())
        pay_tx_set = set(pay_df["transaction_id"].to_list())
        assert pay_tx_set.issubset(tx_set)


class TestFailureInjectionLaboratory:
    """Test all 13 failure scenarios and verify known ground truth."""

    def test_1_missing_rows(self, enterprise_datasets: dict[str, pl.DataFrame]):
        tx_df = enterprise_datasets["transactions"]
        injector = FailureInjector(seed=42)
        corrupted, sc = injector.inject_missing_rows(tx_df, drop_fraction=0.30)

        assert corrupted.height < tx_df.height
        assert sc.root_cause == RootCauseType.MISSING_DATA
        assert sc.severity == Severity.HIGH
        assert sc.ground_truth["dropped_rows"] == tx_df.height - corrupted.height

    def test_2_duplicate_rows(self, enterprise_datasets: dict[str, pl.DataFrame]):
        tx_df = enterprise_datasets["transactions"]
        injector = FailureInjector(seed=42)
        corrupted, sc = injector.inject_duplicate_rows(tx_df, duplicate_fraction=0.20)

        assert corrupted.height > tx_df.height
        assert sc.root_cause == RootCauseType.DUPLICATE_INGESTION
        assert sc.ground_truth["injected_duplicate_count"] > 0

    def test_3_null_spike(self, enterprise_datasets: dict[str, pl.DataFrame]):
        tx_df = enterprise_datasets["transactions"]
        injector = FailureInjector(seed=42)
        corrupted, sc = injector.inject_null_spike(tx_df, column="amount", null_fraction=0.40)

        assert corrupted["amount"].null_count() > 0
        assert sc.root_cause == RootCauseType.NULL_SPIKE
        assert sc.target_column == "amount"

    def test_4_schema_addition(self, enterprise_datasets: dict[str, pl.DataFrame]):
        tx_df = enterprise_datasets["transactions"]
        injector = FailureInjector(seed=42)
        corrupted, sc = injector.inject_schema_addition(tx_df, new_column="extra_field")

        assert "extra_field" in corrupted.columns
        assert sc.root_cause == RootCauseType.SCHEMA_DRIFT

    def test_5_schema_removal(self, enterprise_datasets: dict[str, pl.DataFrame]):
        tx_df = enterprise_datasets["transactions"]
        injector = FailureInjector(seed=42)
        corrupted, sc = injector.inject_schema_removal(tx_df, column="channel")

        assert "channel" not in corrupted.columns
        assert sc.root_cause == RootCauseType.SCHEMA_DRIFT
        assert sc.severity == Severity.CRITICAL

    def test_6_datatype_change(self, enterprise_datasets: dict[str, pl.DataFrame]):
        tx_df = enterprise_datasets["transactions"]
        injector = FailureInjector(seed=42)
        corrupted, sc = injector.inject_datatype_change(tx_df, column="quantity")

        assert corrupted["quantity"].dtype == pl.String
        assert sc.root_cause == RootCauseType.TYPE_CHANGE

    def test_7_range_violation(self, enterprise_datasets: dict[str, pl.DataFrame]):
        tx_df = enterprise_datasets["transactions"]
        injector = FailureInjector(seed=42)
        corrupted, sc = injector.inject_range_violation(tx_df, column="amount", factor=50.0)

        assert corrupted["amount"].max() > tx_df["amount"].max()
        assert sc.root_cause == RootCauseType.TRANSFORMATION_ERROR

    def test_8_categorical_corruption(self, enterprise_datasets: dict[str, pl.DataFrame]):
        tx_df = enterprise_datasets["transactions"]
        injector = FailureInjector(seed=42)
        corrupted, sc = injector.inject_categorical_corruption(
            tx_df, column="channel", corrupted_value="ILLEGAL_VALUE_123"
        )

        assert "ILLEGAL_VALUE_123" in corrupted["channel"].to_list()
        assert sc.root_cause == RootCauseType.SOURCE_DATA_CHANGE

    def test_9_distribution_shift(self, enterprise_datasets: dict[str, pl.DataFrame]):
        tx_df = enterprise_datasets["transactions"]
        injector = FailureInjector(seed=42)
        corrupted, sc = injector.inject_distribution_shift(tx_df, column="amount", shift_mean=100.0)

        assert corrupted["amount"].mean() > tx_df["amount"].mean()
        assert sc.root_cause == RootCauseType.DISTRIBUTION_SHIFT

    def test_10_timezone_shift(self, enterprise_datasets: dict[str, pl.DataFrame]):
        tx_df = enterprise_datasets["transactions"]
        injector = FailureInjector(seed=42)
        corrupted, sc = injector.inject_timezone_shift(tx_df, column="timestamp", offset_hours=5)

        assert corrupted["timestamp"].min() > tx_df["timestamp"].min()
        assert sc.root_cause == RootCauseType.TIMEZONE_MISMATCH

    def test_11_late_arrival(self, enterprise_datasets: dict[str, pl.DataFrame]):
        tx_df = enterprise_datasets["transactions"]
        injector = FailureInjector(seed=42)
        corrupted, sc = injector.inject_late_arrival(tx_df, column="timestamp", delay_days=10)

        assert corrupted["timestamp"].min() < tx_df["timestamp"].min()
        assert sc.root_cause == RootCauseType.LATE_ARRIVAL

    def test_12_upstream_failure(self, enterprise_datasets: dict[str, pl.DataFrame]):
        cust_df = enterprise_datasets["customers"]
        tx_df = enterprise_datasets["transactions"]
        injector = FailureInjector(seed=42)
        corrupted_upstream, _, sc = injector.inject_upstream_failure(
            upstream_df=cust_df,
            downstream_df=tx_df,
            upstream_key="customer_id",
            downstream_key="customer_id",
            upstream_name="customers",
        )

        assert corrupted_upstream.height < cust_df.height
        assert sc.root_cause == RootCauseType.UPSTREAM_FAILURE
        assert sc.severity == Severity.CRITICAL

    def test_13_mixed_failure(self, enterprise_datasets: dict[str, pl.DataFrame]):
        tx_df = enterprise_datasets["transactions"]
        injector = FailureInjector(seed=42)
        corrupted, sc = injector.inject_mixed_failure(
            tx_df, numeric_column="amount", categorical_column="channel"
        )

        assert corrupted.height == tx_df.height
        assert "err_traceback" in corrupted.columns
        assert sc.root_cause == RootCauseType.TRANSFORMATION_ERROR
        assert len(sc.ground_truth["components"]) == 3
