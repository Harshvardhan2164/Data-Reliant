"""Machine Learning Root-Cause Classifier with Logistic Regression, Random Forest, and XGBoost."""

from __future__ import annotations

from typing import Any

import numpy as np
import xgboost as xgb
from pydantic import BaseModel, Field
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

from datareliant.ml.features import FEATURE_NAMES


class MLModelEvaluationMetrics(BaseModel):
    """Evaluation metrics for a trained ML root-cause model."""

    model_name: str
    accuracy: float
    precision_macro: float
    recall_macro: float
    f1_macro: float
    top_3_accuracy: float
    confusion_matrix: list[list[int]] = Field(default_factory=list)
    feature_importances: dict[str, float] = Field(default_factory=dict)
    classes: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return self.model_dump(mode="json")


class MLRootCauseClassifier:
    """Supervised ML model for classifying incident root causes from structured feature vectors."""

    def __init__(
        self,
        model_type: str = "random_forest",  # "logistic_regression", "random_forest", "xgboost"
        random_state: int = 42,
    ) -> None:
        self.model_type = model_type.lower()
        self.random_state = random_state
        self.classes_: list[str] = []
        self.class_to_idx: dict[str, int] = {}
        self.model: Any = None
        self._init_model()

    def _init_model(self) -> None:
        """Instantiate the chosen ML algorithm."""
        if self.model_type in ("logreg", "logistic_regression"):
            self.model = LogisticRegression(
                max_iter=1000,
                random_state=self.random_state,
                class_weight="balanced",
            )
        elif self.model_type in ("rf", "random_forest"):
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=8,
                random_state=self.random_state,
                class_weight="balanced",
            )
        elif self.model_type in ("xgb", "xgboost"):
            self.model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=self.random_state,
                eval_metric="mlogloss",
            )
        else:
            raise ValueError(f"Unsupported model_type '{self.model_type}'")

    def train_and_evaluate(
        self,
        X: np.ndarray,
        y: list[str] | np.ndarray,
        test_size: float = 0.25,
    ) -> MLModelEvaluationMetrics:
        """Train model with proper train/test split and calculate full research metrics."""
        y_arr = np.asarray(y)
        unique_classes = sorted(set(y_arr))
        self.classes_ = unique_classes
        self.class_to_idx = {c: i for i, c in enumerate(unique_classes)}
        y_encoded = np.array([self.class_to_idx[c] for c in y_arr])

        # Stratified train/test split to prevent class imbalance skew
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y_encoded,
            test_size=test_size,
            random_state=self.random_state,
            stratify=y_encoded
            if len(unique_classes) > 1 and len(y_encoded) >= 2 * len(unique_classes)
            else None,
        )

        self.model.fit(X_train, y_train)

        # Predictions
        y_pred = self.model.predict(X_test)
        y_prob = self.model.predict_proba(X_test)

        acc = float(np.mean(y_pred == y_test))
        prec = float(precision_score(y_test, y_pred, average="macro", zero_division=0))
        rec = float(recall_score(y_test, y_pred, average="macro", zero_division=0))
        f1 = float(f1_score(y_test, y_pred, average="macro", zero_division=0))

        # Top-3 Accuracy
        top3_correct = 0
        for i in range(len(y_test)):
            probs = y_prob[i]
            top3_indices = np.argsort(probs)[-3:]
            if y_test[i] in top3_indices:
                top3_correct += 1
        top3_acc = float(top3_correct / max(len(y_test), 1))

        # Confusion Matrix
        cm = confusion_matrix(y_test, y_pred, labels=list(range(len(unique_classes))))

        # Feature importances
        feat_importances: dict[str, float] = {}
        if hasattr(self.model, "feature_importances_"):
            raw_imp = self.model.feature_importances_
            feat_importances = {
                name: round(float(imp), 4)
                for name, imp in zip(FEATURE_NAMES, raw_imp, strict=False)
            }
        elif hasattr(self.model, "coef_"):
            mean_coef = np.mean(np.abs(self.model.coef_), axis=0)
            norm_coef = mean_coef / (np.sum(mean_coef) + 1e-9)
            feat_importances = {
                name: round(float(imp), 4)
                for name, imp in zip(FEATURE_NAMES, norm_coef, strict=False)
            }

        return MLModelEvaluationMetrics(
            model_name=self.model_type,
            accuracy=round(acc, 4),
            precision_macro=round(prec, 4),
            recall_macro=round(rec, 4),
            f1_macro=round(f1, 4),
            top_3_accuracy=round(top3_acc, 4),
            confusion_matrix=cm.tolist(),
            feature_importances=feat_importances,
            classes=self.classes_,
        )

    def predict_top_k(self, feature_vector: np.ndarray, k: int = 3) -> list[tuple[str, float]]:
        """Predict top-K root cause probabilities for a single feature vector."""
        if self.model is None or not self.classes_:
            return []

        X_input = feature_vector.reshape(1, -1)
        probs = self.model.predict_proba(X_input)[0]

        top_indices = np.argsort(probs)[::-1][:k]
        return [(self.classes_[idx], round(float(probs[idx]), 4)) for idx in top_indices]
