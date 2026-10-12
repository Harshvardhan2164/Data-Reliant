"""Plugin registry and abstract base class for data quality rules."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Type

import polars as pl

from datareliant.common.exceptions import QualityRuleError
from datareliant.common.types import Severity, Status
from datareliant.quality.models import QualityResult, QualityRuleConfig


class QualityContext:
    """Execution context containing reference datasets and metadata."""

    def __init__(
        self,
        reference_datasets: dict[str, pl.DataFrame] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.reference_datasets = reference_datasets or {}
        self.metadata = metadata or {}


class BaseQualityRule(ABC):
    """Abstract base class for all pluggable quality rules."""

    rule_type: str = "base"

    def __init__(self, config: QualityRuleConfig) -> None:
        self.config = config

    def execute(self, df: pl.DataFrame, context: QualityContext | None = None) -> QualityResult:
        """Execute the rule and track execution duration in milliseconds."""
        ctx = context or QualityContext()
        start = time.perf_counter()
        try:
            result = self._evaluate(df, ctx)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000.0
            return QualityResult(
                rule_id=self.config.id,
                rule_name=self.config.name,
                rule_type=self.config.type,
                dataset=self.config.dataset,
                column=self.config.column,
                execution_time_ms=round(duration_ms, 3),
                status=Status.ERROR,
                severity=self.config.severity,
                expected="Rule execution without exception",
                actual=f"Exception: {exc}",
                failure_percentage=100.0,
                evidence={"exception": str(exc)},
            )

        duration_ms = (time.perf_counter() - start) * 1000.0
        result.execution_time_ms = round(duration_ms, 3)
        return result

    @abstractmethod
    def _evaluate(self, df: pl.DataFrame, context: QualityContext) -> QualityResult:
        """Internal evaluation logic to be implemented by concrete rules."""
        raise NotImplementedError


class RuleRegistry:
    """Plugin registry for dynamically registering and retrieving quality rules."""

    _registry: dict[str, Type[BaseQualityRule]] = {}

    @classmethod
    def register(cls, rule_type: str) -> Callable[[Type[BaseQualityRule]], Type[BaseQualityRule]]:
        """Decorator to register a rule class with a given type string."""

        def decorator(subclass: Type[BaseQualityRule]) -> Type[BaseQualityRule]:
            cls._registry[rule_type.lower()] = subclass
            subclass.rule_type = rule_type.lower()
            return subclass

        return decorator

    @classmethod
    def get(cls, rule_type: str) -> Type[BaseQualityRule]:
        """Retrieve the rule class for a given type string."""
        key = rule_type.lower()
        if key not in cls._registry:
            raise QualityRuleError(
                f"Unknown quality rule type '{rule_type}'. Available types: {list(cls._registry.keys())}",
                details={"requested_type": rule_type, "available_types": list(cls._registry.keys())},
            )
        return cls._registry[key]

    @classmethod
    def create(cls, config: QualityRuleConfig) -> BaseQualityRule:
        """Instantiate a rule object from its configuration."""
        rule_cls = cls.get(config.type)
        return rule_cls(config)

    @classmethod
    def available_rules(cls) -> list[str]:
        """Return list of all registered rule types."""
        return sorted(list(cls._registry.keys()))
