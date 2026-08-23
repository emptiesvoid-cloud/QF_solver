from __future__ import annotations

import json
from pathlib import Path

import pytest

from solveur.api import list_benchmarks, run_benchmark
from solveur.version import __version__


@pytest.mark.benchmark
@pytest.mark.parametrize("descriptor", list_benchmarks(), ids=lambda item: item.identifier)
def test_controlled_meshed_benchmark_campaign(descriptor: object, tmp_path: Path) -> None:
    pytest.importorskip("gmsh")
    run = run_benchmark(descriptor.identifier, tmp_path)
    expected = "WARNING" if descriptor.maturity in {"experimental", "research"} else "PASS"
    assert run.status == expected
    assert all(check["status"] == "PASS" for check in run.checks)
    case_dir = tmp_path / descriptor.identifier
    summary = json.loads((case_dir / "benchmark_summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((case_dir / "benchmark_manifest.json").read_text(encoding="utf-8"))
    assert summary["status"] == expected
    assert manifest["solver"] == {"name": "QF_solver", "version": __version__}
    assert manifest["benchmark_id"] == descriptor.identifier
    if descriptor.family == "BEAM2":
        assert any(path.name.endswith(".model.json") for path in case_dir.iterdir())
    else:
        assert any(path.suffix == ".msh" for path in case_dir.iterdir())
        if descriptor.identifier == "BM-SOL-CANTILEVER-001":
            assert run.metrics["tet4_h_observed_order"] >= descriptor.criteria["tet4_h_observed_order_min"]
            assert len(run.metrics["tet4_h_convergence"]) == 6
            errors = [row["relative_error"] for row in run.metrics["tet4_h_convergence"]]
            asymptotic_levels = run.metrics["asymptotic_levels"]
            assert asymptotic_levels == [4, 5, 6]
            assert errors[-3:] == sorted(errors[-3:], reverse=True)
    if descriptor.identifier == "BM-SOL-TET4-MEMBRANE-001":
        traction = run.metrics["membrane_h_convergence"]
        compression = run.metrics["compression_h_convergence"]
        assert len(traction) == len(compression) == 5
        for positive, negative in zip(traction, compression):
            assert positive["mesh_size"] == negative["mesh_size"]
            assert positive["mean_end_ux"] == pytest.approx(-negative["mean_end_ux"], rel=1.0e-12)
    if descriptor.identifier == "BM-SOL-TET4-TORSION-001":
        rows = run.metrics["torsion_h_convergence"]
        assert len(rows) == 8
        errors = [row["relative_twist_error"] for row in rows]
        asymptotic_levels = run.metrics["asymptotic_levels"]
        assert asymptotic_levels == [6, 7, 8]
        assert errors[-3:] == sorted(errors[-3:], reverse=True)
        assert rows[-1]["relative_stress_l2_error"] < rows[0]["relative_stress_l2_error"]
