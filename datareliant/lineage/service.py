"""Lineage service managing pipeline definitions and database persistence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from datareliant.common.exceptions import PipelineNotFoundError
from datareliant.common.models import PipelineEdgeModel, PipelineNodeModel
from datareliant.lineage.graph import LineageGraph
from datareliant.lineage.models import (
    BlastRadiusReport,
    LineageEdge,
    LineageNode,
    PipelineMetadata,
)


class LineageService:
    """Orchestrates pipeline metadata loading, persistence, and lineage querying."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session
        self.pipelines_dir = Path("configs/pipelines")

    async def register_pipeline(self, pipeline: PipelineMetadata) -> LineageGraph:
        """Persist pipeline topology to database and return constructed LineageGraph."""
        graph = LineageGraph(pipeline_id=pipeline.id)
        graph.load_pipeline(pipeline)

        if self.session is not None:
            # Delete existing nodes and edges for this pipeline to allow updates
            await self.session.execute(
                delete(PipelineEdgeModel).where(PipelineEdgeModel.pipeline_id == pipeline.id)
            )
            await self.session.execute(
                delete(PipelineNodeModel).where(PipelineNodeModel.pipeline_id == pipeline.id)
            )

            for n in pipeline.nodes:
                node_row = PipelineNodeModel(
                    id=n.id,
                    pipeline_id=pipeline.id,
                    node_type=n.type,
                    label=n.label,
                    metadata_=n.metadata,
                )
                self.session.add(node_row)

            for e in pipeline.edges:
                edge_row = PipelineEdgeModel(
                    pipeline_id=pipeline.id,
                    source_node_id=e.source,
                    target_node_id=e.target,
                    relationship_type=e.relationship,
                    metadata_=e.metadata,
                )
                self.session.add(edge_row)

            await self.session.flush()

        return graph

    async def get_pipeline_graph(self, pipeline_id: str) -> LineageGraph:
        """Load LineageGraph from database or file."""
        if self.session is not None:
            n_stmt = select(PipelineNodeModel).where(PipelineNodeModel.pipeline_id == pipeline_id)
            n_res = await self.session.execute(n_stmt)
            node_models = n_res.scalars().all()

            if node_models:
                e_stmt = select(PipelineEdgeModel).where(PipelineEdgeModel.pipeline_id == pipeline_id)
                e_res = await self.session.execute(e_stmt)
                edge_models = e_res.scalars().all()

                nodes = [
                    LineageNode(id=m.id, type=m.node_type, label=m.label, metadata=m.metadata_)
                    for m in node_models
                ]
                edges = [
                    LineageEdge(
                        source=m.source_node_id,
                        target=m.target_node_id,
                        relationship=m.relationship_type,
                        metadata=m.metadata_,
                    )
                    for m in edge_models
                ]
                pipe = PipelineMetadata(id=pipeline_id, nodes=nodes, edges=edges)
                graph = LineageGraph(pipeline_id=pipeline_id)
                graph.load_pipeline(pipe)
                return graph

        # Check local yaml directory
        yaml_path = self.pipelines_dir / f"{pipeline_id}.yaml"
        if yaml_path.exists():
            return LineageGraph.from_yaml(yaml_path)

        raise PipelineNotFoundError(f"Pipeline '{pipeline_id}' not found")

    async def list_pipelines(self) -> list[dict[str, Any]]:
        """List all distinct registered pipelines."""
        if self.session is not None:
            stmt = select(PipelineNodeModel.pipeline_id).distinct()
            res = await self.session.execute(stmt)
            p_ids = [row[0] for row in res.all()]
            if p_ids:
                return [{"pipeline_id": pid} for pid in p_ids]

        # Scan pipelines_dir
        if self.pipelines_dir.exists():
            return [
                {"pipeline_id": p.stem} for p in self.pipelines_dir.glob("*.yaml")
            ]
        return []

    async def get_blast_radius(self, pipeline_id: str, node_id: str) -> BlastRadiusReport:
        """Compute blast radius report for a node in a pipeline."""
        graph = await self.get_pipeline_graph(pipeline_id)
        return graph.compute_blast_radius(node_id)
