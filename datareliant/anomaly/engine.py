"""Anomaly detection engine coordinating statistical detectors and distribution shifts."""

from __future__ import annotations

from typing import Any

import numpy as np

import datareliant.anomaly.detectors  # noqa: F401 - ensures detectors are registered
from datareliant.anomaly.base import DetectorRegistry
from datareliant.anomaly.detectors import DistributionShiftDetector
from datareliant.anomaly.models import AnomalyResult, DistributionShiftResult


class AnomalyEngine:
    """Central engine for statistical anomaly detection and distribution drift."""

    def __init__(self) -> None:
        self.shift_detector = DistributionShiftDetector()

    def detect(
        self,
        history: list[float] | np.ndarray,
        current: float,
        detector: str = "robust_zscore",
        metric_name: str = "metric",
        dataset_name: str | None = None,
        node_id: str | None = None,
        **parameters: Any,
    ) -> AnomalyResult:
        """Run a single anomaly detector on a historical series and current observed point."""
        det = DetectorRegistry.create(detector, **parameters)
        return det.fit_detect(
            history=history,
            current=current,
            metric_name=metric_name,
            dataset_name=dataset_name,
            node_id=node_id,
        )

    def detect_multi(
        self,
        history: list[float] | np.ndarray,
        current: float,
        detectors: list[str] | None = None,
        metric_name: str = "metric",
        dataset_name: str | None = None,
        node_id: str | None = None,
    ) -> list[AnomalyResult]:
        """Run multiple detectors in parallel on the same metric point."""
        chosen = detectors or ["zscore", "robust_zscore", "iqr"]
        results = []
        for d in chosen:
            res = self.detect(
                history=history,
                current=current,
                detector=d,
                metric_name=metric_name,
                dataset_name=dataset_name,
                node_id=node_id,
            )
            results.append(res)
        return results

    def detect_distribution_shift(
        self,
        baseline: list[float] | np.ndarray,
        observed: list[float] | np.ndarray,
        method: str = "ks_test",
        metric_name: str = "metric",
        dataset_name: str | None = None,
        **parameters: Any,
    ) -> DistributionShiftResult:
        """Evaluate whether an observed data sample exhibits distribution drift compared to baseline."""
        m = method.lower()
        if m in ("ks", "ks_test", "kolmogorov_smirnov"):
            p_threshold = parameters.get("p_threshold", 0.05)
            return self.shift_detector.kolmogorov_smirnov(
                baseline=baseline,
                observed=observed,
                p_threshold=p_threshold,
                metric_name=metric_name,
                dataset_name=dataset_name,
            )
        elif m in ("jsd", "jensen_shannon", "js"):
            threshold = parameters.get("threshold", 0.25)
            bins = parameters.get("bins", 20)
            return self.shift_detector.jensen_shannon(
                baseline=baseline,
                observed=observed,
                threshold=threshold,
                bins=bins,
                metric_name=metric_name,
                dataset_name=dataset_name,
            )
        elif m in ("psi", "population_stability_index"):
            threshold = parameters.get("threshold", 0.25)
            bins = parameters.get("bins", 10)
            return self.shift_detector.population_stability_index(
                baseline=baseline,
                observed=observed,
                threshold=threshold,
                bins=bins,
                metric_name=metric_name,
                dataset_name=dataset_name,
            )
        else:
            raise ValueError(f"Unknown distribution shift method '{method}'")
