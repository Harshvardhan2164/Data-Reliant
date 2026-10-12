"""Base classes and plugin registry for anomaly detection."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Type

import numpy as np

from datareliant.anomaly.models import AnomalyResult
from datareliant.common.exceptions import DetectorNotFoundError


class BaseAnomalyDetector(ABC):
    """Abstract base class for all statistical anomaly detectors."""

    detector_name: str = "base"

    def __init__(self, **parameters: Any) -> None:
        self.parameters = parameters

    @abstractmethod
    def fit_detect(
        self,
        history: list[float] | np.ndarray,
        current: float,
        metric_name: str = "metric",
        dataset_name: str | None = None,
        node_id: str | None = None,
    ) -> AnomalyResult:
        """Fit baseline on history and evaluate whether current is anomalous."""
        raise NotImplementedError


class DetectorRegistry:
    """Pluggable registry for anomaly detectors."""

    _registry: dict[str, Type[BaseAnomalyDetector]] = {}

    @classmethod
    def register(cls, name: str) -> Callable[[Type[BaseAnomalyDetector]], Type[BaseAnomalyDetector]]:
        """Decorator to register a detector class."""

        def decorator(subclass: Type[BaseAnomalyDetector]) -> Type[BaseAnomalyDetector]:
            cls._registry[name.lower()] = subclass
            subclass.detector_name = name.lower()
            return subclass

        return decorator

    @classmethod
    def get(cls, name: str) -> Type[BaseAnomalyDetector]:
        """Fetch detector class by name."""
        key = name.lower()
        if key not in cls._registry:
            raise DetectorNotFoundError(
                f"Anomaly detector '{name}' not found. Available: {list(cls._registry.keys())}",
                details={"requested": name, "available": list(cls._registry.keys())},
            )
        return cls._registry[key]

    @classmethod
    def create(cls, name: str, **parameters: Any) -> BaseAnomalyDetector:
        """Instantiate detector by name."""
        return cls.get(name)(**parameters)

    @classmethod
    def available_detectors(cls) -> list[str]:
        """Return sorted list of registered detectors."""
        return sorted(list(cls._registry.keys()))
