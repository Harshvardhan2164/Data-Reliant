"""Quality rule execution engine and YAML suite loader."""

from __future__ import annotations

import time
import uuid
from pathlib import Path

import polars as pl
import yaml

import datareliant.quality.rules  # noqa: F401 - ensures all rules are registered
from datareliant.common.types import Severity, Status
from datareliant.quality.base import QualityContext, RuleRegistry
from datareliant.quality.models import (
    QualityResult,
    QualityRuleConfig,
    QualityRunSummary,
    QualitySuiteConfig,
)


class QualityEngine:
    """Orchestrates quality rule evaluations and suite executions."""

    def __init__(self) -> None:
        pass

    def run_rule(
        self,
        df: pl.DataFrame,
        config: QualityRuleConfig,
        context: QualityContext | None = None,
    ) -> QualityResult:
        """Execute a single quality rule."""
        rule = RuleRegistry.create(config)
        return rule.execute(df, context)

    def run_suite(
        self,
        df: pl.DataFrame,
        suite: QualitySuiteConfig,
        dataset_name: str,
        version: int = 1,
        context: QualityContext | None = None,
    ) -> QualityRunSummary:
        """Execute a suite of rules against a DataFrame and compile a run summary."""
        ctx = context or QualityContext()
        start = time.perf_counter()
        run_id = str(uuid.uuid4())

        results: list[QualityResult] = []
        passed_count = 0
        failed_count = 0
        error_count = 0
        crit_count = 0
        high_count = 0

        for rule_cfg in suite.rules:
            if not rule_cfg.enabled:
                continue

            res = self.run_rule(df, rule_cfg, ctx)
            results.append(res)

            if res.status == Status.PASSED:
                passed_count += 1
            elif res.status == Status.FAILED:
                failed_count += 1
                if res.severity == Severity.CRITICAL:
                    crit_count += 1
                elif res.severity == Severity.HIGH:
                    high_count += 1
            elif res.status == Status.ERROR:
                error_count += 1

        duration_ms = (time.perf_counter() - start) * 1000.0

        return QualityRunSummary(
            run_id=run_id,
            dataset=dataset_name,
            version=version,
            total_rules=len(results),
            passed_rules=passed_count,
            failed_rules=failed_count,
            error_rules=error_count,
            critical_failures=crit_count,
            high_failures=high_count,
            total_duration_ms=round(duration_ms, 3),
            results=results,
        )

    @staticmethod
    def load_suite_from_yaml(path_or_content: Path | str) -> QualitySuiteConfig:
        """Parse a YAML configuration into a QualitySuiteConfig."""
        if isinstance(path_or_content, Path) or (
            isinstance(path_or_content, str)
            and "\n" not in path_or_content
            and Path(path_or_content).exists()
        ):
            path = Path(path_or_content)
            content = path.read_text(encoding="utf-8")
        else:
            content = str(path_or_content)

        parsed = yaml.safe_load(content)
        if not isinstance(parsed, dict):
            return QualitySuiteConfig()

        name = parsed.get("name", "suite")
        desc = parsed.get("description")
        rule_list: list[QualityRuleConfig] = []

        for r in parsed.get("rules", []):
            rule_list.append(QualityRuleConfig(**r))

        return QualitySuiteConfig(name=name, description=desc, rules=rule_list)
