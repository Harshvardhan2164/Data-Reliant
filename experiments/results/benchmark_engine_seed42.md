# Benchmark Evaluation Report: `datareliant_benchmark_engine`

## Summary Metrics
- **Total Scenarios Evaluated**: 13
- **Detection Recall**: 100.0%
- **Top-1 Root-Cause Accuracy**: 76.9%
- **Top-3 Root-Cause Accuracy**: 92.3%
- **Mean Alert Compression Ratio**: 1.23x
- **Mean Latency per Scenario**: 8.40 ms

## Detailed Scenario Results
| Scenario | True Root Cause | Predicted Top 1 | Top-1 Correct | Top-3 Correct | Detected | Anomaly Count | Latency (ms) |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `missing_rows` | `MISSING_DATA` | `MISSING_DATA` | PASS | PASS | PASS | 1 | 15.82 |
| `duplicate_rows` | `DUPLICATE_INGESTION` | `DUPLICATE_INGESTION` | PASS | PASS | PASS | 1 | 8.66 |
| `null_spike` | `NULL_SPIKE` | `NULL_SPIKE` | PASS | PASS | PASS | 1 | 6.22 |
| `schema_addition` | `SCHEMA_DRIFT` | `SCHEMA_DRIFT` | PASS | PASS | PASS | 1 | 5.67 |
| `schema_removal` | `SCHEMA_DRIFT` | `SCHEMA_DRIFT` | PASS | PASS | PASS | 1 | 7.86 |
| `datatype_change` | `TYPE_CHANGE` | `TYPE_CHANGE` | PASS | PASS | PASS | 1 | 6.29 |
| `range_violation` | `TRANSFORMATION_ERROR` | `TRANSFORMATION_ERROR` | PASS | PASS | PASS | 1 | 6.18 |
| `categorical_corruption` | `SOURCE_DATA_CHANGE` | `SOURCE_DATA_CHANGE` | PASS | PASS | PASS | 1 | 8.64 |
| `distribution_shift` | `DISTRIBUTION_SHIFT` | `DISTRIBUTION_SHIFT` | PASS | PASS | PASS | 1 | 10.64 |
| `timezone_shift` | `TIMEZONE_MISMATCH` | `UPSTREAM_FAILURE` | FAIL | PASS | PASS | 1 | 9.68 |
| `late_arrival` | `LATE_ARRIVAL` | `UPSTREAM_FAILURE` | FAIL | PASS | PASS | 1 | 7.61 |
| `upstream_failure` | `UPSTREAM_FAILURE` | `UPSTREAM_FAILURE` | PASS | PASS | PASS | 2 | 6.57 |
| `mixed_failure` | `TRANSFORMATION_ERROR` | `SCHEMA_DRIFT` | FAIL | FAIL | PASS | 3 | 9.41 |