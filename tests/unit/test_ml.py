"""Unit tests for ML Root-Cause Classification and Feature Engineering."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pytest

from datareliant.anomaly.models import AnomalyResult
from datareliant.common.types import Severity
from datareliant.incidents.models import Incident
from datareliant.ml.classifier import MLRootCauseClassifier
from datareliant.ml.features import FEATURE_NAMES, IncidentMLFeatureExtractor


@pytest.fixture
def sample_incident() -> Incident:
    """Create a sample incident for feature extraction."""
    now = datetime.now(UTC)
    return Incident(
        title="Sample Incident",
        severity=Severity.HIGH,
        start_time=now,
        affected_nodes=["payments_table", "orders_table"],
        anomalies=[
            AnomalyResult(
                detector="zscore",
                metric="null_rate_customer_id",
                observed=0.5,
                anomaly_score=5.2,
                detected_at=now,
            ),
            AnomalyResult(
                detector="ks_test",
                metric="amount_distribution",
                observed=0.1,
                anomaly_score=4.0,
                detected_at=now,
            ),
        ],
    )


@pytest.fixture
def synthetic_ml_dataset() -> tuple[np.ndarray, list[str]]:
    """Create synthetic training data across 4 root-cause classes."""
    np.random.seed(42)
    n_samples = 120

    # 4 classes: NULL_SPIKE, DUPLICATE_INGESTION, SCHEMA_DRIFT, MISSING_DATA
    classes = ["NULL_SPIKE", "DUPLICATE_INGESTION", "SCHEMA_DRIFT", "MISSING_DATA"]
    y = []
    X = []

    for i in range(n_samples):
        c = classes[i % 4]
        y.append(c)
        # Create distinctive signature with small noise
        row = np.random.uniform(0.0, 1.0, size=len(FEATURE_NAMES))
        if c == "NULL_SPIKE":
            row[1] = np.random.uniform(4.0, 8.0)  # null_rate_delta high
        elif c == "DUPLICATE_INGESTION":
            row[2] = np.random.uniform(4.0, 8.0)  # duplicate_rate_delta high
        elif c == "SCHEMA_DRIFT":
            row[5] = 1.0  # schema_change = 1.0
        elif c == "MISSING_DATA":
            row[0] = np.random.uniform(4.0, 8.0)  # record_count_delta high

        X.append(row)

    return np.array(X), y


class TestIncidentMLFeatures:
    """Test feature extractor dimensions and behavior."""

    def test_feature_extractor(self, sample_incident: Incident):
        vec = IncidentMLFeatureExtractor.extract_vector(
            sample_incident,
            context={"processing_delay_seconds": 15.0, "dependency_depth": 2.0},
        )
        assert len(vec) == 12
        assert len(vec) == len(FEATURE_NAMES)
        # null_rate_delta should be > 0.0
        assert vec[1] >= 5.0
        # processing delay should be 15.0
        assert vec[4] == 15.0


class TestMLModels:
    """Test Logistic Regression, Random Forest, and XGBoost classifiers."""

    def test_logistic_regression(self, synthetic_ml_dataset: tuple[np.ndarray, list[str]]):
        X, y = synthetic_ml_dataset
        clf = MLRootCauseClassifier(model_type="logistic_regression", random_state=42)
        metrics = clf.train_and_evaluate(X, y, test_size=0.25)

        assert metrics.accuracy > 0.70
        assert metrics.f1_macro > 0.70
        assert metrics.top_3_accuracy >= 0.90
        assert len(metrics.confusion_matrix) == 4
        assert len(metrics.feature_importances) == 12

    def test_random_forest(self, synthetic_ml_dataset: tuple[np.ndarray, list[str]]):
        X, y = synthetic_ml_dataset
        clf = MLRootCauseClassifier(model_type="random_forest", random_state=42)
        metrics = clf.train_and_evaluate(X, y, test_size=0.25)

        assert metrics.accuracy > 0.85
        assert metrics.f1_macro > 0.85
        assert metrics.top_3_accuracy >= 0.95
        assert len(metrics.feature_importances) == 12

        # Predict top-K
        test_vec = np.zeros(12)
        test_vec[1] = 6.0  # High null rate
        top3 = clf.predict_top_k(test_vec, k=3)
        assert len(top3) == 3
        assert top3[0][0] == "NULL_SPIKE"

    def test_xgboost(self, synthetic_ml_dataset: tuple[np.ndarray, list[str]]):
        X, y = synthetic_ml_dataset
        clf = MLRootCauseClassifier(model_type="xgboost", random_state=42)
        metrics = clf.train_and_evaluate(X, y, test_size=0.25)

        assert metrics.accuracy > 0.85
        assert metrics.f1_macro > 0.85
        assert metrics.top_3_accuracy >= 0.95
        assert len(metrics.feature_importances) == 12
