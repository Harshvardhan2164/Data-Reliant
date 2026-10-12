"""Unit tests for the Pipeline Lineage Graph Engine and Impact Analysis."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from datareliant.common.database import Base
from datareliant.common.types import NodeType
from datareliant.lineage.graph import LineageGraph
from datareliant.lineage.models import LineageEdge, LineageNode, PipelineMetadata
from datareliant.lineage.service import LineageService


@pytest.fixture
def sample_pipeline_yaml() -> str:
    """Sample pipeline topology YAML matching the specification: A -> B -> C -> D."""
    return """
pipeline:
  id: transaction_ingestion
  name: Transaction Ingestion & Analytics
  schedule: "0 * * * *"
  sla_minutes: 30

nodes:
  - id: transactions_raw
    type: source
    label: Raw Transactions Stream
  - id: ingestion_job
    type: pipeline
    label: Spark Ingestion Job
  - id: transactions_clean
    type: table
    label: Clean Transactions Table
  - id: fraud_model
    type: model
    label: Real-time Fraud Detection Model
  - id: executive_dashboard
    type: dashboard
    label: Executive Revenue Dashboard

edges:
  - source: transactions_raw
    target: ingestion_job
    relationship: reads
  - source: ingestion_job
    target: transactions_clean
    relationship: produces
  - source: transactions_clean
    target: fraud_model
    relationship: trains
  - source: transactions_clean
    target: executive_dashboard
    relationship: displays
"""


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


class TestLineageGraph:
    """Test graph traversal, shortest path, common ancestors, and blast radius."""

    def test_load_from_yaml(self, sample_pipeline_yaml: str):
        graph = LineageGraph.from_yaml(sample_pipeline_yaml)
        assert graph.pipeline_id == "transaction_ingestion"
        assert graph.graph.number_of_nodes() == 5
        assert graph.graph.number_of_edges() == 4

    def test_upstream_traversal(self, sample_pipeline_yaml: str):
        graph = LineageGraph.from_yaml(sample_pipeline_yaml)
        # Upstream of executive_dashboard should be: transactions_clean, ingestion_job, transactions_raw
        upstream = graph.get_upstream("executive_dashboard")
        assert len(upstream) == 3
        ancestor_ids = {u["id"] for u in upstream}
        assert ancestor_ids == {"transactions_clean", "ingestion_job", "transactions_raw"}
        # Direct parent has depth 1
        direct = next(u for u in upstream if u["id"] == "transactions_clean")
        assert direct["depth"] == 1

    def test_downstream_traversal(self, sample_pipeline_yaml: str):
        graph = LineageGraph.from_yaml(sample_pipeline_yaml)
        # Downstream of transactions_raw: ingestion_job, transactions_clean, fraud_model, executive_dashboard
        downstream = graph.get_downstream("transactions_raw")
        assert len(downstream) == 4
        desc_ids = {d["id"] for d in downstream}
        assert "executive_dashboard" in desc_ids
        assert "fraud_model" in desc_ids

    def test_shortest_dependency_path(self, sample_pipeline_yaml: str):
        graph = LineageGraph.from_yaml(sample_pipeline_yaml)
        path = graph.get_shortest_path("transactions_raw", "executive_dashboard")
        assert path == [
            "transactions_raw",
            "ingestion_job",
            "transactions_clean",
            "executive_dashboard",
        ]

    def test_common_upstream_ancestor(self, sample_pipeline_yaml: str):
        graph = LineageGraph.from_yaml(sample_pipeline_yaml)
        # LCA of fraud_model and executive_dashboard should be transactions_clean
        lca = graph.get_common_upstream_ancestor(["fraud_model", "executive_dashboard"])
        assert lca == "transactions_clean"

        # LCA of transactions_clean and executive_dashboard
        lca2 = graph.get_common_upstream_ancestor(["transactions_clean", "executive_dashboard"])
        assert lca2 == "transactions_clean"

    def test_blast_radius_analysis(self, sample_pipeline_yaml: str):
        graph = LineageGraph.from_yaml(sample_pipeline_yaml)
        # If ingestion_job fails:
        report = graph.compute_blast_radius("ingestion_job")

        assert report.root_failed_node == "ingestion_job"
        assert "transactions_clean" in report.downstream_impacted
        assert "executive_dashboard" in report.impacted_dashboards
        assert "fraud_model" in report.impacted_models
        assert report.total_impacted_nodes == 4  # ingestion_job + 3 downstream
        assert 0.0 < report.blast_radius_score <= 1.0
        assert "executive_dashboard" in report.shortest_path_to_dashboards

    def test_d3_dictionary_export(self, sample_pipeline_yaml: str):
        graph = LineageGraph.from_yaml(sample_pipeline_yaml)
        d3_data = graph.to_d3_dict()
        assert "nodes" in d3_data
        assert "edges" in d3_data
        assert len(d3_data["nodes"]) == 5
        assert len(d3_data["edges"]) == 4


class TestLineageServicePersistence:
    """Test LineageService database integration."""

    @pytest.mark.asyncio
    async def test_register_and_fetch_pipeline(self, in_memory_session: AsyncSession):
        pipe = PipelineMetadata(
            id="order_etl",
            name="Order ETL",
            nodes=[
                LineageNode(id="orders_db", type=NodeType.SOURCE),
                LineageNode(id="etl_task", type=NodeType.JOB),
                LineageNode(id="orders_dw", type=NodeType.TABLE),
            ],
            edges=[
                LineageEdge(source="orders_db", target="etl_task"),
                LineageEdge(source="etl_task", target="orders_dw"),
            ],
        )

        service = LineageService(in_memory_session)
        graph = await service.register_pipeline(pipe)
        assert graph.graph.number_of_nodes() == 3

        # Re-fetch from DB
        fetched_graph = await service.get_pipeline_graph("order_etl")
        assert fetched_graph.graph.number_of_nodes() == 3
        assert fetched_graph.graph.number_of_edges() == 2

        # Blast radius
        report = await service.get_blast_radius("order_etl", "orders_db")
        assert report.total_impacted_nodes == 3
