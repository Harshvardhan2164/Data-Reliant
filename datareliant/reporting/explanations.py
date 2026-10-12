"""Explanation Providers: Pluggable deterministic rule-based and local LLM explanation engine.

Generates executive summaries, evidence syntheses, and remediation playbooks for incidents.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from datareliant.incidents.models import Incident
    from datareliant.rootcause.models import RootCauseCandidate


class ExplanationReport(BaseModel):
    """Structured, human-readable root-cause investigation report and playbook."""

    incident_id: str
    title: str
    top_root_cause: str
    confidence: float
    executive_summary: str
    evidence_synthesis: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    provider_name: str

    def to_dict(self) -> dict[str, Any]:
        """Return dictionary representation."""
        return self.model_dump(mode="json")


class ExplanationProvider(ABC):
    """Abstract interface for incident explanation and narrative synthesis."""

    @abstractmethod
    def generate_explanation(
        self,
        incident: Incident,
        candidates: list[RootCauseCandidate],
    ) -> ExplanationReport:
        """Generate human-readable explanation and remediation playbook."""


class RuleBasedExplanationProvider(ExplanationProvider):
    """Deterministic, research-oriented explainer generating structured audit reports without LLM latency."""

    def __init__(self, name: str = "deterministic_rule_based") -> None:
        self.name = name

    def generate_explanation(
        self,
        incident: Incident,
        candidates: list[RootCauseCandidate],
    ) -> ExplanationReport:
        top_cause = candidates[0].root_cause_type.value if candidates else "UNKNOWN"
        confidence = candidates[0].confidence if candidates else 0.5
        top_candidate = candidates[0] if candidates else None

        # Build executive summary
        node_str = ", ".join(incident.affected_nodes) if incident.affected_nodes else "pipeline"
        summary = (
            f"Incident '{incident.title}' was triggered by {len(incident.anomalies)} correlated anomalies "
            f"across [{node_str}]. The primary identified root cause is {top_cause} with "
            f"{int(confidence * 100)}% explainable confidence."
        )

        # Synthesize evidence
        evidence_items: list[str] = []
        if top_candidate:
            evidence_items.extend(
                [
                    e.description if hasattr(e, "description") else str(e)
                    for e in top_candidate.evidence_items
                ]
            )
            for cat, score in top_candidate.evidence_breakdown.items():
                evidence_items.append(
                    f"Category '{cat.capitalize()}' signal strength: {int(score * 100)}%"
                )

        # Tailored playbooks per root cause
        playbooks: dict[str, list[str]] = {
            "NULL_SPIKE": [
                "1. Inspect recent upstream schema or API extractor changes for unhandled null fields.",
                "2. Check if default fallback or coalescing was removed in transformation code.",
                "3. Apply quarantined filter or trigger automated pipeline retry with previous valid batch.",
            ],
            "UPSTREAM_FAILURE": [
                "1. Check health and SLAs of upstream source parent tables.",
                "2. Verify network connectivity, batch cron triggers, or upstream producer job logs.",
                "3. Pause downstream analytics refresh until upstream table is backfilled.",
            ],
            "DUPLICATE_INGESTION": [
                "1. Audit pipeline ingestion triggers for duplicate retries without deduplication keys.",
                "2. Check message queue acknowledgment timeouts or consumer offset drift.",
                "3. Run distinct deduplication job on primary key to restore single-record state.",
            ],
            "SCHEMA_DRIFT": [
                "1. Review recent pull requests or producer database migrations.",
                "2. Compare source catalog against registered schema contract.",
                "3. Update downstream pipeline parser or rollback uncoordinated schema mutation.",
            ],
            "TYPE_CHANGE": [
                "1. Identify producer column type change (e.g. integer to string or float widening).",
                "2. Verify serialization format (JSON stringification or Parquet schema evolution).",
                "3. Add explicit type casting in ingestion adapter to preserve contract integrity.",
            ],
            "DISTRIBUTION_SHIFT": [
                "1. Verify if real-world external event caused metric shift (e.g. promo campaign, holiday).",
                "2. Run two-sample Kolmogorov-Smirnov test to verify statistical significance.",
                "3. Retrain downstream ML models or update dynamic threshold boundaries.",
            ],
        }

        actions = playbooks.get(
            top_cause,
            [
                "1. Inspect the earliest anomalous metric in incident timeline.",
                "2. Review pipeline DAG lineage to isolate failure origin.",
                "3. Run data quality suites on upstream parent nodes.",
            ],
        )

        return ExplanationReport(
            incident_id=incident.id,
            title=incident.title,
            top_root_cause=top_cause,
            confidence=round(confidence, 4),
            executive_summary=summary,
            evidence_synthesis=evidence_items,
            recommended_actions=actions,
            provider_name=self.name,
        )


class LocalLLMExplanationProvider(ExplanationProvider):
    """Optional local HuggingFace / Transformers explanation provider with deterministic fallback."""

    def __init__(
        self,
        model_name_or_path: str = "google/flan-t5-small",
        fallback_provider: ExplanationProvider | None = None,
    ) -> None:
        self.model_name = model_name_or_path
        self.fallback = fallback_provider or RuleBasedExplanationProvider()
        self._pipeline: Any = None

    def _init_local_model(self) -> Any:
        if self._pipeline is not None:
            return self._pipeline
        try:
            from transformers import pipeline  # type: ignore[import-untyped]

            self._pipeline = pipeline("text2text-generation", model=self.model_name)
            return self._pipeline
        except Exception:
            return None

    def generate_explanation(
        self,
        incident: Incident,
        candidates: list[RootCauseCandidate],
    ) -> ExplanationReport:
        pipe = self._init_local_model()
        if pipe is None:
            # Fall back transparently to rule-based explainer
            report = self.fallback.generate_explanation(incident, candidates)
            report.provider_name = f"local_llm_fallback ({self.fallback.__class__.__name__})"
            return report

        try:
            prompt = (
                f"Summarize data incident: Title: {incident.title}. "
                f"Anomalies: {len(incident.anomalies)}. Top root cause: {candidates[0].root_cause_type.value}."
            )
            out = pipe(prompt, max_length=120)
            generated_text = out[0].get("generated_text", "")
            base = self.fallback.generate_explanation(incident, candidates)
            base.executive_summary = generated_text or base.executive_summary
            base.provider_name = f"local_llm ({self.model_name})"
            return base
        except Exception:
            return self.fallback.generate_explanation(incident, candidates)
