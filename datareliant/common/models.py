"""SQLAlchemy ORM models for all core DataReliant tables.

This module defines the full relational schema.  Models are grouped by
domain concern but live in one file to keep Alembic auto-generation
simple.  Each model maps to the table list specified in the design doc.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from datareliant.common.database import Base
from datareliant.common.types import (
    IncidentStatus,
    NodeType,
    RootCauseType,
    Severity,
    Status,
)


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(UTC)


# ── Datasets ─────────────────────────────────────────────────────────


class DatasetModel(Base):
    """Registered dataset."""

    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    versions: Mapped[list[DatasetVersionModel]] = relationship(back_populates="dataset")


class DatasetVersionModel(Base):
    """Versioned snapshot of a dataset."""

    __tablename__ = "dataset_versions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    dataset_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    column_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    schema_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    dataset: Mapped[DatasetModel] = relationship(back_populates="versions")
    profiles: Mapped[list[ProfileModel]] = relationship(back_populates="dataset_version")

    __table_args__ = (UniqueConstraint("dataset_id", "version", name="uq_dataset_version"),)


# ── Profiles ─────────────────────────────────────────────────────────


class ProfileModel(Base):
    """Stored data profile for a dataset version."""

    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    dataset_version_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False
    )
    dataset_stats: Mapped[dict] = mapped_column(JSON, default=dict)
    column_stats: Mapped[dict] = mapped_column(JSON, default=dict)
    temporal_stats: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    dataset_version: Mapped[DatasetVersionModel] = relationship(back_populates="profiles")


# ── Quality ──────────────────────────────────────────────────────────


class QualityRuleModel(Base):
    """Persisted quality rule definition."""

    __tablename__ = "quality_rules"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    rule_type: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset_name: Mapped[str] = mapped_column(String(256), nullable=False)
    column: Mapped[str | None] = mapped_column(String(256), nullable=True)
    severity: Mapped[str] = mapped_column(
        Enum(Severity, name="severity_enum", create_constraint=True),
        default=Severity.MEDIUM,
    )
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class QualityResultModel(Base):
    """Result of executing a quality rule."""

    __tablename__ = "quality_results"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    rule_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("quality_rules.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dataset_name: Mapped[str] = mapped_column(String(256), nullable=False)
    column: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(Status, name="status_enum", create_constraint=True), nullable=False
    )
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    expected: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    execution_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ── Pipeline ─────────────────────────────────────────────────────────


class PipelineRunModel(Base):
    """Record of a pipeline execution."""

    __tablename__ = "pipeline_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    pipeline_id: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class PipelineNodeModel(Base):
    """A node in the pipeline dependency graph."""

    __tablename__ = "pipeline_nodes"

    id: Mapped[str] = mapped_column(String(256), primary_key=True)
    pipeline_id: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    node_type: Mapped[str] = mapped_column(
        Enum(NodeType, name="node_type_enum", create_constraint=True), nullable=False
    )
    label: Mapped[str | None] = mapped_column(String(256), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class PipelineEdgeModel(Base):
    """A directed edge in the pipeline dependency graph."""

    __tablename__ = "pipeline_edges"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    pipeline_id: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    source_node_id: Mapped[str] = mapped_column(String(256), nullable=False)
    target_node_id: Mapped[str] = mapped_column(String(256), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        UniqueConstraint(
            "pipeline_id", "source_node_id", "target_node_id", name="uq_pipeline_edge"
        ),
    )


# ── Anomalies ────────────────────────────────────────────────────────


class AnomalyModel(Base):
    """Detected anomaly."""

    __tablename__ = "anomalies"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    detector: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    node_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    metric: Mapped[str] = mapped_column(String(256), nullable=False)
    baseline: Mapped[float | None] = mapped_column(Float, nullable=True)
    observed: Mapped[float] = mapped_column(Float, nullable=False)
    anomaly_score: Mapped[float] = mapped_column(Float, nullable=False)
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    severity: Mapped[str] = mapped_column(
        Enum(Severity, name="severity_enum", create_constraint=False), nullable=False
    )
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ── Incidents ────────────────────────────────────────────────────────


class IncidentModel(Base):
    """Correlated incident grouping multiple anomalies."""

    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    severity: Mapped[str] = mapped_column(
        Enum(Severity, name="severity_enum", create_constraint=False), nullable=False
    )
    status: Mapped[str] = mapped_column(
        Enum(IncidentStatus, name="incident_status_enum", create_constraint=True),
        default=IncidentStatus.OPEN,
    )
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    affected_nodes: Mapped[list] = mapped_column(JSON, default=list)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    anomaly_links: Mapped[list[IncidentAnomalyModel]] = relationship(back_populates="incident")
    rootcause_candidates: Mapped[list[RootCauseCandidateModel]] = relationship(
        back_populates="incident"
    )


class IncidentAnomalyModel(Base):
    """Many-to-many link between incidents and anomalies."""

    __tablename__ = "incident_anomalies"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False
    )
    anomaly_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("anomalies.id", ondelete="CASCADE"), nullable=False
    )

    incident: Mapped[IncidentModel] = relationship(back_populates="anomaly_links")

    __table_args__ = (UniqueConstraint("incident_id", "anomaly_id", name="uq_incident_anomaly"),)


# ── Root Cause ───────────────────────────────────────────────────────


class RootCauseCandidateModel(Base):
    """A candidate root cause for an incident."""

    __tablename__ = "rootcause_candidates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False
    )
    root_cause_type: Mapped[str] = mapped_column(
        Enum(RootCauseType, name="rootcause_type_enum", create_constraint=True),
        nullable=False,
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    total_score: Mapped[float] = mapped_column(Float, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    incident: Mapped[IncidentModel] = relationship(back_populates="rootcause_candidates")


# ── Historical Incidents ─────────────────────────────────────────────


class HistoricalIncidentModel(Base):
    """Archived incident for similarity retrieval."""

    __tablename__ = "historical_incidents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    original_incident_id: Mapped[str] = mapped_column(String(64), nullable=False)
    feature_vector: Mapped[dict] = mapped_column(JSON, default=dict)
    root_cause_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    affected_nodes: Mapped[list] = mapped_column(JSON, default=list)
    evidence_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ── Experiments ──────────────────────────────────────────────────────


class ExperimentModel(Base):
    """Metadata for a reproducible experiment run."""

    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    experiment_type: Mapped[str] = mapped_column(String(64), nullable=False)
    scenario: Mapped[str | None] = mapped_column(String(256), nullable=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    random_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dataset_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    software_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    results: Mapped[list[ExperimentResultModel]] = relationship(back_populates="experiment")


class ExperimentResultModel(Base):
    """Metrics produced by an experiment."""

    __tablename__ = "experiment_results"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    experiment_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False
    )
    metric_name: Mapped[str] = mapped_column(String(256), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    experiment: Mapped[ExperimentModel] = relationship(back_populates="results")
