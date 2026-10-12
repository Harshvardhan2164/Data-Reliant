"""Implementations of all 10 core Data Quality Rules."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import polars as pl

from datareliant.common.types import Status
from datareliant.quality.base import BaseQualityRule, QualityContext, RuleRegistry
from datareliant.quality.models import QualityResult


# ── 1. Not Null Rule ─────────────────────────────────────────────────


@RuleRegistry.register("not_null")
class NotNullRule(BaseQualityRule):
    """Verifies that a column contains no null values, or within an allowed tolerance."""

    def _evaluate(self, df: pl.DataFrame, context: QualityContext) -> QualityResult:
        col = self.config.column
        if not col or col not in df.columns:
            return QualityResult(
                rule_id=self.config.id,
                rule_name=self.config.name,
                rule_type=self.config.type,
                dataset=self.config.dataset,
                column=col,
                execution_time_ms=0.0,
                status=Status.FAILED,
                severity=self.config.severity,
                expected=f"Column '{col}' exists in dataset",
                actual="Column missing",
                failure_percentage=100.0,
            )

        total_rows = df.height
        null_count = df[col].null_count()
        fail_pct = (null_count / max(total_rows, 1)) * 100.0
        max_allowed_pct = float(self.config.parameters.get("max_null_percentage", 0.0))

        passed = fail_pct <= max_allowed_pct
        return QualityResult(
            rule_id=self.config.id,
            rule_name=self.config.name,
            rule_type=self.config.type,
            dataset=self.config.dataset,
            column=col,
            execution_time_ms=0.0,
            status=Status.PASSED if passed else Status.FAILED,
            severity=self.config.severity,
            expected=f"Null percentage <= {max_allowed_pct}%",
            actual=f"{null_count} nulls ({round(fail_pct, 3)}%)",
            failure_percentage=round(fail_pct, 4),
            failure_count=null_count,
            total_evaluated=total_rows,
            evidence={"null_count": null_count, "total_rows": total_rows},
        )


# ── 2. Uniqueness Rule ───────────────────────────────────────────────


@RuleRegistry.register("uniqueness")
class UniquenessRule(BaseQualityRule):
    """Verifies that values in a column are unique."""

    def _evaluate(self, df: pl.DataFrame, context: QualityContext) -> QualityResult:
        col = self.config.column
        if not col or col not in df.columns:
            return QualityResult(
                rule_id=self.config.id,
                rule_name=self.config.name,
                rule_type=self.config.type,
                dataset=self.config.dataset,
                column=col,
                execution_time_ms=0.0,
                status=Status.FAILED,
                severity=self.config.severity,
                expected=f"Column '{col}' exists",
                actual="Column missing",
                failure_percentage=100.0,
            )

        total = df.height
        series = df[col].drop_nulls()
        unique_count = series.n_unique()
        non_null_count = series.len()
        duplicate_count = max(0, non_null_count - unique_count)
        fail_pct = (duplicate_count / max(total, 1)) * 100.0
        max_allowed_pct = float(self.config.parameters.get("max_duplicate_percentage", 0.0))

        passed = fail_pct <= max_allowed_pct
        return QualityResult(
            rule_id=self.config.id,
            rule_name=self.config.name,
            rule_type=self.config.type,
            dataset=self.config.dataset,
            column=col,
            execution_time_ms=0.0,
            status=Status.PASSED if passed else Status.FAILED,
            severity=self.config.severity,
            expected=f"Duplicate percentage <= {max_allowed_pct}%",
            actual=f"{duplicate_count} duplicates ({round(fail_pct, 3)}%)",
            failure_percentage=round(fail_pct, 4),
            failure_count=duplicate_count,
            total_evaluated=total,
            evidence={
                "unique_count": unique_count,
                "duplicate_count": duplicate_count,
            },
        )


# ── 3. Duplicate Rows Rule ───────────────────────────────────────────


@RuleRegistry.register("duplicate_rows")
class DuplicateRowsRule(BaseQualityRule):
    """Verifies that dataset has no duplicate rows across all or a subset of columns."""

    def _evaluate(self, df: pl.DataFrame, context: QualityContext) -> QualityResult:
        subset = self.config.parameters.get("subset")
        total = df.height
        if total == 0:
            return QualityResult(
                rule_id=self.config.id,
                rule_name=self.config.name,
                rule_type=self.config.type,
                dataset=self.config.dataset,
                execution_time_ms=0.0,
                status=Status.PASSED,
                severity=self.config.severity,
                expected="0 duplicate rows",
                actual="0 rows",
            )

        if subset and isinstance(subset, list):
            valid_cols = [c for c in subset if c in df.columns]
            unique_rows = df.select(valid_cols).unique().height
        else:
            unique_rows = df.unique().height

        dups = max(0, total - unique_rows)
        fail_pct = (dups / total) * 100.0
        max_allowed_pct = float(self.config.parameters.get("max_duplicate_percentage", 0.0))

        passed = fail_pct <= max_allowed_pct
        return QualityResult(
            rule_id=self.config.id,
            rule_name=self.config.name,
            rule_type=self.config.type,
            dataset=self.config.dataset,
            execution_time_ms=0.0,
            status=Status.PASSED if passed else Status.FAILED,
            severity=self.config.severity,
            expected=f"Duplicate row percentage <= {max_allowed_pct}%",
            actual=f"{dups} duplicate rows ({round(fail_pct, 3)}%)",
            failure_percentage=round(fail_pct, 4),
            failure_count=dups,
            total_evaluated=total,
            evidence={"duplicate_rows": dups, "unique_rows": unique_rows},
        )


# ── 4. Range Rule ────────────────────────────────────────────────────


@RuleRegistry.register("range")
class RangeRule(BaseQualityRule):
    """Verifies that numerical or date values fall within [min, max] boundaries."""

    def _evaluate(self, df: pl.DataFrame, context: QualityContext) -> QualityResult:
        col = self.config.column
        if not col or col not in df.columns:
            return QualityResult(
                rule_id=self.config.id,
                rule_name=self.config.name,
                rule_type=self.config.type,
                dataset=self.config.dataset,
                column=col,
                execution_time_ms=0.0,
                status=Status.FAILED,
                severity=self.config.severity,
                expected=f"Column '{col}' exists",
                actual="Column missing",
                failure_percentage=100.0,
            )

        min_val = self.config.parameters.get("min")
        max_val = self.config.parameters.get("max")
        series = df[col].drop_nulls()
        total = series.len()

        if total == 0:
            return QualityResult(
                rule_id=self.config.id,
                rule_name=self.config.name,
                rule_type=self.config.type,
                dataset=self.config.dataset,
                column=col,
                execution_time_ms=0.0,
                status=Status.PASSED,
                severity=self.config.severity,
                expected=f"Values between {min_val} and {max_val}",
                actual="0 non-null values evaluated",
            )

        violations = 0
        if min_val is not None and max_val is not None:
            cond = (series < min_val) | (series > max_val)
            violations = series.filter(cond).len()
        elif min_val is not None:
            violations = series.filter(series < min_val).len()
        elif max_val is not None:
            violations = series.filter(series > max_val).len()

        fail_pct = (violations / total) * 100.0
        passed = violations == 0

        return QualityResult(
            rule_id=self.config.id,
            rule_name=self.config.name,
            rule_type=self.config.type,
            dataset=self.config.dataset,
            column=col,
            execution_time_ms=0.0,
            status=Status.PASSED if passed else Status.FAILED,
            severity=self.config.severity,
            expected=f"Values within [{min_val}, {max_val}]",
            actual=f"{violations} out-of-range values ({round(fail_pct, 2)}%)",
            failure_percentage=round(fail_pct, 4),
            failure_count=violations,
            total_evaluated=total,
            evidence={"min_bound": min_val, "max_bound": max_val, "violations": violations},
        )


# ── 5. Categorical Values Rule ───────────────────────────────────────


@RuleRegistry.register("categorical_values")
class CategoricalValuesRule(BaseQualityRule):
    """Verifies that categorical values belong to an allowed set."""

    def _evaluate(self, df: pl.DataFrame, context: QualityContext) -> QualityResult:
        col = self.config.column
        if not col or col not in df.columns:
            return QualityResult(
                rule_id=self.config.id,
                rule_name=self.config.name,
                rule_type=self.config.type,
                dataset=self.config.dataset,
                column=col,
                execution_time_ms=0.0,
                status=Status.FAILED,
                severity=self.config.severity,
                expected=f"Column '{col}' exists",
                actual="Column missing",
                failure_percentage=100.0,
            )

        allowed = set(self.config.parameters.get("allowed_values", []))
        series = df[col].drop_nulls()
        total = series.len()

        # Find rows not in allowed set
        violations = series.filter(~series.is_in(list(allowed)))
        viol_count = violations.len()
        fail_pct = (viol_count / max(total, 1)) * 100.0

        unexpected_samples = [str(x) for x in violations.unique().head(5).to_list()]
        passed = viol_count == 0

        return QualityResult(
            rule_id=self.config.id,
            rule_name=self.config.name,
            rule_type=self.config.type,
            dataset=self.config.dataset,
            column=col,
            execution_time_ms=0.0,
            status=Status.PASSED if passed else Status.FAILED,
            severity=self.config.severity,
            expected=f"Values in {sorted(list(allowed))}",
            actual=f"{viol_count} unexpected values (e.g. {unexpected_samples})",
            failure_percentage=round(fail_pct, 4),
            failure_count=viol_count,
            total_evaluated=total,
            evidence={"allowed_values": list(allowed), "unexpected_samples": unexpected_samples},
        )


# ── 6. Schema Rule ───────────────────────────────────────────────────


@RuleRegistry.register("schema")
class SchemaRule(BaseQualityRule):
    """Verifies expected columns and optionally data types."""

    def _evaluate(self, df: pl.DataFrame, context: QualityContext) -> QualityResult:
        expected_cols = self.config.parameters.get("expected_columns", [])
        expected_types = self.config.parameters.get("expected_types", {})

        actual_cols = set(df.columns)
        missing_cols = [c for c in expected_cols if c not in actual_cols]

        mismatched_types: dict[str, dict[str, str]] = {}
        for col, exp_type in expected_types.items():
            if col in df.columns:
                actual_type = str(df[col].dtype)
                if exp_type.lower() not in actual_type.lower():
                    mismatched_types[col] = {"expected": exp_type, "actual": actual_type}

        passed = len(missing_cols) == 0 and len(mismatched_types) == 0
        fail_pct = (
            ((len(missing_cols) + len(mismatched_types)) / max(len(expected_cols), 1)) * 100.0
            if not passed
            else 0.0
        )

        return QualityResult(
            rule_id=self.config.id,
            rule_name=self.config.name,
            rule_type=self.config.type,
            dataset=self.config.dataset,
            execution_time_ms=0.0,
            status=Status.PASSED if passed else Status.FAILED,
            severity=self.config.severity,
            expected=f"Columns: {expected_cols}, Types: {expected_types}",
            actual=f"Missing: {missing_cols}, Type mismatches: {mismatched_types}",
            failure_percentage=round(fail_pct, 4),
            failure_count=len(missing_cols) + len(mismatched_types),
            total_evaluated=len(expected_cols),
            evidence={"missing_columns": missing_cols, "type_mismatches": mismatched_types},
        )


# ── 7. Freshness Rule ────────────────────────────────────────────────


@RuleRegistry.register("freshness")
class FreshnessRule(BaseQualityRule):
    """Verifies that the most recent timestamp in a column is within max_age limit."""

    def _evaluate(self, df: pl.DataFrame, context: QualityContext) -> QualityResult:
        col = self.config.column
        if not col or col not in df.columns:
            return QualityResult(
                rule_id=self.config.id,
                rule_name=self.config.name,
                rule_type=self.config.type,
                dataset=self.config.dataset,
                column=col,
                execution_time_ms=0.0,
                status=Status.FAILED,
                severity=self.config.severity,
                expected=f"Timestamp column '{col}' exists",
                actual="Column missing",
                failure_percentage=100.0,
            )

        max_age_sec = float(
            self.config.parameters.get(
                "max_age_seconds", self.config.parameters.get("max_age_hours", 24) * 3600
            )
        )
        series = df[col].drop_nulls()
        if series.len() == 0:
            return QualityResult(
                rule_id=self.config.id,
                rule_name=self.config.name,
                rule_type=self.config.type,
                dataset=self.config.dataset,
                column=col,
                execution_time_ms=0.0,
                status=Status.FAILED,
                severity=self.config.severity,
                expected=f"Timestamp age <= {max_age_sec}s",
                actual="Column is empty",
                failure_percentage=100.0,
            )

        max_ts = series.max()
        # Calculate age
        try:
            if isinstance(max_ts, datetime):
                if max_ts.tzinfo is None:
                    max_ts = max_ts.replace(tzinfo=timezone.utc)
                age_sec = (datetime.now(timezone.utc) - max_ts).total_seconds()
            else:
                # String conversion attempt
                parsed = datetime.fromisoformat(str(max_ts))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                age_sec = (datetime.now(timezone.utc) - parsed).total_seconds()
        except Exception:
            age_sec = 0.0

        passed = age_sec <= max_age_sec
        return QualityResult(
            rule_id=self.config.id,
            rule_name=self.config.name,
            rule_type=self.config.type,
            dataset=self.config.dataset,
            column=col,
            execution_time_ms=0.0,
            status=Status.PASSED if passed else Status.FAILED,
            severity=self.config.severity,
            expected=f"Data age <= {max_age_sec}s",
            actual=f"Latest timestamp is {str(max_ts)} (age: {round(age_sec, 1)}s)",
            failure_percentage=0.0 if passed else 100.0,
            evidence={"latest_timestamp": str(max_ts), "age_seconds": round(age_sec, 1)},
        )


# ── 8. Row Count Rule ────────────────────────────────────────────────


@RuleRegistry.register("row_count")
class RowCountRule(BaseQualityRule):
    """Verifies that dataset row count satisfies min, max, or exact constraints."""

    def _evaluate(self, df: pl.DataFrame, context: QualityContext) -> QualityResult:
        min_rows = self.config.parameters.get("min_rows")
        max_rows = self.config.parameters.get("max_rows")
        exact_rows = self.config.parameters.get("exact_rows")

        actual_rows = df.height
        passed = True
        expected_desc = []

        if exact_rows is not None:
            expected_desc.append(f"exactly {exact_rows} rows")
            if actual_rows != exact_rows:
                passed = False
        if min_rows is not None:
            expected_desc.append(f">= {min_rows} rows")
            if actual_rows < min_rows:
                passed = False
        if max_rows is not None:
            expected_desc.append(f"<= {max_rows} rows")
            if actual_rows > max_rows:
                passed = False

        expected_str = ", ".join(expected_desc) if expected_desc else "Valid row count"

        return QualityResult(
            rule_id=self.config.id,
            rule_name=self.config.name,
            rule_type=self.config.type,
            dataset=self.config.dataset,
            execution_time_ms=0.0,
            status=Status.PASSED if passed else Status.FAILED,
            severity=self.config.severity,
            expected=expected_str,
            actual=f"{actual_rows} rows",
            failure_percentage=0.0 if passed else 100.0,
            failure_count=0 if passed else 1,
            total_evaluated=actual_rows,
            evidence={"row_count": actual_rows},
        )


# ── 9. Referential Integrity Rule ────────────────────────────────────


@RuleRegistry.register("referential_integrity")
class ReferentialIntegrityRule(BaseQualityRule):
    """Verifies foreign key relationships between a child column and a parent table."""

    def _evaluate(self, df: pl.DataFrame, context: QualityContext) -> QualityResult:
        col = self.config.column
        parent_dataset = self.config.parameters.get("parent_dataset")
        parent_col = self.config.parameters.get("parent_column")

        if not col or col not in df.columns:
            return QualityResult(
                rule_id=self.config.id,
                rule_name=self.config.name,
                rule_type=self.config.type,
                dataset=self.config.dataset,
                column=col,
                execution_time_ms=0.0,
                status=Status.FAILED,
                severity=self.config.severity,
                expected=f"Column '{col}' exists",
                actual="Column missing",
                failure_percentage=100.0,
            )

        if not parent_dataset or parent_dataset not in context.reference_datasets:
            return QualityResult(
                rule_id=self.config.id,
                rule_name=self.config.name,
                rule_type=self.config.type,
                dataset=self.config.dataset,
                column=col,
                execution_time_ms=0.0,
                status=Status.FAILED,
                severity=self.config.severity,
                expected=f"Parent dataset '{parent_dataset}' available in context",
                actual=f"Parent dataset not found in reference context ({list(context.reference_datasets.keys())})",
                failure_percentage=100.0,
            )

        parent_df = context.reference_datasets[parent_dataset]
        if not parent_col or parent_col not in parent_df.columns:
            return QualityResult(
                rule_id=self.config.id,
                rule_name=self.config.name,
                rule_type=self.config.type,
                dataset=self.config.dataset,
                column=col,
                execution_time_ms=0.0,
                status=Status.FAILED,
                severity=self.config.severity,
                expected=f"Parent column '{parent_col}' exists in '{parent_dataset}'",
                actual="Parent column missing",
                failure_percentage=100.0,
            )

        child_values = df[col].drop_nulls()
        total_eval = child_values.len()
        parent_values_set = set(parent_df[parent_col].drop_nulls().to_list())

        # Check for orphan values
        orphans = child_values.filter(~child_values.is_in(list(parent_values_set)))
        orphan_count = orphans.len()
        fail_pct = (orphan_count / max(total_eval, 1)) * 100.0
        orphan_samples = [str(x) for x in orphans.unique().head(5).to_list()]

        passed = orphan_count == 0
        return QualityResult(
            rule_id=self.config.id,
            rule_name=self.config.name,
            rule_type=self.config.type,
            dataset=self.config.dataset,
            column=col,
            execution_time_ms=0.0,
            status=Status.PASSED if passed else Status.FAILED,
            severity=self.config.severity,
            expected=f"All values in {parent_dataset}.{parent_col}",
            actual=f"{orphan_count} orphan keys (e.g. {orphan_samples})",
            failure_percentage=round(fail_pct, 4),
            failure_count=orphan_count,
            total_evaluated=total_eval,
            evidence={"orphan_count": orphan_count, "orphan_samples": orphan_samples},
        )


# ── 10. Custom Expression Rule ───────────────────────────────────────


@RuleRegistry.register("custom_expression")
class CustomExpressionRule(BaseQualityRule):
    """Verifies that rows satisfy a custom SQL predicate expression evaluated with DuckDB/Polars SQL."""

    def _evaluate(self, df: pl.DataFrame, context: QualityContext) -> QualityResult:
        expression = self.config.parameters.get("expression")
        if not expression:
            return QualityResult(
                rule_id=self.config.id,
                rule_name=self.config.name,
                rule_type=self.config.type,
                dataset=self.config.dataset,
                execution_time_ms=0.0,
                status=Status.FAILED,
                severity=self.config.severity,
                expected="A non-empty 'expression' parameter",
                actual="Expression parameter missing",
                failure_percentage=100.0,
            )

        total_rows = df.height
        if total_rows == 0:
            return QualityResult(
                rule_id=self.config.id,
                rule_name=self.config.name,
                rule_type=self.config.type,
                dataset=self.config.dataset,
                execution_time_ms=0.0,
                status=Status.PASSED,
                severity=self.config.severity,
                expected=f"Condition '{expression}' satisfied",
                actual="0 rows",
            )

        # Execute expression in Polars SQL context
        sql_ctx = pl.SQLContext()
        table_name = "data_tbl"
        sql_ctx.register(table_name, df)
        query = f"SELECT COUNT(*) AS violations FROM {table_name} WHERE NOT ({expression})"

        try:
            res_df = sql_ctx.execute(query).collect()
            viol_count = int(res_df["violations"][0])
        except Exception as exc:
            return QualityResult(
                rule_id=self.config.id,
                rule_name=self.config.name,
                rule_type=self.config.type,
                dataset=self.config.dataset,
                execution_time_ms=0.0,
                status=Status.ERROR,
                severity=self.config.severity,
                expected=f"Valid SQL expression: {expression}",
                actual=f"Evaluation error: {exc}",
                failure_percentage=100.0,
                evidence={"error": str(exc)},
            )

        fail_pct = (viol_count / total_rows) * 100.0
        passed = viol_count == 0

        return QualityResult(
            rule_id=self.config.id,
            rule_name=self.config.name,
            rule_type=self.config.type,
            dataset=self.config.dataset,
            column=self.config.column,
            execution_time_ms=0.0,
            status=Status.PASSED if passed else Status.FAILED,
            severity=self.config.severity,
            expected=f"Condition '{expression}' satisfied",
            actual=f"{viol_count} rows violated condition ({round(fail_pct, 2)}%)",
            failure_percentage=round(fail_pct, 4),
            failure_count=viol_count,
            total_evaluated=total_rows,
            evidence={"expression": expression, "violations": viol_count},
        )
