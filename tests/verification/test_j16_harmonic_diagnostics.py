"""Exact J16 nodes for the bounded guard and NAFEMS 13H mesh diagnostics."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from research.j16.guard_resolution_experiment import (
    DEFAULT_OUTPUT_ROOT as GUARD_OUTPUT_ROOT,
    run_guard_resolution_experiment,
)
from research.j16.harmonic_mesh_study import (
    CONTRACT_PATH as MESH_CONTRACT_PATH,
    FREQUENCIES_HZ,
    OUTPUT_ROOT as MESH_OUTPUT_ROOT,
    run_mesh_study,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
GUARD_CONTRACT_PATH = PROJECT_ROOT / "research/j16/contracts/nafems_13h_guard_resolution_001.json"
ALLOWED_ROUTE_STATUSES = {"QF_SOLVE_ACCEPTED", "QF_GUARD_REJECTED", "QF_NUMERICAL_REJECTED"}


def _assert_mesh_study_complete(mesh_size: int) -> None:
    contract = json.loads(MESH_CONTRACT_PATH.read_text(encoding="utf-8"))
    assert contract["state"] == "FROZEN_BEFORE_EXECUTION"
    assert mesh_size in contract["inputs"]["mesh_sizes_per_edge"]
    result = run_mesh_study(mesh_size)

    assert result["classification"] == "PROSPECTIVE_EXPLORATORY_MULTI_MESH_HARMONIC_STUDY"
    assert result["contract_id"] == contract["contract_id"]
    assert result["mesh_size"] == mesh_size
    assert len(result["rows"]) == len(FREQUENCIES_HZ)
    assert all(row["qf_route_status"] in ALLOWED_ROUTE_STATUSES for row in result["rows"])
    assert result["assembled_load_resultant"]["direct_sum_of_nodal_translational_load_dofs_n"] == pytest.approx(
        result["assembled_load_resultant"]["assembler_load_balance_resultant_n"], abs=1.0e-8
    )

    output = MESH_OUTPUT_ROOT / f"mesh_{mesh_size:02d}"
    saved = json.loads((output / "site_data.json").read_text(encoding="utf-8"))
    assert saved["contract_sha256"] == result["contract_sha256"]
    assert saved["source_git"]["branch"] == "work/0.3.0-j16-science"
    assert len(list(output.glob("mesh_*.json"))) == len(FREQUENCIES_HZ)
    assert len(list(output.glob("mesh_*.npz"))) == len(FREQUENCIES_HZ)
    assert (output / "frequency_response.csv").is_file()
    assert (output / "harmonic_amplitude_phase.png").is_file()
    assert (output / "peak_deformation.png").is_file()
    assert (output / "mesh_setup.png").is_file()
    assert (output / "artifact_manifest.json").is_file()
    for path in output.glob("mesh_*.npz"):
        with np.load(path) as archive:
            assert np.all(np.isfinite(archive["raw_reduced_real"]))
            assert np.all(np.isfinite(archive["raw_reduced_imag"]))


def test_j16_nafems13h_guard_scaling_refinement_diagnostic() -> None:
    contract = json.loads(GUARD_CONTRACT_PATH.read_text(encoding="utf-8"))
    assert contract["state"] == "FROZEN_BEFORE_EXECUTION"
    result = run_guard_resolution_experiment()

    assert result["classification"] == "BOUNDED_SOLVER_DIAGNOSTIC_ON_QF_ASSEMBLED_8X8_SYSTEM"
    assert result["j15_input_artifacts_verified"] == 10
    assert len(result["frequencies"]) == 5
    assert all(row["historical_qf_status"] == "QF_GUARD_REJECTED" for row in result["frequencies"])
    assert all(set(row["variants"]) == {
        "spsolve_unscaled", "spsolve_row_column_equilibrated", "splu_two_refinements"
    } for row in result["frequencies"])
    assert all((GUARD_OUTPUT_ROOT / row["matrix_archive"]).is_file() for row in result["frequencies"])
    assert (GUARD_OUTPUT_ROOT / "guard_resolution_summary.json").is_file()
    assert (GUARD_OUTPUT_ROOT / "artifact_manifest.json").is_file()


def test_j16_nafems13h_mesh_06() -> None:
    _assert_mesh_study_complete(6)


def test_j16_nafems13h_mesh_08() -> None:
    _assert_mesh_study_complete(8)


def test_j16_nafems13h_mesh_10() -> None:
    _assert_mesh_study_complete(10)
