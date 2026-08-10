from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from solveur.api import list_benchmarks, run_benchmark


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_benchmarks_api_and_cli_catalog_agree() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "solveur.cli.main", "benchmarks", "--json"],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    cli_ids = {row["identifier"] for row in json.loads(completed.stdout)}
    assert cli_ids == {item.identifier for item in list_benchmarks()}


def test_patch_benchmark_runs_through_api_and_cli(tmp_path: Path) -> None:
    pytest.importorskip("gmsh")
    api_root = tmp_path / "api"
    run = run_benchmark("BM-SOL-TET4-PATCH-001", api_root)
    assert run.status == "PASS"
    assert (api_root / run.descriptor.identifier / "benchmark_manifest.json").is_file()

    cli_root = tmp_path / "cli"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "solveur.cli.main",
            "benchmark",
            "--case",
            "BM-SOL-TET4-PATCH-001",
            "--output",
            str(cli_root),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "BENCHMARK PASS" in completed.stdout
    summary = json.loads(
        (cli_root / "BM-SOL-TET4-PATCH-001" / "benchmark_summary.json").read_text(encoding="utf-8")
    )
    assert summary["status"] == "PASS"

