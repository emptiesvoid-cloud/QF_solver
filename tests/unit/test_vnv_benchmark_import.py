from __future__ import annotations

from pathlib import Path

import pytest

from solveur.api import import_cantilever_vnv_study, import_torsion_vnv_study, run_vnv_study
from solveur.core.errors import InputValidationError
from tests.helpers.vnv_benchmark import build_cantilever_benchmark_source, build_torsion_benchmark_source


def test_cantilever_benchmark_import_creates_png_vtu_and_a_passing_vnv_study(tmp_path: Path) -> None:
    source = build_cantilever_benchmark_source(tmp_path / "source")
    study_dir = tmp_path / "study"

    study = import_cantilever_vnv_study(study_dir, source_dir=source)
    run = run_vnv_study(study, tmp_path / "evidence")

    assert study.is_file()
    assert run.automated_verdict == "PASS"
    assert run.status == "PENDING_REVIEW"
    assert len(run.study.levels) == 4
    assert run.convergence[0]["observed_order"] == pytest.approx(2.0)
    for level in range(1, 5):
        assert (study_dir / "results" / f"h{level}_qf_deformation.png").stat().st_size > 1000
        assert (study_dir / "results" / f"h{level}_qf_deformation.vtu").is_file()
        assert (study_dir / "references" / f"h{level}_timoshenko.json").is_file()
    assert (study_dir / "references" / "timoshenko_deformation.png").stat().st_size > 1000
    assert (study_dir / "references" / "timoshenko_deformation.vtu").is_file()
    report = (tmp_path / "evidence" / "study_report.md").read_text(encoding="utf-8")
    assert "Reference analytique Timoshenko" in report
    assert "![Deformee QF_solver]" in report
    assert "![Deformee reference]" in report


def test_cantilever_benchmark_import_requires_known_source_and_explicit_overwrite(tmp_path: Path) -> None:
    with pytest.raises(InputValidationError, match="Cannot find"):
        import_cantilever_vnv_study(tmp_path / "missing", source_dir=tmp_path / "unknown")

    source = build_cantilever_benchmark_source(tmp_path / "source")
    output = tmp_path / "study"
    import_cantilever_vnv_study(output, source_dir=source)
    with pytest.raises(InputValidationError, match="not empty"):
        import_cantilever_vnv_study(output, source_dir=source)
    assert import_cantilever_vnv_study(output, source_dir=source, overwrite=True).is_file()


def test_torsion_benchmark_import_creates_paired_deformations_and_passing_study(tmp_path: Path) -> None:
    source = build_torsion_benchmark_source(tmp_path / "source")
    study_dir = tmp_path / "study"

    study = import_torsion_vnv_study(study_dir, source_dir=source)
    run = run_vnv_study(study, tmp_path / "evidence")

    assert run.automated_verdict == "PASS"
    assert run.owner_decision == "accepted_with_reservations"
    assert len(run.study.levels) == 4
    assert run.convergence[0]["observed_order"] == pytest.approx(1.0)
    assert run.convergence[0]["finest_error"] == pytest.approx(0.02)
    for level in range(1, 5):
        assert (study_dir / "results" / f"h{level}_qf_deformation.png").stat().st_size > 1000
        assert (study_dir / "references" / f"h{level}_saint_venant_deformation.png").stat().st_size > 1000
        assert (study_dir / "references" / f"h{level}_saint_venant_deformation.vtu").is_file()
    assert "C:\\Users" not in (study_dir / "source" / "source_manifest.json").read_text(encoding="utf-8")
    report = (tmp_path / "evidence" / "study_report.md").read_text(encoding="utf-8")
    assert "Saint-Venant" in report
    assert "accepted_with_reservations" in report
