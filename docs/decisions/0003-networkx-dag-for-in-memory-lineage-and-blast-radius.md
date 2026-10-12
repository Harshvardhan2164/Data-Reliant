# ADR-0003: NetworkX Directed Graph Engine for In-Memory Lineage & Blast Radius

## Status
Accepted

## Context
Understanding how data corruptions cascade requires querying pipeline dependency DAGs (Directed Acyclic Graphs). External graph databases (such as Neo4j) introduce operational complexity, network round-trips, and infrastructure costs for what is fundamentally an in-memory topological traversal problem.

## Decision
We utilize **NetworkX** (`networkx.DiGraph`) to manage in-memory lineage graphs loaded from declarative YAML definitions or database registrations.

## Consequences
### Positive
- **Instantaneous Traversal**: BFS ancestor and descendant traversals, lowest common ancestor (LCA), and shortest dependency path calculations execute in microseconds.
- **Topological Alert Compression**: Incident correlator groups multi-table anomalies into single incidents using direct graph connectivity, achieving 2x to 6x alert compression.
- **D3.js Interoperability**: Graph structures export directly to standard D3.js node-link dictionaries for frontend visualization.

### Negative
- Extremely large graphs with millions of table-level nodes may require persistent graph storage, though enterprise pipeline DAGs rarely exceed a few thousand nodes.
