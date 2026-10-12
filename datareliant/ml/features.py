"""Feature engineering for ML Root-Cause Classification."""

from __future__ import annotations

from typing import Any

import numpy as np

from datareliant.incidents.models import Incident

FEATURE_NAMES = [
    "record_count_delta",
    "null_rate_delta",
    "duplicate_rate_delta",
    "freshness_delta",
    "processing_delay",
    "schema_change",
    "upstream_failure",
    "downstream_impact",
    "distribution_distance",
    "dependency_depth",
    "historical_similarity",
    "anomaly_count",
]


class IncidentMLFeatureExtractor:
    """Extracts standardized 12-dimensional feature vector for an incident."""

    @staticmethod
    def extract_vector(
        incident: Incident,
        context: dict[str, Any] | None = None,
    ) -> np.ndarray:
        """Extract ordered numerical feature vector matching FEATURE_NAMES."""
        ctx = context or {}

        metrics_lower = [a.metric.lower() for a in incident.anomalies]
        [a.anomaly_score for a in incident.anomalies]

        # 1. record_count_delta
        rc_scores = [a.anomaly_score for a in incident.anomalies if "row" in a.metric.lower()]
        rc_delta = max(rc_scores, default=0.0)

        # 2. null_rate_delta
        null_scores = [a.anomaly_score for a in incident.anomalies if "null" in a.metric.lower()]
        null_delta = max(null_scores, default=0.0)

        # 3. duplicate_rate_delta
        dup_scores = [a.anomaly_score for a in incident.anomalies if "dup" in a.metric.lower()]
        dup_delta = max(dup_scores, default=0.0)

        # 4. freshness_delta
        fresh_scores = [
            a.anomaly_score
            for a in incident.anomalies
            if "fresh" in a.metric.lower() or "time" in a.metric.lower()
        ]
        fresh_delta = max(fresh_scores, default=0.0)

        # 5. processing_delay
        delay = float(ctx.get("processing_delay_seconds", 0.0))

        # 6. schema_change (0 or 1)
        schema_change = float(
            any("schema" in m or "drift" in m for m in metrics_lower)
            or ctx.get("has_schema_drift", False)
        )

        # 7. upstream_failure (0 or 1)
        upstream_fail = float(ctx.get("upstream_failure_detected", False))

        # 8. downstream_impact (number of affected nodes)
        downstream_impact = float(len(incident.affected_nodes))

        # 9. distribution_distance (KS or PSI metric score)
        dist_scores = [
            a.anomaly_score
            for a in incident.anomalies
            if "ks" in a.detector.lower() or "psi" in a.detector.lower()
        ]
        dist_distance = max(dist_scores, default=0.0)

        # 10. dependency_depth
        depth = float(ctx.get("dependency_depth", 1.0))

        # 11. historical_similarity
        hist_sim = float(ctx.get("top_historical_similarity", 0.0))

        # 12. anomaly_count
        anom_count = float(len(incident.anomalies))

        vector = [
            rc_delta,
            null_delta,
            dup_delta,
            fresh_delta,
            delay,
            schema_change,
            upstream_fail,
            downstream_impact,
            dist_distance,
            depth,
            hist_sim,
            anom_count,
        ]
        return np.array(vector, dtype=float)

    @staticmethod
    def feature_names() -> list[str]:
        return list(FEATURE_NAMES)
