from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tests.helpers.vnv import build_vnv_study
from tests.helpers.vnv_benchmark import build_cantilever_benchmark_source, build_torsion_benchmark_source


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _run(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "solveur.cli.main", *(str(item) for item in args)],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_vnv_cli_writes_markdown_and_exposes_pending_review(tmp_path: Path) -> None:
    study = build_vnv_study(tmp_path / "study")
    output = tmp_path / "output"
    completed = _run("vnv-compare", "--study", study, "--output", output)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "VNV PENDING_REVIEW" in completed.stdout
    assert "human decision: pending" in completed.stdout
    assert (output / "study_report.md").is_file()


def test_vnv_cli_can_require_human_approval(tmp_path: Path) -> None:
    pending = build_vnv_study(tmp_path / "pending")
    blocked = _run(
        "vnv-compare",
        "--study",
        pending,
        "--output",
        tmp_path / "pending_output",
        "--require-approval",
    )
    assert blocked.returncode == 4

    accepted = build_vnv_study(tmp_path / "accepted", decision="accepted")
    passed = _run(
        "vnv-compare",
        "--study",
        accepted,
        "--output",
        tmp_path / "accepted_output",
        "--require-approval",
    )
    assert passed.returncode == 0, passed.stdout + passed.stderr
    assert "VNV ACCEPTED" in passed.stdout


def test_vnv_cli_returns_qualification_rejection_for_failed_comparison(tmp_path: Path) -> None:
    study = build_vnv_study(tmp_path / "failed", qf_error_scale=2.0)
    completed = _run("vnv-compare", "--study", study, "--output", tmp_path / "failed_output")
    assert completed.returncode == 4
    assert "VNV FAIL" in completed.stdout


def test_vnv_cli_imports_existing_benchmark_with_png_artifacts(tmp_path: Path) -> None:
    source = build_cantilever_benchmark_source(tmp_path / "source")
    output = tmp_path / "study"
    completed = _run(
        "vnv-import-benchmark",
        "--case",
        "BM-SOL-CANTILEVER-001",
        "--source",
        source,
        "--output",
        output,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "VNV STUDY CREATED" in completed.stdout
    assert (output / "study.json").is_file()
    assert (output / "results" / "h4_qf_deformation.png").is_file()


def test_vnv_cli_imports_and_compares_torsion_benchmark(tmp_path: Path) -> None:
    source = build_torsion_benchmark_source(tmp_path / "source")
    study_dir = tmp_path / "study"
    imported = _run(
        "vnv-import-benchmark",
        "--case",
        "BM-SOL-TET4-TORSION-001",
        "--source",
        source,
        "--output",
        study_dir,
    )
    assert imported.returncode == 0, imported.stdout + imported.stderr
    assert "Saint-Venant" in imported.stdout

    compared = _run(
        "vnv-compare",
        "--study",
        study_dir / "study.json",
        "--output",
        tmp_path / "evidence",
        "--require-approval",
    )
    assert compared.returncode == 0, compared.stdout + compared.stderr
    assert "accepted_with_reservations" in compared.stdout
