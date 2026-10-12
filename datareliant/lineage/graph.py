"""Lineage Graph implementation powered by NetworkX."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import networkx as nx
import yaml

from datareliant.common.exceptions import LineageError
from datareliant.lineage.models import (
    BlastRadiusReport,
    LineageEdge,
    LineageNode,
    PipelineMetadata,
)


class LineageGraph:
    """Directed acyclic data lineage graph with impact analysis and graph traversal."""

    def __init__(self, pipeline_id: str = "default_pipeline") -> None:
        self.pipeline_id = pipeline_id
        self.graph = nx.DiGraph()

    def add_node(self, node: LineageNode) -> None:
        """Add a typed node to the lineage graph."""
        self.graph.add_node(
            node.id,
            node_type=node.type.value if hasattr(node.type, "value") else str(node.type),
            label=node.label or node.id,
            metadata=node.metadata,
        )

    def add_edge(self, edge: LineageEdge) -> None:
        """Add a directed edge between two lineage nodes."""
        if not self.graph.has_node(edge.source):
            self.graph.add_node(edge.source, node_type="unknown", label=edge.source, metadata={})
        if not self.graph.has_node(edge.target):
            self.graph.add_node(edge.target, node_type="unknown", label=edge.target, metadata={})

        self.graph.add_edge(
            edge.source,
            edge.target,
            relationship=edge.relationship,
            metadata=edge.metadata,
        )

    def load_pipeline(self, pipeline: PipelineMetadata) -> None:
        """Populate the graph from PipelineMetadata."""
        self.pipeline_id = pipeline.id
        for n in pipeline.nodes:
            self.add_node(n)
        for e in pipeline.edges:
            self.add_edge(e)

    @classmethod
    def from_yaml(cls, yaml_content_or_path: str | Path) -> LineageGraph:
        """Load and build a LineageGraph from YAML specification."""
        if isinstance(yaml_content_or_path, Path) or (
            isinstance(yaml_content_or_path, str)
            and "\n" not in yaml_content_or_path
            and Path(yaml_content_or_path).exists()
        ):
            content = Path(yaml_content_or_path).read_text(encoding="utf-8")
        else:
            content = str(yaml_content_or_path)

        data = yaml.safe_load(content)
        pipe_meta = data.get("pipeline", {})
        p_id = pipe_meta.get("id", "pipeline")
        name = pipe_meta.get("name", p_id)
        sched = pipe_meta.get("schedule")
        sla = pipe_meta.get("sla_minutes")

        nodes = [LineageNode(**n) for n in data.get("nodes", [])]
        edges = [LineageEdge(**e) for e in data.get("edges", [])]

        pipeline = PipelineMetadata(
            id=p_id,
            name=name,
            schedule=sched,
            sla_minutes=sla,
            nodes=nodes,
            edges=edges,
        )
        graph = cls(pipeline_id=p_id)
        graph.load_pipeline(pipeline)
        return graph

    def get_upstream(self, node_id: str, max_depth: int | None = None) -> list[dict[str, Any]]:
        """Find all upstream ancestors that node_id depends on, with depth."""
        if not self.graph.has_node(node_id):
            raise LineageError(f"Node '{node_id}' does not exist in lineage graph")

        # Reversed BFS from node_id
        ancestors_with_depth = []
        visited = {node_id: 0}
        queue = [(node_id, 0)]

        while queue:
            curr, depth = queue.pop(0)
            if max_depth is not None and depth >= max_depth:
                continue

            for parent in self.graph.predecessors(curr):
                if parent not in visited:
                    visited[parent] = depth + 1
                    node_data = self.graph.nodes[parent]
                    ancestors_with_depth.append(
                        {
                            "id": parent,
                            "depth": depth + 1,
                            "type": node_data.get("node_type", "unknown"),
                            "label": node_data.get("label", parent),
                        }
                    )
                    queue.append((parent, depth + 1))

        return ancestors_with_depth

    def get_downstream(self, node_id: str, max_depth: int | None = None) -> list[dict[str, Any]]:
        """Find all downstream descendants that depend on node_id, with depth."""
        if not self.graph.has_node(node_id):
            raise LineageError(f"Node '{node_id}' does not exist in lineage graph")

        descendants_with_depth = []
        visited = {node_id: 0}
        queue = [(node_id, 0)]

        while queue:
            curr, depth = queue.pop(0)
            if max_depth is not None and depth >= max_depth:
                continue

            for child in self.graph.successors(curr):
                if child not in visited:
                    visited[child] = depth + 1
                    node_data = self.graph.nodes[child]
                    descendants_with_depth.append(
                        {
                            "id": child,
                            "depth": depth + 1,
                            "type": node_data.get("node_type", "unknown"),
                            "label": node_data.get("label", child),
                        }
                    )
                    queue.append((child, depth + 1))

        return descendants_with_depth

    def get_shortest_path(self, source_id: str, target_id: str) -> list[str]:
        """Find the shortest dependency path from source_id to target_id."""
        if not self.graph.has_node(source_id) or not self.graph.has_node(target_id):
            raise LineageError(f"Nodes '{source_id}' or '{target_id}' not found in graph")
        try:
            return list(nx.shortest_path(self.graph, source_id, target_id))
        except nx.NetworkXNoPath:
            return []

    def get_common_upstream_ancestor(self, node_ids: list[str]) -> str | None:
        """Find the Lowest Common Ancestor (LCA) shared by all specified nodes."""
        if not node_ids:
            return None
        if len(node_ids) == 1:
            return node_ids[0]

        # Ancestor sets
        ancestor_sets = []
        for nid in node_ids:
            if not self.graph.has_node(nid):
                return None
            ancs = nx.ancestors(self.graph, nid)
            ancs.add(nid)
            ancestor_sets.append(ancs)

        shared = set.intersection(*ancestor_sets)
        if not shared:
            return None

        # Return the ancestor with maximum topological depth (closest to the nodes)
        try:
            topo_order = {node: i for i, node in enumerate(nx.topological_sort(self.graph))}
            return max(shared, key=lambda n: topo_order.get(n, 0))
        except Exception:
            return next(iter(shared))

    def compute_blast_radius(self, node_id: str) -> BlastRadiusReport:
        """Execute comprehensive blast radius impact analysis for failure at node_id."""
        if not self.graph.has_node(node_id):
            raise LineageError(f"Node '{node_id}' does not exist in lineage graph")

        downstream = self.get_downstream(node_id)
        upstream = self.get_upstream(node_id)

        downstream_ids = [d["id"] for d in downstream]
        upstream_ids = [u["id"] for u in upstream]

        impacted_dashboards = []
        impacted_models = []
        paths_to_dashboards = {}

        for d in downstream:
            nid = d["id"]
            ntype = d.get("type", "").lower()
            if ntype == "dashboard":
                impacted_dashboards.append(nid)
                path = self.get_shortest_path(node_id, nid)
                if path:
                    paths_to_dashboards[nid] = path
            elif ntype == "model":
                impacted_models.append(nid)

        total_nodes = self.graph.number_of_nodes()
        total_impacted = len(downstream_ids) + 1  # includes the failed node itself

        # Score formula: 0.5 * (fraction of total nodes) + 0.3 * (dashboards impacted weight) + 0.2 * (models weight)
        node_fraction = total_impacted / max(total_nodes, 1)
        dash_weight = min(1.0, len(impacted_dashboards) / 2.0)
        model_weight = min(1.0, len(impacted_models) / 2.0)
        score = min(1.0, round(0.5 * node_fraction + 0.3 * dash_weight + 0.2 * model_weight, 4))

        return BlastRadiusReport(
            root_failed_node=node_id,
            upstream_dependencies=upstream_ids,
            downstream_impacted=downstream_ids,
            shortest_path_to_dashboards=paths_to_dashboards,
            impacted_dashboards=impacted_dashboards,
            impacted_models=impacted_models,
            total_nodes_in_pipeline=total_nodes,
            total_impacted_nodes=total_impacted,
            blast_radius_score=score,
        )

    def to_d3_dict(self) -> dict[str, Any]:
        """Serialize graph for D3.js interactive visualization."""
        nodes = []
        for n, data in self.graph.nodes(data=True):
            nodes.append(
                {
                    "id": n,
                    "label": data.get("label", n),
                    "type": data.get("node_type", "unknown"),
                    "in_degree": self.graph.in_degree(n),
                    "out_degree": self.graph.out_degree(n),
                    "metadata": data.get("metadata", {}),
                }
            )

        edges = []
        for u, v, data in self.graph.edges(data=True):
            edges.append(
                {
                    "source": u,
                    "target": v,
                    "relationship": data.get("relationship", "depends_on"),
                    "metadata": data.get("metadata", {}),
                }
            )

        return {"nodes": nodes, "edges": edges, "pipeline_id": self.pipeline_id}
