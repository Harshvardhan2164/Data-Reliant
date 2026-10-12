# DataReliant 🛡️
### Autonomous Data Quality, Anomaly Detection & Root-Cause Intelligence Platform

[![CI](https://github.com/datareliant/datareliant/actions/workflows/ci.yml/badge.svg)](https://github.com/datareliant/datareliant/actions/workflows/ci.yml)
[![Python 3.11 | 3.12](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Benchmark Top-3 Accuracy](https://img.shields.io/badge/Benchmark%20Top--3%20Accuracy-92.3%25-brightgreen.svg)](experiments/results/RESEARCH_BENCHMARKS_REPORT.md)

---

## Overview

**DataReliant** is a production-grade, research-oriented platform for autonomous data quality monitoring, statistical and temporal anomaly detection, DAG-based pipeline lineage tracing, alert compression, and explainable root-cause intelligence.

It is **NOT** a toy dashboard, simple CRUD application, generic EDA tool, or commercial LLM wrapper. All anomaly detection, alert compression, and root-cause analysis run with **zero external cloud LLM dependencies**, guaranteeing deterministic reproducibility, sub-15ms inference latency, zero hallucinations, and complete data privacy.

---

## Key Highlights

- ⚡ **Ultra-Fast Polars Engine**: Vectorized multi-threaded profiling and validation processing **over 1.7 million rows/second** on a single node without Spark or JVM overhead.
- 🎯 **Explainable Root-Cause Intelligence**: Multi-signal evidence weighting across 6 categories (Schema: 0.25, Lineage Graph: 0.20, Statistical: 0.20, Temporal: 0.15, Propagation: 0.10, Historical: 0.10) achieving **92.3% Top-3 Accuracy** across 13 failure scenarios.
- 🗜️ **Up to 6.0x Alert Compression**: NetworkX DAG lineage topology and temporal clustering compress cascading pipeline failures into isolated, actionable incidents.
- 🧪 **Failure Injection Laboratory**: 13 controlled synthetic failure scenarios with known ground truth for empirical reproducibility.
- 🖥️ **Full-Featured React Dashboard**: 11 dedicated views with custom vanilla CSS dark glassmorphic design, interactive SVG DAG lineage visualizer, and live benchmark lab.
- ☁️ **Local-First & Multi-Cloud Ready**: Completely local-first for offline development; decoupled adapters for Google Cloud Storage, BigQuery, and Terraform Cloud Run.

---

## System Architecture

```
                   ┌──────────────────────────────────────────────┐
                   │             DATA SOURCES & SENSORS           │
                   │  (CSV, Parquet, PostgreSQL, BigQuery, GCS)   │
                   └──────────────────────┬───────────────────────┘
                                          │
                                          ▼
                   ┌──────────────────────────────────────────────┐
                   │        HIGH-THROUGHPUT PROFILER & RULES      │
                   │     (Polars Vectorized Ingestion Engine)     │
                   └──────────────────────┬───────────────────────┘
                                          │
                                          ▼
                   ┌──────────────────────────────────────────────┐
                   │        MULTI-SIGNAL ANOMALY DETECTORS        │
                   │   Point: Z-Score, IQR, EWMA, Isolation Forest│
                   │   Distribution: KS-Test, PSI, Jensen-Shannon │
                   │   Temporal: Trend, Seasonality, Change-Point │
                   └──────────────────────┬───────────────────────┘
                                          │
                                          ▼
                   ┌──────────────────────────────────────────────┐
                   │         LINEAGE & INCIDENT CORRELATION       │
                   │    (NetworkX DAG Traversal, Alert Squeezer)  │
                   └──────────────────────┬───────────────────────┘
                                          │
                                          ▼
                   ┌──────────────────────────────────────────────┐
                   │        ROOT-CAUSE INTELLIGENCE ENGINE        │
                   │   - Deterministic 6-Signal Evidence Ranker   │
                   │   - Supervised ML (LogReg, RF, XGBoost)      │
                   │   - Cosine Similarity Historical Matching    │
                   └──────────────────────┬───────────────────────┘
                                          │
                                          ▼
                   ┌──────────────────────────────────────────────┐
                   │            EXPLANATION & FRONTEND            │
                   │    - Rule-based / Local LLM Playbooks        │
                   │    - FastAPI Async REST API                  │
                   │    - React Glassmorphic 11-View Dashboard    │
                   └──────────────────────────────────────────────┘
```

---

## Empirical Benchmark Results

Evaluated across 13 controlled failure injection scenarios with fixed random seeds (`seed=42`):

| Evaluation Metric | Baseline Heuristic | Deterministic Engine (Ours) | Supervised ML (RF) |
| :--- | :---: | :---: | :---: |
| **Detection Recall** | 100.0% | **100.0%** | 100.0% |
| **Top-1 Root-Cause Accuracy** | 69.2% | **76.9%** | 84.6% |
| **Top-3 Root-Cause Accuracy** | 69.2% | **92.3%** | 92.3% |
| **Mean Alert Compression** | 1.00x | **1.23x (up to 6.0x)** | 1.23x |
| **Mean Evaluation Latency** | 6.2 ms | **5.1 ms** | 12.9 ms |

*Full scientific report available at [`experiments/results/RESEARCH_BENCHMARKS_REPORT.md`](experiments/results/RESEARCH_BENCHMARKS_REPORT.md).*

---

## 13 Controlled Failure Scenarios

DataReliant includes a built-in failure injection laboratory with known ground truth:

1. `missing_rows`: Massive row count drops simulating upstream extraction cut-offs.
2. `duplicate_rows`: Double-ingestion retry bug creating duplicate records.
3. `null_spike`: Producer schema breakage injecting unexpected nulls.
4. `schema_addition`: Unannounced metadata column appended upstream.
5. `schema_removal`: Breaking schema deletion of a critical production column.
6. `datatype_change`: Numeric or datetime column cast into strings.
7. `range_violation`: Outlier multipliers (20x) corrupting continuous domains.
8. `categorical_corruption`: Illegal discrete codes violating enum domain constraints.
9. `distribution_shift`: Mean and variance shift detected via KS-test / PSI.
10. `timezone_shift`: Unhandled UTC timezone offset gap.
11. `late_arrival`: Delayed partition records backdated by multiple weeks.
12. `upstream_failure`: Truncation of parent table breaking downstream foreign keys.
13. `mixed_failure`: Compound multi-signal anomaly (nulls + categories + schema drift).

---

## Quickstart

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/datareliant/datareliant.git
cd datareliant

# Create virtual environment and install
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[all,test]"
```

### 2. Generate Synthetic Enterprise Data

```bash
# Generate 1,000 transaction records with relational integrity
datareliant generate --rows 1000 --output-dir datasets/sample
```

### 3. Run Research Evaluation Benchmarks

```bash
# Run benchmark on a specific failure scenario
datareliant evaluate --scenario null_spike --method engine

# Run benchmark on all 13 failure scenarios
datareliant evaluate --scenario all --method engine

# Compare Heuristic vs Deterministic vs ML methods
datareliant evaluate --method compare
```

### 4. Start the FastAPI API Server

```bash
datareliant serve --host 0.0.0.0 --port 8000 --reload
# API docs available at: http://localhost:8000/docs
```

### 5. Start the React Web Dashboard

```bash
cd apps/web
npm install
npm run dev
# Dashboard available at: http://localhost:5173
```

---

## Architecture Decision Records (ADRs)

Design decisions and scientific trade-offs are documented in [`docs/decisions/`](docs/decisions/):
- [`ADR-0001`](docs/decisions/0001-polars-and-pyarrow-for-ingestion-and-profiling.md): Polars & PyArrow for High-Throughput Vectorized Ingestion
- [`ADR-0002`](docs/decisions/0002-deterministic-multi-signal-and-supervised-ml-root-cause.md): Dual Deterministic + Supervised ML for Explainable Root-Cause Analysis
- [`ADR-0003`](docs/decisions/0003-networkx-dag-for-in-memory-lineage-and-blast-radius.md): NetworkX Directed Graph Engine for In-Memory Lineage & Blast Radius
- [`ADR-0004`](docs/decisions/0004-decoupled-cloud-adapters-and-local-first-architecture.md): Decoupled Multi-Cloud Adapters and Local-First Architecture
- [`ADR-0005`](docs/decisions/0005-zero-external-llm-dependency-for-reliability.md): Zero External Cloud LLM Dependency for Reliability

---

## Running Tests

```bash
# Run all unit and integration tests (125 tests passing)
pytest tests/unit/ -v

# Run with test coverage
pytest tests/unit/ -v --cov=datareliant --cov-report=term
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
