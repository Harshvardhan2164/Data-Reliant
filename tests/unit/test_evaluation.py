"""Unit tests for Evaluation Framework and Benchmark Runner (Phase 14)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.main import app
from datareliant.evaluation.runner import SCENARIO_NAMES, EvaluationRunner


class TestEvaluationFramework:
    """Test the research evaluation suite and scenario benchmarking."""

    @pytest.fixture
    def runner(self) -> EvaluationRunner:
        return EvaluationRunner(seed=42)

    def test_scenario_names_complete(self):
        """Ensure all 13 required failure injection scenarios are covered."""
        assert len(SCENARIO_NAMES) == 13
        assert "missing_rows" in SCENARIO_NAMES
        assert "null_spike" in SCENARIO_NAMES
        assert "upstream_failure" in SCENARIO_NAMES
        assert "schema_addition" in SCENARIO_NAMES

    def test_run_single_scenario_missing_rows(self, runner: EvaluationRunner):
        res = runner.run_scenario("missing_rows", method="engine")
        assert res.scenario_type == "missing_rows"
        assert res.detected is True
        assert res.true_root_cause.upper() == "MISSING_DATA"
        assert res.top_1_correct is True
        assert res.time_to_detect_ms > 0

    def test_run_single_scenario_null_spike(self, runner: EvaluationRunner):
        res = runner.run_scenario("null_spike", method="engine")
        assert res.scenario_type == "null_spike"
        assert res.detected is True
        assert res.true_root_cause.upper() == "NULL_SPIKE"
        assert res.top_1_correct is True
        assert res.compression_ratio >= 1.0

    def test_run_single_scenario_upstream_failure(self, runner: EvaluationRunner):
        res = runner.run_scenario("upstream_failure", method="engine")
        assert res.scenario_type == "upstream_failure"
        assert res.detected is True
        assert res.anomaly_count == 2
        assert res.top_1_correct is True or res.top_3_correct is True

    def test_run_all_scenarios_deterministic_engine(self, runner: EvaluationRunner):
        summary = runner.run_all(method="engine")
        assert summary.total_scenarios == 13
        assert summary.detection_recall == 1.0  # 100% of injected failures detected
        assert summary.top_1_accuracy >= 0.70
        assert summary.top_3_accuracy >= 0.85
        assert summary.mean_compression_ratio >= 1.0

    def test_compare_methods(self, runner: EvaluationRunner):
        comparison = runner.compare_methods()
        assert "heuristic_baseline" in comparison
        assert "deterministic_engine" in comparison
        assert "ml_classifier" in comparison

        det = comparison["deterministic_engine"]
        assert det.total_scenarios == 13
        assert det.top_1_accuracy >= 0.70

    def test_markdown_report_generation(self, runner: EvaluationRunner):
        res = runner.run_all(method="engine")
        md = runner.format_markdown_report(res)
        assert "# Benchmark Evaluation Report" in md
        assert "Detection Recall" in md
        assert "| Scenario |" in md


class TestEvaluationAPIRoutes:
    """Test FastAPI evaluation and benchmark endpoints."""

    @pytest.mark.asyncio
    async def test_list_scenarios_endpoint(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/evaluations/scenarios")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total_scenarios"] == 13
            assert len(data["scenarios"]) == 13

    @pytest.mark.asyncio
    async def test_run_single_scenario_endpoint(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {"scenario": "null_spike", "method": "engine", "seed": 42}
            resp = await client.post("/api/v1/evaluations/run", json=payload)
            assert resp.status_code == 200
            data = resp.json()
            assert data["scenario_type"] == "null_spike"
            assert data["detected"] is True
            assert data["top_1_correct"] is True

    @pytest.mark.asyncio
    async def test_run_invalid_scenario_endpoint(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {"scenario": "nonexistent_failure"}
            resp = await client.post("/api/v1/evaluations/run", json=payload)
            assert resp.status_code == 400
