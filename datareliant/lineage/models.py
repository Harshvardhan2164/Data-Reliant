"""Data models and schemas for Pipeline Metadata and Lineage Graphs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from datareliant.common.types import NodeType


class LineageNode(BaseModel):
    """A node in the data and pipeline dependency graph."""

    id: str
    type: NodeType
    label: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LineageEdge(BaseModel):
    """A directed edge indicating dependency or data movement."""

    source: str
    target: str
    relationship: str = "depends_on"  # "reads", "produces", "transforms", "depends_on"
    metadata: dict[str, Any] = Field(default_factory=dict)


class PipelineMetadata(BaseModel):
    """Complete specification of a data pipeline and its dependency topology."""

    id: str
    name: str = ""
    schedule: str | None = None
    sla_minutes: int | None = None
    nodes: list[LineageNode] = Field(default_factory=list)
    edges: list[LineageEdge] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BlastRadiusReport(BaseModel):
    """Impact analysis report showing blast radius when a specific node fails."""

    root_failed_node: str
    upstream_dependencies: list[str] = Field(default_factory=list)
    downstream_impacted: list[str] = Field(default_factory=list)
    shortest_path_to_dashboards: dict[str, list[str]] = Field(default_factory=dict)
    impacted_dashboards: list[str] = Field(default_factory=list)
    impacted_models: list[str] = Field(default_factory=list)
    total_nodes_in_pipeline: int = 0
    total_impacted_nodes: int = 0
    blast_radius_score: float = 0.0  # Normalized between 0.0 and 1.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return self.model_dump(mode="json")
