from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from solveur.large.evidence import write_large_manifest
from solveur.large.tuning import PETSC_TUNING_PRESETS, analyze_petsc_tuning


def _write_run(directory: Path, *, pipeline: float, values: np.ndarray, preset: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    displacement = directory / "displacements.bin"
    np.asarray(values, dtype=np.float64).tofile(displacement)
    (directory / "displacements_metadata.json").write_text(
        json.dumps(
            {
                "format": "qf_solver_mpi_binary_v1",
                "dtype": "float64",
                "byte_order": "little" if np.little_endian else "big",
                "shape": [values.size // 3, 3],
                "flat_size": int(values.size),
            }
        ),
        encoding="utf-8",
    )
    preconditioner = PETSC_TUNING_PRESETS[preset]["preconditioner"]
    benchmark = {
        "status": "PASS",
        "ndof": int(values.size),
        "element_count": 2,
        "solve_pipeline_time_seconds": pipeline,
        "assembly_time_seconds": 1.0,
        "solve_time_seconds": pipeline - 1.0,
        "solver": {
            "preconditioner": preconditioner,
            "setup_time_seconds": 0.5,
            "iteration_time_seconds": pipeline - 1.5,
            "iterations": 20,
            "residual_norm": 1.0e-12,
        },
        "mpi": {"size": 4},
        "memory_telemetry": {"process_peak_rss_bytes": 1000},
    }
    path = directory / "benchmark_large.json"
    path.write_text(json.dumps(benchmark), encoding="utf-8")
    write_large_manifest(directory, {"kind": "test_large_tuning", "status": "PASS"})
    return path


def test_tuning_report_selects_common_faster_preset_without_solution_drift(tmp_path: Path) -> None:
    values = np.linspace(0.1, 0.9, 12)
    paths = []
    topologies = []
    presets = []
    for topology in ("block", "beam"):
        for preset, pipeline in (("gamg-default", 10.0), ("gamg-threshold-001", 8.0)):
            paths.append(_write_run(tmp_path / topology / preset, pipeline=pipeline, values=values, preset=preset))
            topologies.append(topology)
            presets.append(preset)

    result = analyze_petsc_tuning(
        paths,
        tmp_path / "report",
        topologies=topologies,
        presets=presets,
    )

    assert result["status"] == "PASS"
    assert result["default_policy_change_recommended"] is True
    assert result["best_by_topology"]["block"]["preset"] == "gamg-threshold-001"
    assert all(run["relative_displacement_error"] == pytest.approx(0.0) for run in result["runs"])
    assert (tmp_path / "report" / "petsc_tuning_comparison.md").is_file()
    assert (tmp_path / "report" / "evidence_manifest.json").is_file()


def test_tuning_report_keeps_default_when_winners_depend_on_topology(tmp_path: Path) -> None:
    values = np.arange(9, dtype=float)
    paths = (
        _write_run(tmp_path / "block-default", pipeline=8.0, values=values, preset="gamg-default"),
        _write_run(tmp_path / "block-tuned", pipeline=9.0, values=values, preset="gamg-threshold-001"),
        _write_run(tmp_path / "beam-default", pipeline=10.0, values=values, preset="gamg-default"),
        _write_run(tmp_path / "beam-tuned", pipeline=7.0, values=values, preset="gamg-threshold-001"),
    )

    result = analyze_petsc_tuning(
        paths,
        tmp_path / "report",
        topologies=("block", "block", "beam", "beam"),
        presets=("gamg-default", "gamg-threshold-001", "gamg-default", "gamg-threshold-001"),
    )

    assert result["default_policy_change_recommended"] is False
    assert result["best_by_topology"]["block"]["preset"] == "gamg-default"
    assert result["best_by_topology"]["beam"]["preset"] == "gamg-threshold-001"


def test_tuning_report_rejects_unknown_or_misaligned_configuration(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="same length"):
        analyze_petsc_tuning((), tmp_path, topologies=(), presets=())
    missing = tmp_path / "missing.json"
    with pytest.raises(ValueError, match="Unknown"):
        analyze_petsc_tuning(
            (missing,),
            tmp_path,
            topologies=("block",),
            presets=("unknown",),
        )
