"""Quality service for managing rule executions and database persistence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from datareliant.common.exceptions import QualityRunNotFoundError
from datareliant.common.models import QualityResultModel, QualityRuleModel
from datareliant.ingestion.service import IngestionService
from datareliant.quality.engine import QualityEngine
from datareliant.quality.models import (
    QualityRuleConfig,
    QualityRunSummary,
    QualitySuiteConfig,
)


class QualityService:
    """Service orchestrating quality runs and persisting standardized QualityResults."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session
        self.engine = QualityEngine()
        self.ingestion = IngestionService(session)
        self.rules_dir = Path("configs/quality_rules")

    async def execute_quality_run(
        self,
        dataset_id: str,
        version: int | None = None,
        suite: QualitySuiteConfig | None = None,
    ) -> QualityRunSummary:
        """Run quality rules on a dataset version and persist results."""
        dataset = await self.ingestion.get_dataset(dataset_id)
        ver_model, df = await self.ingestion.load_version_dataframe(dataset_id, version=version)

        # Determine suite
        if suite is None:
            suite_file = self.rules_dir / f"{dataset.name}.yaml"
            if suite_file.exists():
                suite = self.engine.load_suite_from_yaml(suite_file)
            else:
                # Default baseline rules: not-null on all columns, row_count > 0
                baseline_rules = [
                    QualityRuleConfig(
                        name="baseline_row_count",
                        type="row_count",
                        dataset=dataset.name,
                        parameters={"min_rows": 1},
                    )
                ]
                for col in df.columns:
                    baseline_rules.append(
                        QualityRuleConfig(
                            name=f"{col}_not_null",
                            type="not_null",
                            dataset=dataset.name,
                            column=col,
                        )
                    )
                suite = QualitySuiteConfig(
                    name=f"{dataset.name}_baseline",
                    rules=baseline_rules,
                )

        summary = self.engine.run_suite(
            df=df,
            suite=suite,
            dataset_name=dataset.name,
            version=ver_model.version,
        )

        # Persist results if database session is present
        if self.session is not None:
            for res in summary.results:
                # Ensure rule definition exists in database
                rule_stmt = select(QualityRuleModel).where(QualityRuleModel.name == res.rule_name)
                rule_res = await self.session.execute(rule_stmt)
                rule_row = rule_res.scalar_one_or_none()
                if rule_row is None:
                    rule_row = QualityRuleModel(
                        id=res.rule_id,
                        name=res.rule_name,
                        rule_type=res.rule_type,
                        dataset_name=dataset.name,
                        column=res.column,
                        severity=res.severity,
                        parameters={},
                        enabled=True,
                    )
                    self.session.add(rule_row)
                    await self.session.flush()

                # Add quality result
                result_row = QualityResultModel(
                    rule_id=rule_row.id,
                    run_id=summary.run_id,
                    dataset_name=dataset.name,
                    column=res.column,
                    status=res.status,
                    severity=res.severity.value,
                    expected=res.expected,
                    actual=res.actual,
                    failure_percentage=res.failure_percentage,
                    evidence=res.evidence,
                    metadata_={"failure_count": res.failure_count, "total": res.total_evaluated},
                    execution_time_ms=res.execution_time_ms,
                )
                self.session.add(result_row)

            await self.session.flush()

        return summary

    async def get_run_results(self, run_id: str) -> dict[str, Any]:
        """Fetch all results associated with a run ID."""
        if self.session is None:
            raise QualityRunNotFoundError("Database session required")

        stmt = (
            select(QualityResultModel)
            .where(QualityResultModel.run_id == run_id)
            .order_by(QualityResultModel.created_at.asc())
        )
        res = await self.session.execute(stmt)
        rows = list(res.scalars().all())
        if not rows:
            raise QualityRunNotFoundError(f"Quality run with ID '{run_id}' not found")

        results = []
        for r in rows:
            results.append(
                {
                    "id": r.id,
                    "rule_id": r.rule_id,
                    "run_id": r.run_id,
                    "dataset_name": r.dataset_name,
                    "column": r.column,
                    "status": r.status.value if hasattr(r.status, "value") else str(r.status),
                    "severity": r.severity,
                    "expected": r.expected,
                    "actual": r.actual,
                    "failure_percentage": r.failure_percentage,
                    "evidence": r.evidence,
                    "execution_time_ms": r.execution_time_ms,
                    "created_at": r.created_at.isoformat(),
                }
            )

        return {
            "run_id": run_id,
            "dataset": rows[0].dataset_name,
            "total_checks": len(results),
            "results": results,
        }
