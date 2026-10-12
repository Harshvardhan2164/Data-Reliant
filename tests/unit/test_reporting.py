"""Unit tests for Explanation Providers (Phase 19)."""

from __future__ import annotations

from datetime import UTC, datetime

from datareliant.anomaly.models import AnomalyResult
from datareliant.common.types import RootCauseType, Severity
from datareliant.incidents.models import Incident
from datareliant.reporting.explanations import (
    LocalLLMExplanationProvider,
    RuleBasedExplanationProvider,
)
from datareliant.rootcause.models import RootCauseCandidate


def test_rule_based_explanation_provider():
    now = datetime.now(UTC)
    inc = Incident(
        title="Null Rate Anomaly on Transactions",
        severity=Severity.HIGH,
        start_time=now,
        affected_nodes=["transactions"],
        anomalies=[
            AnomalyResult(
                detector="zscore",
                metric="null_rate_amount",
                observed=0.45,
                anomaly_score=5.2,
                severity=Severity.HIGH,
                detected_at=now,
            )
        ],
    )

    from datareliant.common.types import Evidence, EvidenceCategory

    candidate = RootCauseCandidate(
        root_cause_type=RootCauseType.NULL_SPIKE,
        confidence=0.88,
        evidence_breakdown={"statistical": 0.95, "graph": 0.70},
        evidence_items=[
            Evidence(
                category=EvidenceCategory.STATISTICAL,
                description="Null rate 5.2 sigma beyond baseline on 'amount'",
                score=0.95,
            )
        ],
    )

    provider = RuleBasedExplanationProvider()
    report = provider.generate_explanation(inc, [candidate])

    assert report.incident_id == inc.id
    assert report.top_root_cause == "NULL_SPIKE"
    assert report.confidence == 0.88
    assert "Null Rate Anomaly on Transactions" in report.executive_summary
    assert len(report.recommended_actions) >= 3
    assert any("null" in act.lower() for act in report.recommended_actions)
    assert len(report.evidence_synthesis) >= 1


def test_local_llm_explanation_provider_fallback():
    now = datetime.now(UTC)
    inc = Incident(
        title="Pipeline Delay",
        severity=Severity.MEDIUM,
        start_time=now,
        affected_nodes=["payments"],
        anomalies=[],
    )

    candidate = RootCauseCandidate(
        root_cause_type=RootCauseType.UPSTREAM_FAILURE,
        confidence=0.75,
        evidence_breakdown={"graph": 0.80},
    )

    # With non-installed/dummy model, it must gracefully fall back to RuleBasedExplanationProvider
    provider = LocalLLMExplanationProvider(model_name_or_path="dummy/nonexistent-model")
    report = provider.generate_explanation(inc, [candidate])

    assert report.incident_id == inc.id
    assert report.top_root_cause == "UPSTREAM_FAILURE"
    assert "local_llm_fallback" in report.provider_name
    assert len(report.recommended_actions) > 0
