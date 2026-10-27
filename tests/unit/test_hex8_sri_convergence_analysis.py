from __future__ import annotations

import json

import pytest

from experiments.hex8_sri_equilibrium.convergence_analysis import (
    analyze_sidecars,
    read_sidecar,
    sha256_file,
    write_analysis_csv,
    write_convergence_svg,
)
from experiments.hex8_sri_equilibrium.convergence import MESH_LEVELS


def _sidecar(mesh: tuple[int, int, int], uz: float, energy: float) -> dict:
    element_count = mesh[0] * mesh[1] * mesh[2]
    node_count = (mesh[0] + 1) * (mesh[1] + 1) * (mesh[2] + 1)
    fixed = (mesh[1] + 1) * (mesh[2] + 1) * 3
    return {
        "schema": "qfsolver-hex8-sri-convergence-sidecar-v1",
        "case": {
            "formulation": "sri_corrected",
            "poisson_ratio": 0.3,
            "divisions_xyz": list(mesh),
            "element_count": element_count,
            "node_count": node_count,
            "dof_count": 3 * node_count,
            "fixed_dof_count": fixed,
            "free_dof_count": 3 * node_count - fixed,
        },
        "units": {
            "displacement": "m",
            "strain": "dimensionless",
            "energy": "J",
            "force": "N",
            "moment": "N·m",
            "time": "s",
        },
        "observables": {
            "signed_mean_loaded_face_UZ_m": uz,
            "internal_energy_J": energy,
            "external_load_work_J": 2.0 * energy,
            "free_residual_l2_N": 1.0e-12,
            "free_residual_relative": 1.0e-12,
            "force_closure_relative": 1.0e-12,
            "moment_closure_relative": 1.0e-12,
            "condition_number_1_estimate_Kff": 1.0e6,
            "support_reaction_resultant_N": [0.0, 0.0, 1.0],
            "force_closure_N": [0.0, 0.0, 0.0],
            "moment_closure_Nm": [0.0, 0.0, 0.0],
        },
        "criteria_verdicts": {"free_residual": "PASS"},
    }


def test_self_convergence_is_a_diagnostic_and_not_an_oracle_error() -> None:
    records = [
        _sidecar(mesh, uz, energy)
        for mesh, uz, energy in zip(
            MESH_LEVELS,
            (-0.010, -0.012, -0.013, -0.01325),
            (10.0, 12.0, 13.0, 13.25),
            strict=True,
        )
    ]

    rows = analyze_sidecars(records)

    assert len(rows) == 4
    assert rows[0]["relative_change_UZ_from_previous_level"] is None
    assert rows[-1]["UZ_self_convergence_indicator_order"] == pytest.approx(2.0)
    assert rows[-1]["energy_self_convergence_indicator_order"] == pytest.approx(2.0)
    assert rows[-1]["independent_reference_status"] == "NOT_ASSESSED_NO_QUALIFIED_ORACLE"
    assert rows[-1]["UZ_relative_error_to_qualified_reference"] is None


def test_reference_errors_require_explicit_qualified_reference_and_uncertainty() -> None:
    record = _sidecar(MESH_LEVELS[0], -0.01, 10.0)
    reference = {
        "qualified": True,
        "relative_uncertainty_uz": 0.004,
        "relative_uncertainty_energy": 0.005,
        "signed_mean_loaded_face_UZ_m": -0.0101,
        "internal_energy_J": 10.1,
    }

    row = analyze_sidecars([record], qualified_references={0.3: reference})[0]

    assert row["independent_reference_status"] == "QUALIFIED_REFERENCE"
    assert row["UZ_relative_error_to_qualified_reference"] == pytest.approx(0.01 / 1.01)
    assert row["energy_relative_error_to_qualified_reference"] == pytest.approx(0.1 / 10.1)

    rejected = {**reference, "relative_uncertainty_uz": 0.0051}
    row_without_gate = analyze_sidecars([record], qualified_references={0.3: rejected})[0]
    assert row_without_gate["independent_reference_status"] == "NOT_ASSESSED_NO_QUALIFIED_ORACLE"
    assert row_without_gate["UZ_relative_error_to_qualified_reference"] is None
    invalid_uncertainty = {**reference, "relative_uncertainty_energy": -0.1}
    row_with_invalid_reference = analyze_sidecars([record], qualified_references={0.3: invalid_uncertainty})[0]
    assert row_with_invalid_reference["independent_reference_status"] == "NOT_ASSESSED_NO_QUALIFIED_ORACLE"


def test_analysis_rejects_duplicate_cases_and_unit_mismatch() -> None:
    record = _sidecar(MESH_LEVELS[0], -0.01, 10.0)
    with pytest.raises(ValueError, match="duplicate"):
        analyze_sidecars([record, record])

    wrong_units = _sidecar(MESH_LEVELS[0], -0.01, 10.0)
    wrong_units["units"]["energy"] = "N·m"
    with pytest.raises(ValueError, match="unit mismatch"):
        analyze_sidecars([wrong_units])

    invalid_mesh = _sidecar(MESH_LEVELS[0], -0.01, 10.0)
    invalid_mesh["case"]["divisions_xyz"] = [4.0, 2, 2]
    with pytest.raises(ValueError, match="positive integers"):
        analyze_sidecars([invalid_mesh])


def test_sidecar_reader_verifies_optional_sha256_without_rewriting(tmp_path) -> None:
    path = tmp_path / "sidecar.json"
    path.write_text(json.dumps(_sidecar(MESH_LEVELS[0], -0.01, 10.0)), encoding="utf-8")
    digest = sha256_file(path)

    loaded = read_sidecar(path, expected_sha256=digest)

    assert loaded["schema"] == "qfsolver-hex8-sri-convergence-sidecar-v1"
    assert sha256_file(path) == digest
    with pytest.raises(ValueError, match="INTEGRITY_MISMATCH"):
        read_sidecar(path, expected_sha256="0" * 64)


def test_synthetic_analysis_writers_create_new_csv_and_svg_only(tmp_path) -> None:
    records = [
        _sidecar(mesh, uz, energy)
        for mesh, uz, energy in zip(
            MESH_LEVELS,
            (-0.010, -0.012, -0.013, -0.01325),
            (10.0, 12.0, 13.0, 13.25),
            strict=True,
        )
    ]
    rows = analyze_sidecars(records)
    csv_path = tmp_path / "synthetic.csv"
    svg_path = tmp_path / "synthetic.svg"

    csv_sha = write_analysis_csv(csv_path, rows)
    svg_sha = write_convergence_svg(
        svg_path,
        rows,
        value_field="signed_mean_loaded_face_UZ_m",
        title="Synthetic unit-test data — not a physical result",
        unit="m",
    )

    assert sha256_file(csv_path) == csv_sha
    assert sha256_file(svg_path) == svg_sha
    assert "not a physical result" in svg_path.read_text(encoding="utf-8")
    with pytest.raises(FileExistsError):
        write_analysis_csv(csv_path, rows)
