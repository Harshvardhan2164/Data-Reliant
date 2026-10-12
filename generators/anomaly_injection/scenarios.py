"""Failure Injection Laboratory: Controlled anomaly injection with known ground truth for all 13 scenarios."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
import polars as pl
from pydantic import BaseModel, Field

from datareliant.common.types import RootCauseType, Severity


class FailureScenario(BaseModel):
    """Container holding injected dataset and known ground truth for research evaluation."""

    scenario_id: str
    scenario_type: str
    root_cause: RootCauseType
    severity: Severity
    target_dataset: str
    target_column: str | None = None
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    ground_truth: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return self.model_dump(mode="json")


class FailureInjector:
    """Injects controlled data anomalies and failure scenarios into DataFrames."""

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    # ── 1. Missing Rows ───────────────────────────────────────────────
    def inject_missing_rows(
        self,
        df: pl.DataFrame,
        drop_fraction: float = 0.40,
        dataset_name: str = "dataset",
    ) -> tuple[pl.DataFrame, FailureScenario]:
        """Drop a substantial percentage of rows simulating upstream extraction cut-off."""
        orig_count = df.height
        keep_count = max(1, int(orig_count * (1.0 - drop_fraction)))
        # Sample rows to keep
        shuffled_indices = self.rng.permutation(orig_count)[:keep_count]
        corrupted_df = df[shuffled_indices].sort(df.columns[0])

        scenario = FailureScenario(
            scenario_id=f"missing_rows_{self.seed:03d}",
            scenario_type="missing_rows",
            root_cause=RootCauseType.MISSING_DATA,
            severity=Severity.HIGH,
            target_dataset=dataset_name,
            description=f"Dropped {round(drop_fraction * 100, 1)}% of rows from {dataset_name}",
            parameters={"drop_fraction": drop_fraction},
            ground_truth={
                "original_row_count": orig_count,
                "injected_row_count": corrupted_df.height,
                "dropped_rows": orig_count - corrupted_df.height,
            },
        )
        return corrupted_df, scenario

    # ── 2. Duplicate Rows ─────────────────────────────────────────────
    def inject_duplicate_rows(
        self,
        df: pl.DataFrame,
        duplicate_fraction: float = 0.35,
        dataset_name: str = "dataset",
    ) -> tuple[pl.DataFrame, FailureScenario]:
        """Duplicate a subset of rows simulating double-ingestion retry bug."""
        orig_count = df.height
        dup_count = int(orig_count * duplicate_fraction)
        chosen_indices = self.rng.choice(orig_count, size=dup_count)
        duplicate_slice = df[chosen_indices]
        corrupted_df = pl.concat([df, duplicate_slice])

        scenario = FailureScenario(
            scenario_id=f"duplicate_rows_{self.seed:03d}",
            scenario_type="duplicate_rows",
            root_cause=RootCauseType.DUPLICATE_INGESTION,
            severity=Severity.HIGH,
            target_dataset=dataset_name,
            description=f"Injected {dup_count} duplicate rows into {dataset_name}",
            parameters={"duplicate_fraction": duplicate_fraction},
            ground_truth={
                "original_row_count": orig_count,
                "injected_duplicate_count": dup_count,
                "total_rows": corrupted_df.height,
            },
        )
        return corrupted_df, scenario

    # ── 3. Null Spike ─────────────────────────────────────────────────
    def inject_null_spike(
        self,
        df: pl.DataFrame,
        column: str,
        null_fraction: float = 0.45,
        dataset_name: str = "dataset",
    ) -> tuple[pl.DataFrame, FailureScenario]:
        """Corrupt values in target column with nulls."""
        n = df.height
        corrupt_count = int(n * null_fraction)
        mask = np.zeros(n, dtype=bool)
        corrupt_indices = self.rng.choice(n, size=corrupt_count, replace=False)
        mask[corrupt_indices] = True

        orig_col = df[column]
        new_col = pl.when(pl.Series(mask)).then(None).otherwise(orig_col).alias(column)
        corrupted_df = df.with_columns(new_col)

        scenario = FailureScenario(
            scenario_id=f"null_spike_{self.seed:03d}",
            scenario_type="null_spike",
            root_cause=RootCauseType.NULL_SPIKE,
            severity=Severity.HIGH,
            target_dataset=dataset_name,
            target_column=column,
            description=f"Injected {round(null_fraction * 100, 1)}% null values into column '{column}'",
            parameters={"column": column, "null_fraction": null_fraction},
            ground_truth={"null_injected_count": corrupt_count, "column": column},
        )
        return corrupted_df, scenario

    # ── 4. Schema Addition ────────────────────────────────────────────
    def inject_schema_addition(
        self,
        df: pl.DataFrame,
        new_column: str = "unannounced_metadata_v2",
        dataset_name: str = "dataset",
    ) -> tuple[pl.DataFrame, FailureScenario]:
        """Append an unannounced column simulating uncoordinated schema addition."""
        values = [f"payload_{i}" for i in range(df.height)]
        corrupted_df = df.with_columns(pl.Series(new_column, values))

        scenario = FailureScenario(
            scenario_id=f"schema_addition_{self.seed:03d}",
            scenario_type="schema_addition",
            root_cause=RootCauseType.SCHEMA_DRIFT,
            severity=Severity.MEDIUM,
            target_dataset=dataset_name,
            target_column=new_column,
            description=f"Added unexpected column '{new_column}' to {dataset_name}",
            parameters={"new_column": new_column},
            ground_truth={"added_column": new_column},
        )
        return corrupted_df, scenario

    # ── 5. Schema Removal ─────────────────────────────────────────────
    def inject_schema_removal(
        self,
        df: pl.DataFrame,
        column: str,
        dataset_name: str = "dataset",
    ) -> tuple[pl.DataFrame, FailureScenario]:
        """Drop a critical column simulating breaking schema removal."""
        corrupted_df = df.drop(column)

        scenario = FailureScenario(
            scenario_id=f"schema_removal_{self.seed:03d}",
            scenario_type="schema_removal",
            root_cause=RootCauseType.SCHEMA_DRIFT,
            severity=Severity.CRITICAL,
            target_dataset=dataset_name,
            target_column=column,
            description=f"Removed column '{column}' from {dataset_name}",
            parameters={"removed_column": column},
            ground_truth={"removed_column": column},
        )
        return corrupted_df, scenario

    # ── 6. Datatype Change ────────────────────────────────────────────
    def inject_datatype_change(
        self,
        df: pl.DataFrame,
        column: str,
        dataset_name: str = "dataset",
    ) -> tuple[pl.DataFrame, FailureScenario]:
        """Cast numeric or datetime column to string simulating producer type corruption."""
        orig_type = str(df[column].dtype)
        corrupted_df = df.with_columns(df[column].cast(pl.String).alias(column))

        scenario = FailureScenario(
            scenario_id=f"datatype_change_{self.seed:03d}",
            scenario_type="datatype_change",
            root_cause=RootCauseType.TYPE_CHANGE,
            severity=Severity.HIGH,
            target_dataset=dataset_name,
            target_column=column,
            description=f"Changed datatype of '{column}' from {orig_type} to String",
            parameters={"column": column, "old_type": orig_type, "new_type": "String"},
            ground_truth={"column": column, "old_type": orig_type, "new_type": "String"},
        )
        return corrupted_df, scenario

    # ── 7. Range Violation ────────────────────────────────────────────
    def inject_range_violation(
        self,
        df: pl.DataFrame,
        column: str,
        fraction: float = 0.20,
        factor: float = 20.0,
        dataset_name: str = "dataset",
    ) -> tuple[pl.DataFrame, FailureScenario]:
        """Corrupt a subset of numeric values with extreme out-of-range values."""
        n = df.height
        k = max(1, int(n * fraction))
        indices = self.rng.choice(n, size=k, replace=False)
        mask = np.zeros(n, dtype=bool)
        mask[indices] = True

        orig_col = df[column]
        corrupted_vals = orig_col * factor
        new_col = pl.when(pl.Series(mask)).then(corrupted_vals).otherwise(orig_col).alias(column)
        corrupted_df = df.with_columns(new_col)

        scenario = FailureScenario(
            scenario_id=f"range_violation_{self.seed:03d}",
            scenario_type="range_violation",
            root_cause=RootCauseType.TRANSFORMATION_ERROR,
            severity=Severity.HIGH,
            target_dataset=dataset_name,
            target_column=column,
            description=f"Injected extreme values into '{column}' multiplied by {factor}",
            parameters={"column": column, "factor": factor, "fraction": fraction},
            ground_truth={"corrupted_count": k, "column": column},
        )
        return corrupted_df, scenario

    # ── 8. Categorical Corruption ─────────────────────────────────────
    def inject_categorical_corruption(
        self,
        df: pl.DataFrame,
        column: str,
        corrupted_value: str = "ILLEGAL_STATUS_OVERFLOW",
        fraction: float = 0.15,
        dataset_name: str = "dataset",
    ) -> tuple[pl.DataFrame, FailureScenario]:
        """Inject an unallowed categorical value into a discrete domain column."""
        n = df.height
        k = max(1, int(n * fraction))
        indices = self.rng.choice(n, size=k, replace=False)
        mask = np.zeros(n, dtype=bool)
        mask[indices] = True

        orig_col = df[column]
        new_col = (
            pl.when(pl.Series(mask)).then(pl.lit(corrupted_value)).otherwise(orig_col).alias(column)
        )
        corrupted_df = df.with_columns(new_col)

        scenario = FailureScenario(
            scenario_id=f"categorical_corruption_{self.seed:03d}",
            scenario_type="categorical_corruption",
            root_cause=RootCauseType.SOURCE_DATA_CHANGE,
            severity=Severity.HIGH,
            target_dataset=dataset_name,
            target_column=column,
            description=f"Injected invalid categorical value '{corrupted_value}' into column '{column}'",
            parameters={"column": column, "corrupted_value": corrupted_value, "fraction": fraction},
            ground_truth={"corrupted_count": k, "corrupted_value": corrupted_value},
        )
        return corrupted_df, scenario

    # ── 9. Distribution Shift ─────────────────────────────────────────
    def inject_distribution_shift(
        self,
        df: pl.DataFrame,
        column: str,
        shift_mean: float = 40.0,
        dataset_name: str = "dataset",
    ) -> tuple[pl.DataFrame, FailureScenario]:
        """Shift the mean and variance of a continuous distribution."""
        orig_col = df[column]
        shifted_col = (orig_col + shift_mean).alias(column)
        corrupted_df = df.with_columns(shifted_col)

        scenario = FailureScenario(
            scenario_id=f"distribution_shift_{self.seed:03d}",
            scenario_type="distribution_shift",
            root_cause=RootCauseType.DISTRIBUTION_SHIFT,
            severity=Severity.MEDIUM,
            target_dataset=dataset_name,
            target_column=column,
            description=f"Shifted distribution of '{column}' by +{shift_mean}",
            parameters={"column": column, "shift_mean": shift_mean},
            ground_truth={"shift_mean": shift_mean, "column": column},
        )
        return corrupted_df, scenario

    # ── 10. Timezone Shift ────────────────────────────────────────────
    def inject_timezone_shift(
        self,
        df: pl.DataFrame,
        column: str,
        offset_hours: int = -5,
        dataset_name: str = "dataset",
    ) -> tuple[pl.DataFrame, FailureScenario]:
        """Shift timestamps by a fixed offset simulating unhandled timezone translation."""
        orig_col = df[column]
        shifted_col = (orig_col + timedelta(hours=offset_hours)).alias(column)
        corrupted_df = df.with_columns(shifted_col)

        scenario = FailureScenario(
            scenario_id=f"timezone_shift_{self.seed:03d}",
            scenario_type="timezone_shift",
            root_cause=RootCauseType.TIMEZONE_MISMATCH,
            severity=Severity.HIGH,
            target_dataset=dataset_name,
            target_column=column,
            description=f"Shifted timestamps in '{column}' by {offset_hours} hours",
            parameters={"column": column, "offset_hours": offset_hours},
            ground_truth={"offset_hours": offset_hours, "column": column},
        )
        return corrupted_df, scenario

    # ── 11. Late Arrival ──────────────────────────────────────────────
    def inject_late_arrival(
        self,
        df: pl.DataFrame,
        column: str,
        fraction: float = 0.25,
        delay_days: int = 14,
        dataset_name: str = "dataset",
    ) -> tuple[pl.DataFrame, FailureScenario]:
        """Simulate delayed partition ingestion by backdating recent transactions."""
        n = df.height
        k = max(1, int(n * fraction))
        indices = self.rng.choice(n, size=k, replace=False)
        mask = np.zeros(n, dtype=bool)
        mask[indices] = True

        orig_col = df[column]
        delayed = orig_col - timedelta(days=delay_days)
        new_col = pl.when(pl.Series(mask)).then(delayed).otherwise(orig_col).alias(column)
        corrupted_df = df.with_columns(new_col)

        scenario = FailureScenario(
            scenario_id=f"late_arrival_{self.seed:03d}",
            scenario_type="late_arrival",
            root_cause=RootCauseType.LATE_ARRIVAL,
            severity=Severity.MEDIUM,
            target_dataset=dataset_name,
            target_column=column,
            description=f"Delayed arrival: {k} records backdated by {delay_days} days in '{column}'",
            parameters={"column": column, "delay_days": delay_days, "fraction": fraction},
            ground_truth={"delayed_records": k, "delay_days": delay_days},
        )
        return corrupted_df, scenario

    # ── 12. Upstream Failure ──────────────────────────────────────────
    def inject_upstream_failure(
        self,
        upstream_df: pl.DataFrame,
        downstream_df: pl.DataFrame,
        upstream_key: str,
        downstream_key: str,
        upstream_name: str = "customers",
        downstream_name: str = "transactions",
    ) -> tuple[pl.DataFrame, pl.DataFrame, FailureScenario]:
        """Truncate upstream table causing massive foreign-key referential integrity breakage downstream."""
        # Truncate 80% of upstream
        keep = max(1, int(upstream_df.height * 0.2))
        corrupted_upstream = upstream_df.head(keep)

        scenario = FailureScenario(
            scenario_id=f"upstream_failure_{self.seed:03d}",
            scenario_type="upstream_failure",
            root_cause=RootCauseType.UPSTREAM_FAILURE,
            severity=Severity.CRITICAL,
            target_dataset=upstream_name,
            description=f"Upstream dataset '{upstream_name}' failed to produce 80% of records",
            parameters={"upstream": upstream_name, "downstream": downstream_name},
            ground_truth={
                "upstream_kept_rows": keep,
                "original_upstream_rows": upstream_df.height,
                "impacted_downstream": downstream_name,
            },
        )
        return corrupted_upstream, downstream_df, scenario

    # ── 13. Mixed Failure ─────────────────────────────────────────────
    def inject_mixed_failure(
        self,
        df: pl.DataFrame,
        numeric_column: str,
        categorical_column: str,
        dataset_name: str = "dataset",
    ) -> tuple[pl.DataFrame, FailureScenario]:
        """Combine multiple simultaneous anomalies: range violation + categorical corruption + nulls."""
        # 1. Null spike
        df_step1, _ = self.inject_null_spike(df, numeric_column, null_fraction=0.25)
        # 2. Categorical corruption
        df_step2, _ = self.inject_categorical_corruption(
            df_step1, categorical_column, corrupted_value="MALFORMED_INPUT", fraction=0.15
        )
        # 3. Add unexpected schema column
        df_step3, _ = self.inject_schema_addition(df_step2, new_column="err_traceback")

        scenario = FailureScenario(
            scenario_id=f"mixed_failure_{self.seed:03d}",
            scenario_type="mixed_failure",
            root_cause=RootCauseType.TRANSFORMATION_ERROR,
            severity=Severity.CRITICAL,
            target_dataset=dataset_name,
            description=f"Multiple compound failures injected into {dataset_name}",
            ground_truth={
                "components": ["null_spike", "categorical_corruption", "schema_addition"]
            },
        )
        return df_step3, scenario
