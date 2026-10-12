"""Unit tests for Incident Correlation, Root-Cause Analysis, and Historical Similarity."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from datareliant.anomaly.models import AnomalyResult
from datareliant.common.database import Base
from datareliant.common.types import NodeType, RootCauseType, Severity
from datareliant.incidents.correlator import IncidentCorrelator
from datareliant.incidents.models import Incident
from datareliant.incidents.service import IncidentService
from datareliant.incidents.similarity import (
    IncidentSimilarityEngine,
    extract_incident_features,
)
from datareliant.lineage.graph import LineageGraph
from datareliant.lineage.models import LineageEdge, LineageNode, PipelineMetadata
from datareliant.rootcause.engine import RootCauseEngine


@pytest.fixture
def sample_lineage() -> LineageGraph:
    """Create a sample A -> B -> C lineage graph."""
    graph = LineageGraph("test_pipe")
    pipe = PipelineMetadata(
        id="test_pipe",
        nodes=[
            LineageNode(id="orders_raw", type=NodeType.SOURCE),
            LineageNode(id="orders_clean", type=NodeType.TABLE),
            LineageNode(id="revenue_dash", type=NodeType.DASHBOARD),
        ],
        edges=[
            LineageEdge(source="orders_raw", target="orders_clean"),
            LineageEdge(source="orders_clean", target="revenue_dash"),
        ],
    )
    graph.load_pipeline(pipe)
    return graph


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


class TestIncidentCorrelator:
    """Test anomaly clustering and alert compression."""

    def test_alert_compression(self, sample_lineage: LineageGraph):
        now = datetime.now(UTC)
        # 4 anomalies occurring in close temporal proximity on connected nodes
        anomalies = [
            AnomalyResult(
                detector="zscore",
                dataset_name="orders",
                node_id="orders_raw",
                metric="null_rate_customer_id",
                observed=0.45,
                anomaly_score=4.5,
                severity=Severity.HIGH,
                detected_at=now,
            ),
            AnomalyResult(
                detector="robust_zscore",
                dataset_name="orders",
                node_id="orders_raw",
                metric="row_count",
                observed=200.0,
                anomaly_score=3.8,
                severity=Severity.HIGH,
                detected_at=now + timedelta(minutes=2),
            ),
            AnomalyResult(
                detector="zscore",
                dataset_name="orders",
                node_id="orders_clean",
                metric="null_rate_customer_id",
                observed=0.45,
                anomaly_score=4.2,
                severity=Severity.HIGH,
                detected_at=now + timedelta(minutes=5),
            ),
            AnomalyResult(
                detector="iqr",
                dataset_name="orders",
                node_id="orders_clean",
                metric="total_revenue",
                observed=1000.0,
                anomaly_score=3.5,
                severity=Severity.MEDIUM,
                detected_at=now + timedelta(minutes=6),
            ),
        ]

        correlator = IncidentCorrelator(time_window_minutes=30)
        incidents = correlator.correlate(anomalies, lineage_graph=sample_lineage)

        # 4 raw alerts should be compressed into 1 correlated incident!
        assert len(incidents) == 1
        inc = incidents[0]
        assert inc.anomaly_count == 4
        assert "orders_raw" in inc.affected_nodes
        assert "orders_clean" in inc.affected_nodes
        assert inc.severity in (Severity.HIGH, Severity.CRITICAL)

    def test_unrelated_anomalies_separated(self):
        now = datetime.now(UTC)
        # Anomalies separated by 24 hours on different datasets
        anom1 = AnomalyResult(
            detector="zscore",
            dataset_name="customers",
            metric="null_rate",
            observed=0.2,
            anomaly_score=3.0,
            detected_at=now,
        )
        anom2 = AnomalyResult(
            detector="zscore",
            dataset_name="inventory",
            metric="stock_level",
            observed=0.0,
            anomaly_score=4.0,
            detected_at=now + timedelta(hours=24),
        )

        correlator = IncidentCorrelator(time_window_minutes=30)
        incidents = correlator.correlate([anom1, anom2])
        assert len(incidents) == 2


class TestRootCauseEngine:
    """Test explainable root-cause ranking and evidence scoring."""

    def test_null_spike_root_cause(self):
        now = datetime.now(UTC)
        inc = Incident(
            title="Customer ID Quality Failure",
            start_time=now,
            affected_nodes=["customers"],
            anomalies=[
                AnomalyResult(
                    detector="robust_zscore",
                    dataset_name="customers",
                    metric="null_rate_customer_id",
                    observed=0.60,
                    anomaly_score=6.2,
                    severity=Severity.CRITICAL,
                    detected_at=now,
                )
            ],
        )

        engine = RootCauseEngine(top_k=3)
        candidates = engine.analyze_incident(inc)

        assert len(candidates) > 0
        top = candidates[0]
        assert top.root_cause_type == RootCauseType.NULL_SPIKE
        assert top.confidence > 0.0
        assert "statistical" in top.evidence_breakdown
        assert len(top.evidence_items) > 0

    def test_upstream_failure_with_lineage(self, sample_lineage: LineageGraph):
        now = datetime.now(UTC)
        inc = Incident(
            title="Clean Table Failure",
            start_time=now,
            affected_nodes=["orders_clean"],
            anomalies=[
                AnomalyResult(
                    detector="zscore",
                    node_id="orders_clean",
                    metric="missing_rows",
                    observed=50.0,
                    anomaly_score=4.0,
                    detected_at=now,
                )
            ],
        )

        engine = RootCauseEngine(top_k=3)
        candidates = engine.analyze_incident(inc, lineage_graph=sample_lineage)

        cause_types = {c.root_cause_type for c in candidates}
        assert RootCauseType.UPSTREAM_FAILURE in cause_types
        up_cand = next(c for c in candidates if c.root_cause_type == RootCauseType.UPSTREAM_FAILURE)
        assert "graph" in up_cand.evidence_breakdown


class TestHistoricalIncidentSimilarity:
    """Test structured feature vector extraction and cosine similarity retrieval."""

    def test_feature_extraction(self):
        now = datetime.now(UTC)
        inc = Incident(
            title="Test Incident",
            severity=Severity.HIGH,
            start_time=now,
            affected_nodes=["table_a", "table_b"],
            anomalies=[
                AnomalyResult(
                    detector="zscore",
                    metric="null_rate",
                    observed=0.5,
                    anomaly_score=5.0,
                    detected_at=now,
                )
            ],
        )
        feats = extract_incident_features(inc)
        assert feats["anomaly_count"] == 1.0
        assert feats["affected_nodes_count"] == 2.0
        assert feats["has_null"] == 1.0
        assert feats["has_dup"] == 0.0

    def test_similarity_matching(self):
        now = datetime.now(UTC)
        curr = Incident(
            title="Current Null Spike",
            severity=Severity.HIGH,
            start_time=now,
            affected_nodes=["orders"],
            anomalies=[
                AnomalyResult(
                    detector="zscore",
                    metric="null_rate",
                    observed=0.5,
                    anomaly_score=5.0,
                    detected_at=now,
                )
            ],
        )

        history = [
            {
                "original_incident_id": "hist_001",
                "root_cause_type": "NULL_SPIKE",
                "severity": "HIGH",
                "feature_vector": extract_incident_features(curr),  # Identical
            },
            {
                "original_incident_id": "hist_002",
                "root_cause_type": "DUPLICATE_INGESTION",
                "severity": "LOW",
                "feature_vector": {
                    "anomaly_count": 10.0,
                    "affected_nodes_count": 5.0,
                    "severity": 1.0,
                    "has_null": 0.0,
                    "has_dup": 1.0,
                    "has_rows": 0.0,
                    "has_schema": 0.0,
                    "has_shift": 0.0,
                    "has_temporal": 0.0,
                    "max_score": 2.0,
                },
            },
        ]

        engine = IncidentSimilarityEngine()
        matches = engine.match_against_archive(curr, history, top_k=2)
        assert len(matches) == 2
        # Identical incident must have highest similarity
        assert matches[0]["incident_id"] == "hist_001"
        assert matches[0]["similarity"] == pytest.approx(1.0, abs=0.01)
        assert matches[0]["root_cause_type"] == "NULL_SPIKE"


class TestIncidentServiceIntegration:
    """Test end-to-end incident service with database persistence."""

    @pytest.mark.asyncio
    async def test_correlate_analyze_and_persist(self, in_memory_session: AsyncSession):
        now = datetime.now(UTC)
        anomalies = [
            AnomalyResult(
                id="anom_1",
                detector="zscore",
                dataset_name="transactions",
                node_id="tx_table",
                metric="null_rate_tx_id",
                observed=0.35,
                anomaly_score=4.0,
                severity=Severity.HIGH,
                detected_at=now,
            ),
            AnomalyResult(
                id="anom_2",
                detector="robust_zscore",
                dataset_name="transactions",
                node_id="tx_table",
                metric="duplicate_tx_id",
                observed=0.20,
                anomaly_score=3.5,
                severity=Severity.HIGH,
                detected_at=now + timedelta(minutes=1),
            ),
        ]

        service = IncidentService(in_memory_session)
        incidents = await service.correlate_and_analyze(anomalies)

        assert len(incidents) == 1
        inc = incidents[0]
        assert len(inc.candidate_causes) > 0

        # Query back from DB
        listed = await service.list_incidents()
        assert len(listed) == 1
        assert listed[0]["id"] == inc.id
        assert listed[0]["top_root_cause"] is not None

        full_inc = await service.get_incident(inc.id)
        assert full_inc["id"] == inc.id
        assert len(full_inc["candidate_causes"]) > 0
