from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import solveur.large.optimization as optimization
from solveur.large.optimization import (
    _binary_relative_error,
    _preconditioner_markdown,
    _scaling_markdown,
    _validated_preconditioners,
    analyze_large_scaling,
)
from solveur.large.solver import _automatic_petsc_options


def _write_displacements(directory: Path, values: np.ndarray) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "displacements.bin"
    np.asarray(values, dtype=np.float64).tofile(path)
    metadata = {
        "format": "qf_solver_mpi_binary_v1",
        "dtype": "float64",
        "byte_order": "little" if np.little_endian else "big",
        "shape": [values.size // 3, 3],
        "flat_size": int(values.size),
    }
    (directory / "displacements_metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    return path


def _write_benchmark(path: Path, *, ranks: int, dofs: int, time: float) -> Path:
    data = {
        "status": "PASS",
        "ndof": dofs,
        "element_count": dofs,
        "solve_pipeline_time_seconds": time,
        "assembly_time_seconds": time * 0.4,
        "solve_time_seconds": time * 0.5,
        "solver": {"iterations": 20, "residual_norm": 1.0e-10},
        "mpi": {"size": ranks},
        "memory_telemetry": {"process_peak_rss_bytes": 1000 * ranks},
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_binary_relative_error_is_chunked_and_exact(tmp_path: Path) -> None:
    reference_values = np.linspace(1.0, 3.0, 30)
    candidate_values = reference_values.copy()
    candidate_values[7] += 0.2
    reference = _write_displacements(tmp_path / "reference", reference_values)
    candidate = _write_displacements(tmp_path / "candidate", candidate_values)

    error = _binary_relative_error(reference, candidate, chunk_values=4)

    assert np.isclose(error, np.linalg.norm(reference_values - candidate_values) / np.linalg.norm(reference_values))


def test_strong_scaling_report_computes_speedup_and_efficiency(tmp_path: Path) -> None:
    paths = (
        _write_benchmark(tmp_path / "r1.json", ranks=1, dofs=1200, time=12.0),
        _write_benchmark(tmp_path / "r2.json", ranks=2, dofs=1200, time=7.0),
        _write_benchmark(tmp_path / "r4.json", ranks=4, dofs=1200, time=4.0),
    )

    result = analyze_large_scaling(paths, tmp_path / "report", mode="strong")

    assert result["status"] == "PASS"
    assert result["runs"][2]["speedup"] == pytest.approx(3.0)
    assert result["runs"][2]["strong_efficiency"] == pytest.approx(0.75)
    assert (tmp_path / "report" / "large_scaling.md").is_file()
    assert (tmp_path / "report" / "evidence_manifest.json").is_file()


def test_weak_scaling_report_uses_constant_work_per_rank(tmp_path: Path) -> None:
    paths = (
        _write_benchmark(tmp_path / "r1.json", ranks=1, dofs=1000, time=10.0),
        _write_benchmark(tmp_path / "r2.json", ranks=2, dofs=2000, time=11.0),
        _write_benchmark(tmp_path / "r4.json", ranks=4, dofs=4000, time=12.5),
    )

    result = analyze_large_scaling(paths, tmp_path / "report", mode="weak")

    assert result["runs"][2]["weak_efficiency"] == pytest.approx(0.8)
    assert result["minimum_efficiency"] == pytest.approx(0.8)


def test_scaling_report_warns_below_efficiency_threshold(tmp_path: Path) -> None:
    paths = (
        _write_benchmark(tmp_path / "r1.json", ranks=1, dofs=1000, time=10.0),
        _write_benchmark(tmp_path / "r2.json", ranks=2, dofs=2000, time=20.0),
    )

    result = analyze_large_scaling(paths, tmp_path / "report", mode="weak")

    assert result["status"] == "WARNING"
    assert result["minimum_efficiency"] == pytest.approx(0.5)


def test_scaling_rejects_invalid_campaigns(tmp_path: Path) -> None:
    first = _write_benchmark(tmp_path / "first.json", ranks=1, dofs=1000, time=10.0)
    second = _write_benchmark(tmp_path / "second.json", ranks=2, dofs=1000, time=8.0)
    with pytest.raises(ValueError, match="at least two"):
        analyze_large_scaling((first,), tmp_path / "one", mode="strong")
    with pytest.raises(ValueError, match="work per rank"):
        analyze_large_scaling((first, second), tmp_path / "weak", mode="weak")
    with pytest.raises(ValueError, match="Scaling mode"):
        analyze_large_scaling((first, second), tmp_path / "invalid", mode="other")


def test_preconditioner_names_are_nonempty_and_unique() -> None:
    assert _validated_preconditioners(("GAMG", " hypre ")) == ("gamg", "hypre")
    with pytest.raises(ValueError, match="unique"):
        _validated_preconditioners(("gamg", "GAMG"))
    with pytest.raises(ValueError, match="non-empty"):
        _validated_preconditioners(())


def test_gamg_repartition_is_automatic_only_for_four_or_more_ranks() -> None:
    assert _automatic_petsc_options("gamg", 4, explicit_keys=set(), existing_keys=set()) == {
        "pc_gamg_repartition": True
    }
    assert _automatic_petsc_options("gamg", 2, explicit_keys=set(), existing_keys=set()) == {}
    assert _automatic_petsc_options(
        "gamg", 4, explicit_keys={"pc_gamg_repartition"}, existing_keys=set()
    ) == {}
    assert _automatic_petsc_options(
        "gamg", 4, explicit_keys=set(), existing_keys={"pc_gamg_repartition"}
    ) == {}
    assert _automatic_petsc_options("hypre", 4, explicit_keys=set(), existing_keys=set()) == {}


def test_scaling_markdown_and_preconditioner_markdown_render_optional_metrics() -> None:
    preconditioner = _preconditioner_markdown(
        {
            "status": "WARNING",
            "runs": [
                {
                    "preconditioner": "gamg",
                    "ranks": 2,
                    "pipeline_time_seconds": 1.0,
                    "ksp_setup_time_seconds": None,
                    "ksp_iteration_time_seconds": 0.5,
                    "iterations": None,
                    "residual_norm": None,
                    "peak_rss_per_rank_bytes": None,
                    "relative_displacement_error": None,
                }
            ],
        }
    )
    scaling = _scaling_markdown(
        {
            "mode": "weak",
            "status": "PASS",
            "runs": [
                {
                    "ranks": 1,
                    "dofs": 100,
                    "dofs_per_rank": 100.0,
                    "pipeline_time_seconds": 1.0,
                    "speedup": 1.0,
                    "weak_efficiency": 1.0,
                    "iterations": None,
                    "peak_rss_per_rank_bytes": None,
                }
            ],
        }
    )
    assert "gamg" in preconditioner
    assert "Scalabilite weak" in scaling
    assert "| 1 | 100 |" in scaling


def test_preconditioner_campaign_archives_comparison_with_controlled_backend(tmp_path, monkeypatch) -> None:
    def fake_benchmark(input_path, output_dir, **kwargs):
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        values = np.asarray([1.0, 2.0, 3.0], dtype=np.float64)
        values.tofile(output_dir / "displacements.bin")
        metadata = {"dtype": "float64", "byte_order": "little", "shape": [1, 3], "flat_size": 3}
        (output_dir / "displacements_metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
        return {
            "status": "PASS",
            "evidence_verification": {"status": "PASS"},
            "ndof": 3,
            "mpi": {"size": 1},
            "solve_pipeline_time_seconds": 1.0,
            "assembly_time_seconds": 0.2,
            "solver": {"setup_time_seconds": 0.1, "iteration_time_seconds": 0.3, "iterations": 2, "residual_norm": 1.0e-10},
            "memory_telemetry": {"process_peak_rss_bytes": 1000},
        }

    monkeypatch.setattr(optimization, "benchmark_large_model", fake_benchmark)
    monkeypatch.setattr(optimization, "_mpi_rank", lambda: 0)
    monkeypatch.setattr(optimization, "write_large_manifest", lambda root, payload: root / "evidence_manifest.json")

    result = optimization.run_large_preconditioner_campaign(
        "model.h5",
        tmp_path / "campaign",
        preconditioners=("gamg", "hypre"),
    )

    assert result["status"] == "PASS"
    assert result["runs"][1]["relative_displacement_error"] == pytest.approx(0.0)
    assert (tmp_path / "campaign" / "preconditioner_comparison.json").is_file()
    assert (tmp_path / "campaign" / "preconditioner_comparison.md").is_file()


def test_scaling_report_rejects_invalid_efficiency_controls(tmp_path) -> None:
    first = _write_benchmark(tmp_path / "first.json", ranks=1, dofs=1000, time=10.0)
    second = _write_benchmark(tmp_path / "second.json", ranks=2, dofs=1000, time=8.0)
    with pytest.raises(ValueError, match="Efficiency warning"):
        analyze_large_scaling((first, second), tmp_path / "bad", mode="strong", efficiency_warning_threshold=0.0)
    with pytest.raises(ValueError, match="Weak-work tolerance"):
        analyze_large_scaling((first, second), tmp_path / "bad2", mode="strong", weak_work_tolerance=1.0)
