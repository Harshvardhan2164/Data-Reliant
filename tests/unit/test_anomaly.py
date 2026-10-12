"""Unit tests for the Statistical Anomaly Engine and Distribution Shift Detectors."""

from __future__ import annotations

import numpy as np
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from datareliant.anomaly.base import DetectorRegistry
from datareliant.anomaly.engine import AnomalyEngine
from datareliant.anomaly.service import AnomalyService
from datareliant.common.database import Base


@pytest.fixture
def normal_series() -> list[float]:
    """Synthetic normal metric values with mean 100 and std 5."""
    np.random.seed(42)
    return list(np.random.normal(loc=100.0, scale=5.0, size=50))


@pytest.fixture
async def in_memory_session():
    """Create an in-memory SQLite database session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


class TestAnomalyDetectors:
    """Test all 6 individual point anomaly detectors."""

    def test_detector_registry(self):
        registered = DetectorRegistry.available_detectors()
        for expected in ["zscore", "robust_zscore", "iqr", "ewma", "cusum", "isolation_forest"]:
            assert expected in registered

    def test_zscore_detector(self, normal_series: list[float]):
        engine = AnomalyEngine()
        # Point near mean: 102 -> NORMAL
        res_normal = engine.detect(normal_series, 102.0, detector="zscore")
        assert res_normal.is_anomaly is False

        # Extreme spike: 200.0 (mean=100, std=5 -> ~20 sigmas) -> ANOMALY
        res_spike = engine.detect(normal_series, 200.0, detector="zscore")
        assert res_spike.is_anomaly is True
        assert res_spike.anomaly_score > 10.0

    def test_robust_zscore_with_contaminated_history(self):
        engine = AnomalyEngine()
        # History contains few extreme outliers (contamination)
        history = [10.0] * 30 + [1000.0, 1500.0]
        # Normal value 10.0
        assert engine.detect(history, 10.0, detector="robust_zscore").is_anomaly is False
        # Anomalous value 50.0
        res = engine.detect(history, 50.0, detector="robust_zscore")
        assert res.is_anomaly is True

    def test_iqr_detector(self, normal_series: list[float]):
        engine = AnomalyEngine()
        res_norm = engine.detect(normal_series, 101.0, detector="iqr")
        assert res_norm.is_anomaly is False

        # Far outside Tukey fences
        res_out = engine.detect(normal_series, 180.0, detector="iqr")
        assert res_out.is_anomaly is True

    def test_ewma_detector(self, normal_series: list[float]):
        engine = AnomalyEngine()
        res_norm = engine.detect(normal_series, 99.0, detector="ewma")
        assert res_norm.is_anomaly is False

        res_drop = engine.detect(normal_series, 20.0, detector="ewma")
        assert res_drop.is_anomaly is True

    def test_cusum_detector(self, normal_series: list[float]):
        engine = AnomalyEngine()
        res_norm = engine.detect(normal_series, 100.0, detector="cusum")
        assert res_norm.is_anomaly is False

        res_shift = engine.detect(normal_series, 140.0, detector="cusum")
        assert res_shift.is_anomaly is True

    def test_isolation_forest_detector(self, normal_series: list[float]):
        engine = AnomalyEngine()
        res_norm = engine.detect(normal_series, 100.0, detector="isolation_forest")
        assert res_norm.is_anomaly is False

        res_anom = engine.detect(normal_series, 250.0, detector="isolation_forest")
        assert res_anom.is_anomaly is True

    def test_multi_detector(self, normal_series: list[float]):
        engine = AnomalyEngine()
        results = engine.detect_multi(
            normal_series, 195.0, detectors=["zscore", "robust_zscore", "iqr"]
        )
        assert len(results) == 3
        # All three should flag 195.0 as anomaly
        for r in results:
            assert r.is_anomaly is True


class TestDistributionShiftDetectors:
    """Test KS-test, Jensen-Shannon, and PSI drift detection."""

    def test_ks_test_shift_and_stable(self):
        engine = AnomalyEngine()
        np.random.seed(42)
        base = np.random.normal(loc=50.0, scale=5.0, size=100)
        same_dist = np.random.normal(loc=50.0, scale=5.0, size=100)
        shifted = np.random.normal(loc=80.0, scale=12.0, size=100)

        res_stable = engine.detect_distribution_shift(base, same_dist, method="ks_test")
        assert res_stable.is_shift is False
        assert res_stable.p_value is not None and res_stable.p_value > 0.05

        res_drift = engine.detect_distribution_shift(base, shifted, method="ks_test")
        assert res_drift.is_shift is True
        assert res_drift.p_value is not None and res_drift.p_value < 0.01

    def test_jensen_shannon_divergence(self):
        engine = AnomalyEngine()
        np.random.seed(42)
        base = np.random.normal(loc=0.0, scale=1.0, size=150)
        same = np.random.normal(loc=0.0, scale=1.0, size=150)
        shifted = np.random.normal(loc=5.0, scale=1.0, size=150)

        res_same = engine.detect_distribution_shift(base, same, method="jensen_shannon")
        assert res_same.is_shift is False
        assert res_same.statistic < 0.20

        res_drift = engine.detect_distribution_shift(base, shifted, method="jensen_shannon")
        assert res_drift.is_shift is True
        assert res_drift.statistic >= 0.25

    def test_psi_metric(self):
        engine = AnomalyEngine()
        np.random.seed(42)
        base = np.random.normal(loc=10.0, scale=2.0, size=200)
        same = np.random.normal(loc=10.0, scale=2.0, size=200)
        shifted = np.random.normal(loc=20.0, scale=6.0, size=200)

        res_stable = engine.detect_distribution_shift(base, same, method="psi")
        assert res_stable.is_shift is False
        assert res_stable.statistic < 0.20

        res_shifted = engine.detect_distribution_shift(base, shifted, method="psi")
        assert res_shifted.is_shift is True
        assert res_shifted.statistic > 0.25


class TestAnomalyServicePersistence:
    """Test AnomalyService database persistence and queries."""

    @pytest.mark.asyncio
    async def test_persist_and_list_anomalies(
        self, normal_series: list[float], in_memory_session: AsyncSession
    ):
        service = AnomalyService(in_memory_session)
        res = service.engine.detect(
            normal_series,
            250.0,
            detector="zscore",
            metric_name="row_count",
            dataset_name="orders",
        )
        assert res.is_anomaly is True

        model = await service.record_anomaly(res)
        assert model is not None

        anomalies = await service.list_anomalies(dataset_name="orders")
        assert len(anomalies) == 1
        assert anomalies[0]["detector"] == "zscore"
        assert anomalies[0]["metric"] == "row_count"
        assert anomalies[0]["observed"] == 250.0
