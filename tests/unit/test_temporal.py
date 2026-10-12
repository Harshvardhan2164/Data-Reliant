"""Unit tests for the Temporal Anomaly Analysis Engine."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from datareliant.anomaly.temporal import TemporalAnomalyAnalyzer


class TestTemporalAnomalyAnalyzer:
    """Test trend, seasonality, spikes/drops, change points, and gaps."""

    def test_insufficient_history_graceful_downgrade(self):
        analyzer = TemporalAnomalyAnalyzer()
        base_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        # Only 5 data points
        ts = [base_time + timedelta(hours=i) for i in range(5)]
        vals = [10.0, 11.0, 10.5, 9.8, 10.2]

        res = analyzer.analyze_series(ts, vals, metric_name="row_count")
        assert res.data_points_count == 5
        assert res.is_seasonal is False
        assert res.baseline_method == "SIMPLE_STATISTICAL"
        assert res.seasonality_period is None

    def test_trend_detection_upward_and_downward(self):
        analyzer = TemporalAnomalyAnalyzer()
        base_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)

        # Upward trend
        ts_up = [base_time + timedelta(hours=i) for i in range(20)]
        vals_up = [100.0 + 10.0 * i for i in range(20)]
        res_up = analyzer.analyze_series(ts_up, vals_up)
        assert res_up.trend_direction == "UPWARD"
        assert res_up.trend_slope > 0.0

        # Downward trend
        vals_down = [300.0 - 10.0 * i for i in range(20)]
        res_down = analyzer.analyze_series(ts_up, vals_down)
        assert res_down.trend_direction == "DOWNWARD"
        assert res_down.trend_slope < 0.0

    def test_seasonality_detection_with_full_cycles(self):
        analyzer = TemporalAnomalyAnalyzer()
        base_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        # 7-point repeating cycle repeated 5 times = 35 points
        pattern = [10.0, 20.0, 50.0, 80.0, 40.0, 15.0, 5.0]
        vals = pattern * 5
        ts = [base_time + timedelta(days=i) for i in range(len(vals))]

        res = analyzer.analyze_series(ts, vals)
        assert res.is_seasonal is True
        assert res.seasonality_period == 7
        assert res.baseline_method == "SEASONAL_DECOMPOSITION"

    def test_sudden_spike_and_drop_detection(self):
        analyzer = TemporalAnomalyAnalyzer()
        base_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        ts = [base_time + timedelta(hours=i) for i in range(20)]
        vals = [100.0] * 20
        # Add normal small noise
        vals = [100.0 + (i % 2) for i in range(20)]
        # Inject spike at index 10 and drop at index 15
        vals[10] = 300.0  # huge spike
        vals[15] = 10.0  # huge drop

        res = analyzer.analyze_series(ts, vals)
        assert len(res.spikes) >= 1
        assert res.spikes[0]["value"] == 300.0
        assert len(res.drops) >= 1

    def test_missing_intervals_detection(self):
        analyzer = TemporalAnomalyAnalyzer()
        base_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        ts = [
            base_time + timedelta(hours=1),
            base_time + timedelta(hours=2),
            base_time + timedelta(hours=3),
            base_time + timedelta(hours=24),  # 21-hour gap!
            base_time + timedelta(hours=25),
        ]
        vals = [10.0, 10.0, 10.0, 10.0, 10.0]

        res = analyzer.analyze_series(ts, vals, expected_interval_seconds=3600.0)
        assert len(res.missing_intervals) == 1
        assert "start" in res.missing_intervals[0]
        assert "end" in res.missing_intervals[0]

    def test_change_point_detection(self):
        analyzer = TemporalAnomalyAnalyzer()
        base_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        ts = [base_time + timedelta(hours=i) for i in range(24)]
        # Regime 1: mean 50, Regime 2: mean 150
        vals = [50.0 + (i % 2) for i in range(12)] + [150.0 + (i % 2) for i in range(12)]

        res = analyzer.analyze_series(ts, vals)
        assert len(res.change_points) >= 1
        cp = res.change_points[0]
        assert cp["shift_sigmas"] >= 3.0
