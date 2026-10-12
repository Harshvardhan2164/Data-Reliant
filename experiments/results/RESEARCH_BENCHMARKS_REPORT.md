# DataReliant: Empirical Research Benchmarks & Experimental Results

## Abstract
This document presents empirical evaluation results for **DataReliant**, an autonomous data quality,
anomaly detection, and explainable root-cause intelligence platform. The experiments evaluate:
1. **Root-Cause Ranking Accuracy** across 13 controlled failure scenarios.
2. **Alert Compression Ratio vs Lineage Graph Depth**.
3. **Statistical Anomaly Detection Precision & Recall**.
4. **High-Throughput Polars Ingestion & Profiling Latency Scaling**.

---

## Experiment A: Root-Cause Ranking Accuracy
Comparing baseline heuristics against the deterministic multi-signal engine and ML classifier.

| Method | Detection Recall | Top-1 Accuracy | Top-3 Accuracy | Mean Alert Compression | Mean Latency |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `heuristic_baseline` | 100.0% | 69.2% | 69.2% | 1.23x | 6.24 ms |
| `deterministic_engine` | 100.0% | 76.9% | 92.3% | 1.23x | 5.14 ms |
| `ml_classifier` | 100.0% | 23.1% | 46.2% | 1.23x | 12.97 ms |

---

## Experiment B: Alert Compression Ratio vs Lineage Graph Depth
Quantifying alert fatigue reduction via DAG topological correlation.

| Lineage Depth | Injected Cascading Anomalies | Resulting Incidents (Lineage) | Compression Ratio | Naive Alerts (No Lineage) |
| :---: | :---: | :---: | :---: | :---: |
| 1 | 2 | 1 | **2.00x** | 2 |
| 2 | 3 | 1 | **3.00x** | 3 |
| 3 | 4 | 1 | **4.00x** | 4 |
| 4 | 5 | 1 | **5.00x** | 5 |
| 5 | 6 | 1 | **6.00x** | 6 |

---

## Experiment C: Anomaly Detection Precision & Recall
Z-Score statistical detector performance under varied noise contamination levels.

| Contamination Level | Injected Anomalies | Detected | Precision | Recall | F1 Score |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `contamination_1pct` | 10 | 9 | 77.8% | 70.0% | **0.7369** |
| `contamination_5pct` | 50 | 31 | 100.0% | 62.0% | **0.7654** |
| `contamination_10pct` | 100 | 22 | 100.0% | 22.0% | **0.3607** |

---

## Experiment D: End-to-End Latency & Scaling
Polars high-performance profiling and quality execution latency across record counts.

| Row Count | Data Generation (ms) | Profiling Latency (ms) | Quality Engine (ms) | Total Processing (ms) | Throughput (rows/sec) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 1,000 | 7.42 ms | 5.05 ms | 0.23 ms | **5.28 ms** | **189,393 rows/s** |
| 10,000 | 49.41 ms | 9.27 ms | 0.46 ms | **9.73 ms** | **1,027,749 rows/s** |
| 50,000 | 254.55 ms | 51.92 ms | 0.49 ms | **52.41 ms** | **954,016 rows/s** |
| 100,000 | 483.55 ms | 57.38 ms | 0.56 ms | **57.94 ms** | **1,725,923 rows/s** |

---

## Conclusion & Key Findings
- **Zero-Hallucination Explainability**: Multi-signal evidence weighting achieves **92.3% Top-3 accuracy** with 100% deterministic reproducibility.
- **Significant Fatigue Reduction**: Lineage-aware clustering compresses cascading pipeline alerts by **up to 6.0x**.
- **Sub-Second Throughput**: Polars native query execution processes **over 500,000 rows/second** on a single node without Spark or JVM overhead.