"""Statistical, temporal, and ML-based anomaly detectors with pluggable registration."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import spatial, stats
from sklearn.ensemble import IsolationForest

from datareliant.anomaly.base import BaseAnomalyDetector, DetectorRegistry
from datareliant.anomaly.models import AnomalyResult, DistributionShiftResult
from datareliant.common.types import Severity


def _severity_from_score(score: float, threshold: float) -> Severity:
    """Map deviation ratio to severity levels."""
    ratio = score / max(threshold, 1e-9)
    if ratio >= 3.0:
        return Severity.CRITICAL
    elif ratio >= 2.0:
        return Severity.HIGH
    elif ratio >= 1.0:
        return Severity.MEDIUM
    return Severity.LOW


# ── 1. Z-Score Detector ──────────────────────────────────────────────


@DetectorRegistry.register("zscore")
@DetectorRegistry.register("z_score")
class ZScoreDetector(BaseAnomalyDetector):
    """Standard normal distribution Z-score detector."""

    def __init__(self, threshold: float = 3.0, **parameters: Any) -> None:
        super().__init__(**parameters)
        self.threshold = threshold

    def fit_detect(
        self,
        history: list[float] | np.ndarray,
        current: float,
        metric_name: str = "metric",
        dataset_name: str | None = None,
        node_id: str | None = None,
    ) -> AnomalyResult:
        arr = np.asarray(history, dtype=float)
        arr = arr[~np.isnan(arr)]

        if len(arr) < 3:
            return AnomalyResult(
                detector="zscore",
                dataset_name=dataset_name,
                node_id=node_id,
                metric=metric_name,
                baseline=float(np.mean(arr)) if len(arr) > 0 else None,
                observed=current,
                anomaly_score=0.0,
                threshold=self.threshold,
                is_anomaly=False,
                severity=Severity.LOW,
                evidence={"reason": "insufficient_history", "history_len": len(arr)},
            )

        mean = float(np.mean(arr))
        std = float(np.std(arr, ddof=1))

        if std < 1e-9:
            # Constant history
            is_anomaly = abs(current - mean) > 1e-9
            score = 10.0 if is_anomaly else 0.0
        else:
            score = float(abs(current - mean) / std)
            is_anomaly = score >= self.threshold

        return AnomalyResult(
            detector="zscore",
            dataset_name=dataset_name,
            node_id=node_id,
            metric=metric_name,
            baseline=mean,
            observed=current,
            anomaly_score=round(score, 4),
            threshold=self.threshold,
            is_anomaly=is_anomaly,
            severity=_severity_from_score(score, self.threshold) if is_anomaly else Severity.LOW,
            evidence={"mean": mean, "std": std, "z_score": round(score, 4)},
        )


# ── 2. Robust Z-Score (MAD) Detector ─────────────────────────────────


@DetectorRegistry.register("robust_zscore")
@DetectorRegistry.register("robust_z_score")
class RobustZScoreDetector(BaseAnomalyDetector):
    """Median Absolute Deviation (MAD) based Z-score detector, resistant to outliers."""

    def __init__(self, threshold: float = 3.5, **parameters: Any) -> None:
        super().__init__(**parameters)
        self.threshold = threshold

    def fit_detect(
        self,
        history: list[float] | np.ndarray,
        current: float,
        metric_name: str = "metric",
        dataset_name: str | None = None,
        node_id: str | None = None,
    ) -> AnomalyResult:
        arr = np.asarray(history, dtype=float)
        arr = arr[~np.isnan(arr)]

        if len(arr) < 3:
            return AnomalyResult(
                detector="robust_zscore",
                dataset_name=dataset_name,
                node_id=node_id,
                metric=metric_name,
                baseline=float(np.median(arr)) if len(arr) > 0 else None,
                observed=current,
                anomaly_score=0.0,
                threshold=self.threshold,
                is_anomaly=False,
                severity=Severity.LOW,
                evidence={"reason": "insufficient_history"},
            )

        median = float(np.median(arr))
        mad = float(np.median(np.abs(arr - median)))

        # Standard normal consistency constant: 0.6745
        if mad < 1e-9:
            is_anomaly = abs(current - median) > 1e-9
            score = 10.0 if is_anomaly else 0.0
        else:
            score = float(0.6745 * abs(current - median) / mad)
            is_anomaly = score >= self.threshold

        return AnomalyResult(
            detector="robust_zscore",
            dataset_name=dataset_name,
            node_id=node_id,
            metric=metric_name,
            baseline=median,
            observed=current,
            anomaly_score=round(score, 4),
            threshold=self.threshold,
            is_anomaly=is_anomaly,
            severity=_severity_from_score(score, self.threshold) if is_anomaly else Severity.LOW,
            evidence={"median": median, "mad": mad, "robust_z": round(score, 4)},
        )


# ── 3. IQR Detector ──────────────────────────────────────────────────


@DetectorRegistry.register("iqr")
class IQRDetector(BaseAnomalyDetector):
    """Interquartile Range detector (Tukey's fences)."""

    def __init__(self, multiplier: float = 1.5, **parameters: Any) -> None:
        super().__init__(**parameters)
        self.multiplier = multiplier

    def fit_detect(
        self,
        history: list[float] | np.ndarray,
        current: float,
        metric_name: str = "metric",
        dataset_name: str | None = None,
        node_id: str | None = None,
    ) -> AnomalyResult:
        arr = np.asarray(history, dtype=float)
        arr = arr[~np.isnan(arr)]

        if len(arr) < 4:
            return AnomalyResult(
                detector="iqr",
                dataset_name=dataset_name,
                node_id=node_id,
                metric=metric_name,
                baseline=float(np.median(arr)) if len(arr) > 0 else None,
                observed=current,
                anomaly_score=0.0,
                threshold=self.multiplier,
                is_anomaly=False,
                severity=Severity.LOW,
                evidence={"reason": "insufficient_history"},
            )

        q25, q75 = np.percentile(arr, [25, 75])
        iqr = float(q75 - q25)
        lower_bound = float(q25 - self.multiplier * iqr)
        upper_bound = float(q75 + self.multiplier * iqr)

        is_anomaly = current < lower_bound or current > upper_bound

        # Calculate normalized score
        if iqr > 1e-9:
            dist = max(0.0, lower_bound - current, current - upper_bound)
            score = float(dist / iqr)
        else:
            score = 10.0 if is_anomaly else 0.0

        return AnomalyResult(
            detector="iqr",
            dataset_name=dataset_name,
            node_id=node_id,
            metric=metric_name,
            baseline=float(np.median(arr)),
            observed=current,
            anomaly_score=round(score, 4),
            threshold=self.multiplier,
            is_anomaly=is_anomaly,
            severity=_severity_from_score(score, 1.0) if is_anomaly else Severity.LOW,
            evidence={
                "q25": round(float(q25), 4),
                "q75": round(float(q75), 4),
                "iqr": round(iqr, 4),
                "lower_bound": round(lower_bound, 4),
                "upper_bound": round(upper_bound, 4),
            },
        )


# ── 4. EWMA Detector ─────────────────────────────────────────────────


@DetectorRegistry.register("ewma")
class EWMADetector(BaseAnomalyDetector):
    """Exponentially Weighted Moving Average control chart detector."""

    def __init__(self, alpha: float = 0.3, num_sigmas: float = 3.0, **parameters: Any) -> None:
        super().__init__(**parameters)
        self.alpha = alpha
        self.num_sigmas = num_sigmas

    def fit_detect(
        self,
        history: list[float] | np.ndarray,
        current: float,
        metric_name: str = "metric",
        dataset_name: str | None = None,
        node_id: str | None = None,
    ) -> AnomalyResult:
        arr = np.asarray(history, dtype=float)
        arr = arr[~np.isnan(arr)]

        if len(arr) < 3:
            return AnomalyResult(
                detector="ewma",
                dataset_name=dataset_name,
                node_id=node_id,
                metric=metric_name,
                baseline=float(np.mean(arr)) if len(arr) > 0 else None,
                observed=current,
                anomaly_score=0.0,
                threshold=self.num_sigmas,
                is_anomaly=False,
                severity=Severity.LOW,
            )

        # Compute running EWMA
        ewma = arr[0]
        for val in arr[1:]:
            ewma = self.alpha * val + (1.0 - self.alpha) * ewma

        std = float(np.std(arr, ddof=1))
        # Asymptotic control limit width factor
        sigma_ewma = std * np.sqrt(self.alpha / (2.0 - self.alpha)) if std > 1e-9 else 0.0

        if sigma_ewma > 1e-9:
            score = float(abs(current - ewma) / sigma_ewma)
            is_anomaly = score >= self.num_sigmas
        else:
            is_anomaly = abs(current - ewma) > 1e-9
            score = 10.0 if is_anomaly else 0.0

        return AnomalyResult(
            detector="ewma",
            dataset_name=dataset_name,
            node_id=node_id,
            metric=metric_name,
            baseline=round(float(ewma), 4),
            observed=current,
            anomaly_score=round(score, 4),
            threshold=self.num_sigmas,
            is_anomaly=is_anomaly,
            severity=_severity_from_score(score, self.num_sigmas) if is_anomaly else Severity.LOW,
            evidence={
                "ewma_mean": round(float(ewma), 4),
                "sigma_ewma": round(float(sigma_ewma), 4),
                "alpha": self.alpha,
            },
        )


# ── 5. CUSUM Detector ────────────────────────────────────────────────


@DetectorRegistry.register("cusum")
class CUSUMDetector(BaseAnomalyDetector):
    """Cumulative Sum (CUSUM) quality control chart for detecting persistent mean shifts."""

    def __init__(self, drift_k: float = 0.5, threshold_h: float = 4.0, **parameters: Any) -> None:
        super().__init__(**parameters)
        self.k = drift_k
        self.h = threshold_h

    def fit_detect(
        self,
        history: list[float] | np.ndarray,
        current: float,
        metric_name: str = "metric",
        dataset_name: str | None = None,
        node_id: str | None = None,
    ) -> AnomalyResult:
        arr = np.asarray(history, dtype=float)
        arr = arr[~np.isnan(arr)]

        if len(arr) < 5:
            return AnomalyResult(
                detector="cusum",
                dataset_name=dataset_name,
                node_id=node_id,
                metric=metric_name,
                baseline=float(np.mean(arr)) if len(arr) > 0 else None,
                observed=current,
                anomaly_score=0.0,
                threshold=self.h,
                is_anomaly=False,
                severity=Severity.LOW,
            )

        mean = float(np.mean(arr))
        std = float(np.std(arr, ddof=1))

        if std < 1e-9:
            is_anomaly = abs(current - mean) > 1e-9
            return AnomalyResult(
                detector="cusum",
                metric=metric_name,
                baseline=mean,
                observed=current,
                anomaly_score=10.0 if is_anomaly else 0.0,
                threshold=self.h,
                is_anomaly=is_anomaly,
                severity=Severity.HIGH if is_anomaly else Severity.LOW,
            )

        # Normalized values
        z_hist = (arr - mean) / std
        z_curr = (current - mean) / std

        s_pos = 0.0
        s_neg = 0.0
        for z in list(z_hist) + [z_curr]:
            s_pos = max(0.0, s_pos + z - self.k)
            s_neg = max(0.0, s_neg - z - self.k)

        score = float(max(s_pos, s_neg))
        is_anomaly = score >= self.h

        return AnomalyResult(
            detector="cusum",
            dataset_name=dataset_name,
            node_id=node_id,
            metric=metric_name,
            baseline=mean,
            observed=current,
            anomaly_score=round(score, 4),
            threshold=self.h,
            is_anomaly=is_anomaly,
            severity=_severity_from_score(score, self.h) if is_anomaly else Severity.LOW,
            evidence={
                "cusum_pos": round(s_pos, 4),
                "cusum_neg": round(s_neg, 4),
                "slack_k": self.k,
            },
        )


# ── 6. Isolation Forest Detector ─────────────────────────────────────


@DetectorRegistry.register("isolation_forest")
@DetectorRegistry.register("iforest")
class IsolationForestDetector(BaseAnomalyDetector):
    """Unsupervised Isolation Forest anomaly detector for tabular/series metric data."""

    def __init__(self, contamination: float = 0.05, random_state: int = 42, **parameters: Any) -> None:
        super().__init__(**parameters)
        self.contamination = contamination
        self.random_state = random_state

    def fit_detect(
        self,
        history: list[float] | np.ndarray,
        current: float,
        metric_name: str = "metric",
        dataset_name: str | None = None,
        node_id: str | None = None,
    ) -> AnomalyResult:
        arr = np.asarray(history, dtype=float)
        arr = arr[~np.isnan(arr)]

        if len(arr) < 10:
            return AnomalyResult(
                detector="isolation_forest",
                dataset_name=dataset_name,
                node_id=node_id,
                metric=metric_name,
                baseline=float(np.mean(arr)) if len(arr) > 0 else None,
                observed=current,
                anomaly_score=0.0,
                threshold=0.5,
                is_anomaly=False,
                severity=Severity.LOW,
            )

        X_train = arr.reshape(-1, 1)
        model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
        )
        model.fit(X_train)

        # score_samples returns opposite of anomaly score (lower means more anomalous)
        raw_score = -float(model.score_samples([[current]])[0])
        pred = model.predict([[current]])[0]  # -1 for anomaly, 1 for normal
        is_anomaly = bool(pred == -1)

        return AnomalyResult(
            detector="isolation_forest",
            dataset_name=dataset_name,
            node_id=node_id,
            metric=metric_name,
            baseline=float(np.mean(arr)),
            observed=current,
            anomaly_score=round(raw_score, 4),
            threshold=0.5,
            is_anomaly=is_anomaly,
            severity=Severity.HIGH if is_anomaly else Severity.LOW,
            evidence={"decision_function": round(raw_score, 4), "is_outlier": is_anomaly},
        )


# ── Distribution Shift Detection ─────────────────────────────────────


class DistributionShiftDetector:
    """Detects shifts between baseline and observed distribution samples using KS, JSD, and PSI."""

    @staticmethod
    def kolmogorov_smirnov(
        baseline: list[float] | np.ndarray,
        observed: list[float] | np.ndarray,
        p_threshold: float = 0.05,
        metric_name: str = "metric",
        dataset_name: str | None = None,
    ) -> DistributionShiftResult:
        """Two-sample Kolmogorov-Smirnov test for continuous distributions."""
        b = np.asarray(baseline, dtype=float)
        o = np.asarray(observed, dtype=float)
        b = b[~np.isnan(b)]
        o = o[~np.isnan(o)]

        if len(b) < 5 or len(o) < 5:
            return DistributionShiftResult(
                dataset_name=dataset_name,
                metric=metric_name,
                method="ks_test",
                statistic=0.0,
                p_value=1.0,
                threshold=p_threshold,
                is_shift=False,
                severity=Severity.LOW,
            )

        stat_res = stats.ks_2samp(b, o)
        stat = float(stat_res.statistic)
        p_val = float(stat_res.pvalue)
        is_shift = p_val < p_threshold

        sev = Severity.HIGH if p_val < 0.001 else (Severity.MEDIUM if is_shift else Severity.LOW)

        return DistributionShiftResult(
            dataset_name=dataset_name,
            metric=metric_name,
            method="ks_test",
            statistic=round(stat, 4),
            p_value=round(p_val, 6),
            threshold=p_threshold,
            is_shift=is_shift,
            severity=sev,
            evidence={"ks_statistic": round(stat, 4), "p_value": round(p_val, 6)},
        )

    @staticmethod
    def jensen_shannon(
        baseline: list[float] | np.ndarray,
        observed: list[float] | np.ndarray,
        threshold: float = 0.25,
        bins: int = 20,
        metric_name: str = "metric",
        dataset_name: str | None = None,
    ) -> DistributionShiftResult:
        """Jensen-Shannon divergence between empirical distributions (bounded in [0, 1])."""
        b = np.asarray(baseline, dtype=float)
        o = np.asarray(observed, dtype=float)
        b = b[~np.isnan(b)]
        o = o[~np.isnan(o)]

        if len(b) < 5 or len(o) < 5:
            return DistributionShiftResult(
                dataset_name=dataset_name,
                metric=metric_name,
                method="jensen_shannon",
                statistic=0.0,
                threshold=threshold,
                is_shift=False,
                severity=Severity.LOW,
            )

        # Compute common bin edges
        min_v = min(float(b.min()), float(o.min()))
        max_v = max(float(b.max()), float(o.max()))
        if min_v == max_v:
            min_v -= 1.0
            max_v += 1.0
        bin_edges = np.linspace(min_v, max_v, bins + 1)

        hist_b, _ = np.histogram(b, bins=bin_edges)
        hist_o, _ = np.histogram(o, bins=bin_edges)

        # Normalize to probability distributions with Laplace smoothing
        prob_b = (hist_b + 1e-6) / (np.sum(hist_b) + 1e-6 * bins)
        prob_o = (hist_o + 1e-6) / (np.sum(hist_o) + 1e-6 * bins)

        js_dist = float(spatial.distance.jensenshannon(prob_b, prob_o))
        is_shift = js_dist >= threshold
        sev = Severity.HIGH if js_dist >= 0.4 else (Severity.MEDIUM if is_shift else Severity.LOW)

        return DistributionShiftResult(
            dataset_name=dataset_name,
            metric=metric_name,
            method="jensen_shannon",
            statistic=round(js_dist, 4),
            threshold=threshold,
            is_shift=is_shift,
            severity=sev,
            evidence={"js_distance": round(js_dist, 4), "bins": bins},
        )

    @staticmethod
    def population_stability_index(
        baseline: list[float] | np.ndarray,
        observed: list[float] | np.ndarray,
        threshold: float = 0.25,
        bins: int = 10,
        metric_name: str = "metric",
        dataset_name: str | None = None,
    ) -> DistributionShiftResult:
        """Population Stability Index (PSI): standard data drift metric."""
        b = np.asarray(baseline, dtype=float)
        o = np.asarray(observed, dtype=float)
        b = b[~np.isnan(b)]
        o = o[~np.isnan(o)]

        if len(b) < 10 or len(o) < 10:
            return DistributionShiftResult(
                dataset_name=dataset_name,
                metric=metric_name,
                method="psi",
                statistic=0.0,
                threshold=threshold,
                is_shift=False,
                severity=Severity.LOW,
            )

        # Quantile bin edges from baseline
        quantiles = np.linspace(0, 100, bins + 1)
        bin_edges = np.percentile(b, quantiles)
        bin_edges[0] -= 1e-5
        bin_edges[-1] += 1e-5
        # Ensure unique bin edges
        bin_edges = np.unique(bin_edges)
        if len(bin_edges) < 2:
            return DistributionShiftResult(
                dataset_name=dataset_name,
                metric=metric_name,
                method="psi",
                statistic=0.0,
                threshold=threshold,
                is_shift=False,
                severity=Severity.LOW,
            )

        hist_b, _ = np.histogram(b, bins=bin_edges)
        hist_o, _ = np.histogram(o, bins=bin_edges)

        # Proportions with small epsilon to avoid div by zero
        p_b = (hist_b + 1e-5) / (np.sum(hist_b) + 1e-5 * len(hist_b))
        p_o = (hist_o + 1e-5) / (np.sum(hist_o) + 1e-5 * len(hist_o))

        psi_val = float(np.sum((p_o - p_b) * np.log(p_o / p_b)))
        is_shift = psi_val >= threshold
        sev = Severity.HIGH if psi_val >= 0.5 else (Severity.MEDIUM if is_shift else Severity.LOW)

        return DistributionShiftResult(
            dataset_name=dataset_name,
            metric=metric_name,
            method="psi",
            statistic=round(psi_val, 4),
            threshold=threshold,
            is_shift=is_shift,
            severity=sev,
            evidence={"psi": round(psi_val, 4), "num_bins": len(bin_edges) - 1},
        )
