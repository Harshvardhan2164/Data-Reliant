# ADR-0001: Polars and PyArrow for Data Ingestion & Profiling

## Status
Accepted

## Context
Data quality profiling and validation across large tabular files (hundreds of thousands to millions of rows) is typically performed using Pandas or distributed engines like PySpark. However, Pandas exhibits high memory overhead (often 5-10x the raw file size) and single-threaded GIL constraints, while Spark introduces heavy JVM startup costs, cluster orchestration complexity, and substantial latency for interactive investigation workflows.

## Decision
We chose **Polars** (built on Apache Arrow in Rust) and **PyArrow** as the primary execution engine for all data ingestion, profiling, rule evaluation, and drift detection in DataReliant.

## Consequences
### Positive
- **High Throughput**: Multi-threaded query execution achieves over 1.7 million rows/second processing speed on a single machine.
- **Memory Efficiency**: Zero-copy Arrow integration minimizes RAM consumption, allowing large enterprise datasets to be profiled locally without out-of-memory errors.
- **Rich Expression DSL**: Polars columnar expressions allow expressive, vectorized rule evaluations without Python bytecode loops.

### Negative
- Users accustomed to Pandas syntax must use Polars idioms (e.g. `pl.col(...)`, `pl.lit(...)`).
