# ADR-0002: Dual Deterministic + Supervised ML for Explainable Root-Cause Analysis

## Status
Accepted

## Context
When data pipelines fail, engineers need immediate, explainable reasons why a table corrupted or an assertion failed. Black-box deep learning or non-deterministic LLM prompting can produce plausible-sounding hallucinations or ungrounded explanations without concrete provenance. Conversely, pure rigid heuristics fail to account for multi-stage graph propagation and historical incident recurrence.

## Decision
We implemented a **dual root-cause intelligence architecture**:
1. **Deterministic Multi-Signal Engine (`RootCauseEngine`)**: Weights explainable evidence across 6 standardized categories (Schema: 0.25, Lineage Graph: 0.20, Statistical: 0.20, Temporal: 0.15, Failure Propagation: 0.10, Historical Similarity: 0.10). Every score maps to concrete evidence items.
2. **Supervised ML Classification Layer (`MLRootCauseClassifier`)**: Trained on standardized 12-dimensional feature vectors (Logistic Regression, Random Forest, XGBoost) to cross-validate rankings and provide learned feature importances.

## Consequences
### Positive
- **100% Audit Provenance**: Every root-cause ranking provides an exact mathematical evidence breakdown and audit trail.
- **High Accuracy**: Evaluated on 13 controlled failure scenarios, the deterministic engine achieves 92.3% Top-3 accuracy with sub-10ms evaluation latency.
- **Reproducibility**: Experiments yield identical scores across runs with fixed random seeds.

### Negative
- Weight tuning requires empirical benchmarking across representative pipeline topologies.
