# ADR-0004: Decoupled Multi-Cloud Adapters and Local-First Architecture

## Status
Accepted

## Context
Enterprise data teams operate across multiple cloud providers (AWS, GCP, Azure) and local development workstations. Tightly coupling the core data quality and root-cause engine to cloud SDKs (e.g. boto3, google-cloud-storage) prevents seamless local testing, increases CI execution times, and introduces vendor lock-in.

## Decision
We adopted a **strict local-first architecture**:
1. All core engine abstractions (`ingestion`, `profiling`, `quality`, `anomaly`, `lineage`, `rootcause`, `evaluation`) run locally with zero external network or cloud dependencies.
2. Cloud adapters (e.g. GCS, BigQuery) reside in isolated modules with lazy imports and graceful fallbacks.
3. Database persistence uses SQLAlchemy async with SQLite support for local unit testing and PostgreSQL for production deployments.

## Consequences
### Positive
- **100% Offline Reproducibility**: Unit tests and benchmarks execute entirely on developer workstations in seconds.
- **Portability**: The system can be deployed on bare metal, single Docker containers, Kubernetes, or cloud serverless environments (Cloud Run).

### Negative
- Cloud-specific optimized features (e.g. BigQuery storage read API) require separate adapter maintenance.
