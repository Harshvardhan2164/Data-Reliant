"""Temporal Anomaly Analysis Engine: Trend, seasonality, spikes/drops, change points, and missing intervals."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import numpy as np
from pydantic import BaseModel, Field


class TemporalAnalysisResult(BaseModel):
    """Output of temporal analysis on a metric series."""

    metric_name: str
    data_points_count: int
    trend_direction: str  # "UPWARD", "DOWNWARD", "STABLE"
    trend_slope: float
    is_seasonal: bool
    seasonality_period: int | None = None
    baseline_method: str  # "SEASONAL_DECOMPOSITION", "EWMA_TREND", "SIMPLE_STATISTICAL"
    change_points: list[dict[str, Any]] = Field(default_factory=list)
    missing_intervals: list[dict[str, str]] = Field(default_factory=list)
    spikes: list[dict[str, Any]] = Field(default_factory=list)
    drops: list[dict[str, Any]] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return self.model_dump(mode="json")


class TemporalAnomalyAnalyzer:
    """Analyzes pipeline metric time-series with trend, change points, and adaptive baselines."""

    def analyze_series(
        self,
        timestamps: list[datetime],
        values: list[float],
        metric_name: str = "metric",
        expected_interval_seconds: float | None = None,
    ) -> TemporalAnalysisResult:
        """Run temporal analysis on a sequence of timestamped metric observations.

        Gracefully downgrades baseline method if history is insufficient.
        """
        n = len(values)
        if n == 0:
            return TemporalAnalysisResult(
                metric_name=metric_name,
                data_points_count=0,
                trend_direction="STABLE",
                trend_slope=0.0,
                is_seasonal=False,
                baseline_method="SIMPLE_STATISTICAL",
                evidence={"reason": "empty_series"},
            )

        # Sort chronologically
        combined = sorted(zip(timestamps, values, strict=False), key=lambda x: x[0])
        ts_sorted = [c[0] for c in combined]
        vals = np.array([float(c[1]) for c in combined], dtype=float)

        # 1. Missing interval detection
        missing_intervals: list[dict[str, str]] = []
        if n >= 2:
            time_diffs_sec = np.array(
                [(ts_sorted[i] - ts_sorted[i - 1]).total_seconds() for i in range(1, n)]
            )
            median_interval = float(np.median(time_diffs_sec))
            exp_interval = expected_interval_seconds or (
                median_interval if median_interval > 0 else 3600.0
            )

            gap_threshold = exp_interval * 2.0
            for i in range(1, n):
                diff = (ts_sorted[i] - ts_sorted[i - 1]).total_seconds()
                if diff >= gap_threshold:
                    missing_intervals.append(
                        {
                            "start": ts_sorted[i - 1].isoformat(),
                            "end": ts_sorted[i].isoformat(),
                            "gap_seconds": str(round(diff, 1)),
                            "expected_interval": str(round(exp_interval, 1)),
                        }
                    )

        # 2. Trend detection via linear regression
        x = np.arange(n, dtype=float)
        if n >= 3:
            slope, _intercept = np.polyfit(x, vals, deg=1)
            mean_v = float(np.mean(vals))
            norm_slope = slope / max(abs(mean_v), 1e-6)

            # Check if slope is statistically / practically meaningful (> 2% per step)
            if norm_slope > 0.02:
                trend_dir = "UPWARD"
            elif norm_slope < -0.02:
                trend_dir = "DOWNWARD"
            else:
                trend_dir = "STABLE"
        else:
            slope = 0.0
            trend_dir = "STABLE"

        # 3. Seasonality detection (Autocorrelation with minimum data requirements)
        # Never claim seasonality if history < 14 points
        is_seasonal = False
        season_period = None
        baseline_method = "SIMPLE_STATISTICAL"

        if n >= 20:
            detrended = vals - (slope * x + np.mean(vals))
            norm_detrended = (
                (detrended - np.mean(detrended)) / (np.std(detrended) + 1e-9)
                if np.std(detrended) > 1e-9
                else detrended
            )
            # Compute autocorrelation for lags 2 to n//2
            max_lag = min(n // 2, 30)
            corrs = []
            for lag in range(2, max_lag):
                c = np.corrcoef(norm_detrended[:-lag], norm_detrended[lag:])[0, 1]
                corrs.append((lag, c))

            if corrs:
                best_lag, best_corr = max(corrs, key=lambda item: item[1])
                # Strong periodic signal threshold >= 0.65
                if best_corr >= 0.65:
                    is_seasonal = True
                    season_period = best_lag
                    baseline_method = "SEASONAL_DECOMPOSITION"
                elif n >= 10:
                    baseline_method = "EWMA_TREND"
        elif n >= 6:
            baseline_method = "EWMA_TREND"
        else:
            baseline_method = "SIMPLE_STATISTICAL"

        # 4. Sudden spikes and sudden drops detection using robust MAD scaling
        spikes: list[dict[str, Any]] = []
        drops: list[dict[str, Any]] = []
        median_v = float(np.median(vals))
        mad = float(np.median(np.abs(vals - median_v)))
        scale_v = 1.4826 * mad if mad > 1e-6 else float(np.std(vals))

        if n >= 3 and scale_v > 1e-6:
            diffs = np.diff(vals)
            step_threshold = 2.0 * scale_v

            for i in range(len(diffs)):
                step = diffs[i]
                curr_t = ts_sorted[i + 1]
                curr_val = vals[i + 1]

                if step >= step_threshold and (curr_val - median_v) >= 2.0 * scale_v:
                    spikes.append(
                        {
                            "timestamp": curr_t.isoformat(),
                            "value": curr_val,
                            "previous_value": vals[i],
                            "delta": round(float(step), 3),
                            "deviation_sigmas": round(float((curr_val - median_v) / scale_v), 2),
                        }
                    )
                elif step <= -step_threshold and (median_v - curr_val) >= 2.0 * scale_v:
                    drops.append(
                        {
                            "timestamp": curr_t.isoformat(),
                            "value": curr_val,
                            "previous_value": vals[i],
                            "delta": round(float(step), 3),
                            "deviation_sigmas": round(float((median_v - curr_val) / scale_v), 2),
                        }
                    )

        # 5. Change Point Detection (two-window mean shift test)
        change_points: list[dict[str, Any]] = []
        min_window = 4
        if n >= min_window * 2:
            for split_idx in range(min_window, n - min_window):
                w1 = vals[:split_idx]
                w2 = vals[split_idx:]
                m1, s1 = np.mean(w1), np.std(w1)
                m2, s2 = np.mean(w2), np.std(w2)
                pooled_std = np.sqrt((s1**2 + s2**2) / 2.0) if (s1 + s2) > 0 else 1.0

                shift_sigmas = abs(m2 - m1) / max(pooled_std, 1e-6)
                if shift_sigmas >= 3.0:
                    change_points.append(
                        {
                            "timestamp": ts_sorted[split_idx].isoformat(),
                            "shift_sigmas": round(float(shift_sigmas), 2),
                            "mean_before": round(float(m1), 3),
                            "mean_after": round(float(m2), 3),
                        }
                    )
                    break  # Record dominant change point

        return TemporalAnalysisResult(
            metric_name=metric_name,
            data_points_count=n,
            trend_direction=trend_dir,
            trend_slope=round(float(slope), 4),
            is_seasonal=is_seasonal,
            seasonality_period=season_period,
            baseline_method=baseline_method,
            change_points=change_points,
            missing_intervals=missing_intervals,
            spikes=spikes,
            drops=drops,
            evidence={
                "mean": round(float(np.mean(vals)), 3),
                "std": round(float(np.std(vals)), 3),
                "median": round(float(np.median(vals)), 3),
            },
        )
