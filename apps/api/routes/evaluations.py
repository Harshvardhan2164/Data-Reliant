"""Evaluation and Benchmark REST API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from datareliant.evaluation.runner import SCENARIO_NAMES, EvaluationRunner

router = APIRouter()


class RunBenchmarkRequest(BaseModel):
    scenario: str = Field(default="all", description="Scenario name or 'all'")
    method: str = Field(default="engine", description="'engine', 'heuristic', or 'ml'")
    seed: int = Field(default=42, description="Random seed for data generation")


@router.get("/evaluations/scenarios", summary="List all benchmark failure scenarios")
async def list_benchmark_scenarios() -> dict[str, Any]:
    """Return all 13 supported failure scenarios available for evaluation."""
    return {
        "total_scenarios": len(SCENARIO_NAMES),
        "scenarios": SCENARIO_NAMES,
    }


@router.post("/evaluations/run", summary="Run benchmark on failure scenarios")
async def run_benchmark(request: RunBenchmarkRequest) -> dict[str, Any]:
    """Execute research benchmark across failure scenarios and return precision/recall metrics."""
    runner = EvaluationRunner(seed=request.seed)

    if request.scenario.lower() == "all":
        summary = runner.run_all(method=request.method)
        return summary.to_dict()

    if request.scenario not in SCENARIO_NAMES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown scenario '{request.scenario}'. Valid options: {SCENARIO_NAMES}",
        )

    result = runner.run_scenario(request.scenario, method=request.method)
    return result.model_dump(mode="json")


@router.get("/evaluations/compare", summary="Compare heuristic, engine, and ML methods")
async def compare_benchmark_methods(
    seed: int = Query(default=42, description="Random seed"),
) -> dict[str, Any]:
    """Run full benchmark comparing heuristic baseline, deterministic engine, and ML classifier."""
    runner = EvaluationRunner(seed=seed)
    comparison = runner.compare_methods()
    return {k: v.to_dict() for k, v in comparison.items()}
