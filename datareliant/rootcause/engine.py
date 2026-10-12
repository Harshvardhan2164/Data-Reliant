"""Explainable Root-Cause Analysis Engine with multi-signal evidence scoring."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from datareliant.common.types import Evidence, EvidenceCategory, RootCauseType
from datareliant.lineage.graph import LineageGraph
from datareliant.rootcause.models import RootCauseCandidate

if TYPE_CHECKING:
    from datareliant.incidents.models import Incident

# Category weights documented in methodology: sum to 1.0
EVIDENCE_WEIGHTS: dict[str, float] = {
    "schema": 0.25,
    "graph": 0.20,
    "statistical": 0.20,
    "temporal": 0.15,
    "propagation": 0.10,
    "historical": 0.10,
}


class RootCauseEngine:
    """Evaluates incidents and ranks candidate root causes with explainable evidence breakdowns."""

    def __init__(self, top_k: int = 3) -> None:
        self.top_k = top_k

    def analyze_incident(
        self,
        incident: Incident,
        lineage_graph: LineageGraph | None = None,
        historical_matches: list[dict[str, Any]] | None = None,
    ) -> list[RootCauseCandidate]:
        """Rank candidate root causes for an incident and provide evidence for each."""
        candidates_map: dict[RootCauseType, list[Evidence]] = {}

        # 1. Inspect anomaly types and metric signatures to identify candidate causes
        for anom in incident.anomalies:
            metric_lower = anom.metric.lower()
            det_lower = anom.detector.lower()

            # Null spike signal
            if "null" in metric_lower or "not_null" in det_lower:
                self._add_evidence(
                    candidates_map,
                    RootCauseType.NULL_SPIKE,
                    Evidence(
                        category=EvidenceCategory.STATISTICAL,
                        description=f"Null rate anomaly detected on {anom.metric} (score={anom.anomaly_score})",
                        score=0.95,
                    ),
                )

            # Duplicate ingestion signal
            if "duplicate" in metric_lower or "dup" in metric_lower or "duplicate" in det_lower:
                self._add_evidence(
                    candidates_map,
                    RootCauseType.DUPLICATE_INGESTION,
                    Evidence(
                        category=EvidenceCategory.STATISTICAL,
                        description=f"Duplicate row anomaly detected on {anom.metric} (score={anom.anomaly_score})",
                        score=0.95,
                    ),
                )

            # Missing data / row count drop signal (when not caused by foreign key)
            if (
                ("row_count" in metric_lower or "missing" in metric_lower)
                and "referential" not in det_lower
                and "orphan" not in metric_lower
            ):
                self._add_evidence(
                    candidates_map,
                    RootCauseType.MISSING_DATA,
                    Evidence(
                        category=EvidenceCategory.STATISTICAL,
                        description=f"Row count deviation on {anom.metric} (observed={anom.observed}, baseline={anom.baseline})",
                        score=0.95,
                    ),
                )

            # Distribution shift signal
            if (
                "ks" in det_lower
                or "shift" in metric_lower
                or "psi" in det_lower
                or "distribution" in metric_lower
            ):
                self._add_evidence(
                    candidates_map,
                    RootCauseType.DISTRIBUTION_SHIFT,
                    Evidence(
                        category=EvidenceCategory.STATISTICAL,
                        description=f"Statistical distribution shift confirmed by {anom.detector}",
                        score=0.95,
                    ),
                )

            # Datatype change signal
            if (
                "datatype" in metric_lower
                or "type" in metric_lower
                or "incompatible" in metric_lower
            ):
                self._add_evidence(
                    candidates_map,
                    RootCauseType.TYPE_CHANGE,
                    Evidence(
                        category=EvidenceCategory.SCHEMA,
                        description=f"Incompatible datatype alteration detected on {anom.metric}",
                        score=0.95,
                    ),
                )

            # Schema drift signal (added/removed columns)
            if (
                ("schema" in det_lower or "column" in metric_lower or "drift" in metric_lower)
                and "datatype" not in metric_lower
                and "type" not in metric_lower
            ):
                self._add_evidence(
                    candidates_map,
                    RootCauseType.SCHEMA_DRIFT,
                    Evidence(
                        category=EvidenceCategory.SCHEMA,
                        description="Schema drift observed between dataset versions",
                        score=0.95,
                    ),
                )

            # Transformation error (range violations / extreme bounds)
            if "range" in det_lower or "bound" in metric_lower:
                self._add_evidence(
                    candidates_map,
                    RootCauseType.TRANSFORMATION_ERROR,
                    Evidence(
                        category=EvidenceCategory.STATISTICAL,
                        description=f"Numeric range violation detected on {anom.metric}",
                        score=0.95,
                    ),
                )

            # Source data change (categorical invalidity)
            if "categorical" in det_lower or "domain" in metric_lower or "invalid" in metric_lower:
                self._add_evidence(
                    candidates_map,
                    RootCauseType.SOURCE_DATA_CHANGE,
                    Evidence(
                        category=EvidenceCategory.STATISTICAL,
                        description=f"Invalid categorical domain code detected on {anom.metric}",
                        score=0.95,
                    ),
                )

            # Timezone shift
            if "timezone" in metric_lower or "gap" in metric_lower or "gap" in det_lower:
                self._add_evidence(
                    candidates_map,
                    RootCauseType.TIMEZONE_MISMATCH,
                    Evidence(
                        category=EvidenceCategory.TEMPORAL,
                        description=f"Temporal discrepancy or timezone gap in timestamp column {anom.metric}",
                        score=0.95,
                    ),
                )

            # Late arrival / freshness
            if "freshness" in det_lower or "staleness" in metric_lower or "late" in metric_lower:
                self._add_evidence(
                    candidates_map,
                    RootCauseType.LATE_ARRIVAL,
                    Evidence(
                        category=EvidenceCategory.TEMPORAL,
                        description=f"Stale data arrival or processing lag on {anom.metric}",
                        score=0.95,
                    ),
                )

            # Referential integrity / upstream foreign key orphan signal
            if "referential" in det_lower or "orphan" in metric_lower:
                self._add_evidence(
                    candidates_map,
                    RootCauseType.UPSTREAM_FAILURE,
                    Evidence(
                        category=EvidenceCategory.GRAPH,
                        description="Foreign key referential orphan records indicating upstream producer failure",
                        score=1.0,
                    ),
                )
                self._add_evidence(
                    candidates_map,
                    RootCauseType.UPSTREAM_FAILURE,
                    Evidence(
                        category=EvidenceCategory.STATISTICAL,
                        description="High orphan rate consistent with upstream cut-off",
                        score=0.90,
                    ),
                )

        # 2. Lineage and Graph Evidence
        if lineage_graph and incident.affected_nodes:
            # Check if any affected node has upstream dependencies
            for node in incident.affected_nodes:
                try:
                    upstream = lineage_graph.get_upstream(node)
                except Exception:
                    continue
                if upstream:
                    upstream_ids = [
                        u["id"] for u in upstream if isinstance(u, dict) and "id" in u
                    ] or [str(u) for u in upstream]
                    upstream_in_incident = [
                        uid for uid in upstream_ids if uid in incident.affected_nodes
                    ]
                    score = (
                        min(1.0, 0.80 + 0.10 * len(upstream_in_incident))
                        if upstream_in_incident
                        else min(1.0, 0.5 + 0.15 * len(upstream_ids))
                    )
                    self._add_evidence(
                        candidates_map,
                        RootCauseType.UPSTREAM_FAILURE,
                        Evidence(
                            category=EvidenceCategory.GRAPH,
                            description=f"Node '{node}' has upstream dependencies: {', '.join(upstream_ids)}",
                            score=score,
                        ),
                    )

            first_affected = incident.affected_nodes[0]
            try:
                downstream = lineage_graph.get_downstream(first_affected)
            except Exception:
                downstream = []
            if downstream:
                for c_type in list(candidates_map.keys()):
                    self._add_evidence(
                        candidates_map,
                        c_type,
                        Evidence(
                            category=EvidenceCategory.PROPAGATION,
                            description=f"Failure propagates to {len(downstream)} downstream nodes",
                            score=min(1.0, 0.2 * len(downstream)),
                        ),
                    )

        # 3. Temporal Sequence Evidence (earliest anomaly)
        if len(incident.anomalies) >= 2:
            earliest = min(incident.anomalies, key=lambda a: a.detected_at)
            for c_type in candidates_map:
                self._add_evidence(
                    candidates_map,
                    c_type,
                    Evidence(
                        category=EvidenceCategory.TEMPORAL,
                        description=f"Earliest anomaly detected at {earliest.detected_at.isoformat()} on {earliest.metric}",
                        score=0.80,
                    ),
                )

        # 4. Historical Match Evidence
        if historical_matches:
            for match in historical_matches:
                m_type_str = match.get("root_cause_type")
                sim_score = match.get("similarity", 0.5)
                try:
                    m_type = RootCauseType(m_type_str)
                    self._add_evidence(
                        candidates_map,
                        m_type,
                        Evidence(
                            category=EvidenceCategory.HISTORICAL,
                            description=f"Matches historical incident '{match.get('id', 'past')}' with similarity {round(sim_score, 2)}",
                            score=float(sim_score),
                        ),
                    )
                except Exception:
                    pass

        # If no specific cause generated, provide default TRANSFORMATION_ERROR
        if not candidates_map:
            candidates_map[RootCauseType.TRANSFORMATION_ERROR] = [
                Evidence(
                    category=EvidenceCategory.STATISTICAL,
                    description="Uncategorized anomaly signature consistent with transformation error",
                    score=0.50,
                )
            ]

        # 5. Compute candidate scores using formula
        ranked_candidates: list[RootCauseCandidate] = []
        scores: list[float] = []

        for cause_type, evidence_list in candidates_map.items():
            breakdown: dict[str, float] = {}
            for e in evidence_list:
                cat_name = e.category.value
                breakdown[cat_name] = max(breakdown.get(cat_name, 0.0), e.score)

            # Weighted sum formula
            total_score = sum(
                breakdown.get(cat, 0.0) * weight for cat, weight in EVIDENCE_WEIGHTS.items()
            )
            scores.append(total_score)

            explanation = (
                f"Candidate {cause_type.value} supported by {len(evidence_list)} evidence items "
                f"across [{', '.join(breakdown.keys())}]."
            )

            ranked_candidates.append(
                RootCauseCandidate(
                    root_cause_type=cause_type,
                    confidence=0.0,  # to be normalized
                    total_score=round(total_score, 4),
                    evidence_items=evidence_list,
                    evidence_breakdown=breakdown,
                    explanation=explanation,
                )
            )

        # Sort by total_score descending
        ranked_candidates.sort(key=lambda c: c.total_score, reverse=True)
        top_candidates = ranked_candidates[: self.top_k]

        # 6. Normalize confidence scores
        sum_scores = sum(c.total_score for c in top_candidates)
        for i, cand in enumerate(top_candidates):
            cand.rank = i + 1
            if sum_scores > 1e-6:
                cand.confidence = round(cand.total_score / sum_scores, 4)
            else:
                cand.confidence = round(1.0 / len(top_candidates), 4)

        return top_candidates

    def _add_evidence(
        self,
        mapping: dict[RootCauseType, list[Evidence]],
        cause: RootCauseType,
        evidence: Evidence,
    ) -> None:
        """Helper to append evidence to a candidate cause."""
        if cause not in mapping:
            mapping[cause] = []
        mapping[cause].append(evidence)
