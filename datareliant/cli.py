"""DataReliant CLI entry point.

Provides commands for data generation, evaluation, migration, and
server management.
"""

from __future__ import annotations

import json
from pathlib import Path

import click

from datareliant import __version__
from datareliant.evaluation.runner import SCENARIO_NAMES, EvaluationRunner
from generators.normal_data.enterprise import EnterpriseDataGenerator


@click.group()
@click.version_option(version=__version__, prog_name="datareliant")
def main() -> None:
    """DataReliant — Autonomous Data Quality & Root-Cause Intelligence."""


@main.command()
@click.option("--scenario", default="all", help="Scenario to evaluate (or 'all').")
@click.option("--method", default="engine", type=click.Choice(["engine", "heuristic", "ml", "compare"]), help="Method to evaluate.")
@click.option("--seed", default=42, type=int, help="Random seed for reproducibility.")
@click.option("--output-dir", default="experiments/results", help="Output directory for reports.")
def evaluate(scenario: str, method: str, seed: int, output_dir: str) -> None:
    """Run research evaluation against synthetic failure scenarios."""
    click.echo(f"[*] Running DataReliant benchmark: scenario={scenario}, method={method}, seed={seed}")
    runner = EvaluationRunner(seed=seed)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    if method == "compare":
        click.echo("Comparing Heuristic Baseline, Deterministic Engine, and ML Classifier...")
        comparisons = runner.compare_methods()
        comp_dict = {k: v.to_dict() for k, v in comparisons.items()}
        json_file = out_path / f"method_comparison_seed{seed}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(comp_dict, f, indent=2)

        for m_name, summary in comparisons.items():
            click.echo("\n" + runner.format_markdown_report(summary))
        click.echo(f"\n[+] Method comparison saved to: {json_file}")
        return

    if scenario.lower() == "all":
        summary = runner.run_all(method=method)
        md_report = runner.format_markdown_report(summary)
        click.echo("\n" + md_report)

        json_file = out_path / f"benchmark_{method}_seed{seed}.json"
        md_file = out_path / f"benchmark_{method}_seed{seed}.md"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(summary.to_dict(), f, indent=2)
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(md_report)
        click.echo(f"\n[+] Benchmark results saved to:\n  - {json_file}\n  - {md_file}")
    else:
        if scenario not in SCENARIO_NAMES:
            click.echo(f"[-] Error: Scenario '{scenario}' not recognized. Choose from: {SCENARIO_NAMES}", err=True)
            return
        result = runner.run_scenario(scenario, method=method)
        click.echo(f"Scenario: {result.scenario_type}")
        click.echo(f"True Root Cause: {result.true_root_cause}")
        click.echo(f"Predicted Top 1: {result.predicted_top_1} (Correct: {result.top_1_correct})")
        click.echo(f"Predicted Top 3: {result.predicted_top_3} (Correct: {result.top_3_correct})")
        click.echo(f"Compression: {result.anomaly_count} anomalies -> {result.compressed_incident_count} incidents ({result.compression_ratio}x)")
        click.echo(f"Latency: {result.time_to_detect_ms:.2f} ms")


@main.command()
@click.option("--rows", default=1000, type=int, help="Base transactions count to generate.")
@click.option("--seed", default=42, type=int, help="Random seed.")
@click.option("--output-dir", default="datasets/synthetic", help="Output directory.")
@click.option("--format", "file_format", default="csv", type=click.Choice(["csv", "parquet"]), help="File format.")
def generate(rows: int, seed: int, output_dir: str, file_format: str) -> None:
    """Generate synthetic enterprise datasets with relational integrity."""
    click.echo(f"[*] Generating enterprise synthetic data (seed={seed}, base_transactions={rows})...")
    generator = EnterpriseDataGenerator(seed=seed)
    n_customers = max(10, rows // 5)
    n_products = max(5, rows // 20)
    n_payments = int(rows * 0.95)

    datasets = generator.generate(
        n_customers=n_customers,
        n_products=n_products,
        n_transactions=rows,
        n_payments=n_payments,
    )

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    for name, df in datasets.items():
        if file_format == "parquet":
            file_path = out_path / f"{name}.parquet"
            df.write_parquet(file_path)
        else:
            file_path = out_path / f"{name}.csv"
            df.write_csv(file_path)
        click.echo(f"  - Written {name}: {df.height} rows -> {file_path}")

    click.echo(f"[+] Generated {len(datasets)} datasets into {out_path.resolve()}")


@main.command()
@click.option("--host", default="0.0.0.0", help="Bind host.")
@click.option("--port", default=8000, type=int, help="Bind port.")
@click.option("--reload", is_flag=True, help="Enable auto-reload.")
def serve(host: str, port: int, reload: bool) -> None:
    """Start the DataReliant API server."""
    import uvicorn

    uvicorn.run(
        "apps.api.main:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
