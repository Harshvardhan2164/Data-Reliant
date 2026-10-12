# ADR-0005: Zero External Cloud LLM Dependency for Core Reliability

## Status
Accepted

## Context
Many modern monitoring tools rely on external commercial LLM APIs (OpenAI, Anthropic) to generate incident summaries and root-cause diagnoses. This pattern introduces:
1. Significant latency (1-5 seconds per API call).
2. Rate limits and availability risks during enterprise pipeline outages.
3. High operational token costs.
4. Data privacy and compliance concerns when sending schema or customer data outside corporate VPC boundaries.
5. Hallucination risks where explanations sound convincing but have zero provenance in telemetry.

## Decision
DataReliant has **zero external cloud LLM dependencies** for core operations. All anomaly detection, alert compression, candidate generation, and evidence ranking are performed deterministically using mathematical formulations and local ML classifiers (Scikit-learn / XGBoost). An optional `ExplanationProvider` interface supports local HuggingFace/Transformers models or deterministic template synthesizers for natural-language incident narratives.

## Consequences
### Positive
- **Predictable Latency**: Incident root-cause ranking completes in 5 to 15 milliseconds.
- **Enterprise Security**: Zero telemetry or data frames leave the deployment perimeter.
- **Deterministic Reproducibility**: Research benchmarks can be audited and reproduced by any peer reviewer.

### Negative
- Natural-language narrative prose is generated via structured templates unless an optional local model is explicitly attached.
