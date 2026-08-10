"""Controlled benchmark checks for the BEAM2 element."""

from pathlib import Path

from solveur.benchmarks import BenchmarkRunner


def test_beam2_cantilever_benchmark_meets_internal_criteria(tmp_path: Path) -> None:
    run = BenchmarkRunner().run("BM-BEAM2-CANTILEVER-001", tmp_path)

    assert run.status == "WARNING"
    assert all(check["status"] == "PASS" for check in run.checks)
    assert len(run.metrics["convergence"]) == 5
    assert (tmp_path / run.descriptor.identifier / "benchmark_summary.json").is_file()
    assert (tmp_path / run.descriptor.identifier / "benchmark_manifest.json").is_file()
