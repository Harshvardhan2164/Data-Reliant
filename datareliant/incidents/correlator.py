"""Incident Correlation Engine: Multi-signal clustering and alert compression."""

from __future__ import annotations

from datetime import timedelta

from datareliant.anomaly.models import AnomalyResult
from datareliant.common.types import IncidentStatus, Severity
from datareliant.incidents.models import Incident
from datareliant.lineage.graph import LineageGraph


class IncidentCorrelator:
    """Correlates multiple anomalies across time, lineage topology, and shared metrics into incidents."""

    def __init__(self, time_window_minutes: int = 30) -> None:
        self.time_window = timedelta(minutes=time_window_minutes)

    def correlate(
        self,
        anomalies: list[AnomalyResult],
        lineage_graph: LineageGraph | None = None,
        pipeline_id: str | None = None,
    ) -> list[Incident]:
        """Group anomalies into incidents based on temporal proximity and lineage dependency."""
        if not anomalies:
            return []

        # Sort anomalies chronologically
        sorted_anoms = sorted(anomalies, key=lambda a: a.detected_at)

        # Graph connectivity check helper
        def are_nodes_connected(n1: str | None, n2: str | None) -> bool:
            if not n1 or not n2:
                return False
            if n1 == n2:
                return True
            if lineage_graph is None:
                return False
            # Check if n1 is ancestor of n2, or n2 is ancestor of n1
            try:
                if lineage_graph.graph.has_node(n1) and lineage_graph.graph.has_node(n2):
                    p1 = lineage_graph.get_shortest_path(n1, n2)
                    p2 = lineage_graph.get_shortest_path(n2, n1)
                    return len(p1) > 0 or len(p2) > 0
            except Exception:
                pass
            return False

        # Cluster anomalies
        clusters: list[list[AnomalyResult]] = []

        for anom in sorted_anoms:
            assigned = False
            for cluster in clusters:
                # Compare with the most recent anomaly in this cluster
                last_anom = cluster[-1]
                time_diff = abs(anom.detected_at - last_anom.detected_at)

                if time_diff <= self.time_window:
                    # Check shared dataset/node, shared metric, or graph connection
                    same_dataset = (
                        anom.dataset_name is not None
                        and anom.dataset_name == last_anom.dataset_name
                    )
                    connected = are_nodes_connected(anom.node_id, last_anom.node_id)
                    same_node = anom.node_id is not None and anom.node_id == last_anom.node_id

                    if same_dataset or connected or same_node:
                        cluster.append(anom)
                        assigned = True
                        break

            if not assigned:
                clusters.append([anom])

        # Convert clusters to Incident objects
        incidents: list[Incident] = []
        for cluster in clusters:
            start_t = min(a.detected_at for a in cluster)
            end_t = max(a.detected_at for a in cluster)

            # Collect affected nodes and datasets
            affected = set()
            for a in cluster:
                if a.node_id:
                    affected.add(a.node_id)
                if a.dataset_name:
                    affected.add(a.dataset_name)

            # Determine maximum severity
            severities = [a.severity for a in cluster]
            if Severity.CRITICAL in severities or len(affected) >= 3:
                sev = Severity.CRITICAL
            elif Severity.HIGH in severities or len(cluster) >= 3:
                sev = Severity.HIGH
            elif Severity.MEDIUM in severities:
                sev = Severity.MEDIUM
            else:
                sev = Severity.LOW

            primary_node = next(iter(affected)) if affected else "pipeline"
            metrics_summary = ", ".join(list({a.metric for a in cluster})[:3])

            title = (
                f"Incident on {primary_node}: {len(cluster)} anomalies detected "
                f"across [{metrics_summary}]"
            )

            incidents.append(
                Incident(
                    title=title,
                    severity=sev,
                    status=IncidentStatus.OPEN,
                    start_time=start_t,
                    end_time=end_t,
                    pipeline_id=pipeline_id,
                    affected_nodes=sorted(affected),
                    anomaly_ids=[a.id for a in cluster],
                    anomalies=cluster,
                    metadata={"anomaly_count": len(cluster)},
                )
            )

        return incidents

    correlate_anomalies = correlate
