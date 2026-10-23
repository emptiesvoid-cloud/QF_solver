"""Synthetic, non-FEM contract tests for native WP-C02 collection/reporting."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pytest

from scripts import report_wpc02_ar_native as reporter
from scripts.wpc02_ar_native_collection import (
    contact_force_vectors,
    decode_contact_rows,
    decode_audit_vectors,
    elastic_strain_energy_from_total_internal,
    production_free_stationarity_inf,
    production_support_reactions,
    recover_elastic_internal_force,
    resultant_and_moment,
)
from solveur.core.audit import _vector_summary
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.solvers.static import LinearStaticSolver


def _record(name: str, values: list[float]) -> dict[str, object]:
    nonzero = [
        {"index": index, "value": value}
        for index, value in enumerate(values)
        if abs(value) > 1.0e-30
    ]
    array = np.asarray(values, dtype=float)
    return {
        "name": name,
        "size": len(values),
        "norm": float(np.linalg.norm(array)),
        "max_abs": float(np.max(np.abs(array), initial=0.0)),
        "nonzero_count": len(nonzero),
        "nonzero_entries": nonzero,
    }


def _valid_vectors() -> list[dict[str, object]]:
    return [
        _record("loads", [0, 0, -5, 0, 0, 0]),
        _record("displacements", [0, 0, 0.01, 0, 0, 0]),
        _record("internal_force", [0, 0, 0, 0, 0, 0]),
        _record("residual", [0, 0, 0, 0, 0, 5]),
        _record("reactions", [0, 0, 0, 0, 0, 5]),
    ]


def _complete_record() -> dict[str, object]:
    diagnostics: dict[str, object] = {
        "relative_l2_displacement_error": 0.01,
        "pressure_relative_l2_error": 0.1,
        "active_count": 2,
        "open_count": 2,
        "mesh": {"nodes": 4, "tet4": 6, "body_mechanical_dofs": 12, "body_free_dofs": 6, "contact_rows": 4},
        "maximum_penetration_m": 0.0,
        "production_gap_reconstruction_error_m": 0.0,
        "production_complementarity_inf_nm": 0.0,
        "strict_active_max_gap_m": 0.0,
        "strict_open_max_multiplier_n": 0.0,
        "production_stationarity_inf_n": 0.0,
        "independent_qp_primal_gap_min_m": 0.0,
        "independent_qp_dual_multiplier_min_n": 0.0,
        "independent_qp_complementarity_inf_nm": 0.0,
        "independent_qp_stationarity_inf_n": 0.0,
        "independent_qp_displacement_max_error_m": 0.0,
        "independent_qp_multiplier_max_error_n": 0.0,
        "production_force_balance_relative": 0.0,
        "production_moment_balance_relative": 0.0,
        "independent_qp_force_balance_relative": 0.0,
        "independent_qp_moment_balance_relative": 0.0,
        "production_contact_work_identity_error_j": 0.0,
        "independent_qp_contact_work_identity_error_j": 0.0,
        "fe_energy_matrix_vs_quadrature_error_j": 0.0,
        "contact_resultant_relative_error": 0.0,
        "contact_moment_relative_error": 0.0,
        "front_error_max_abs_m": 0.0,
        "front_error_max_over_hx": 0.0,
        "front_bracketed_row_count": 1,
        "front_bracket_ordered_row_count": 1,
        "front_row_count": 1,
        "front_trace_by_y": [{
            "front_bracketed_by_observed_states": True,
            "ordered_active_open_bracket": True,
            "contact_states_by_x": [
                {"node": 0, "classification": "ACTIVE"},
                {"node": 1, "classification": "ACTIVE"},
                {"node": 2, "classification": "OPEN"},
                {"node": 3, "classification": "OPEN"},
            ],
        }],
        "false_positives": [],
        "false_negatives": [],
        "false_positive_count": 0,
        "false_negative_count": 0,
        "rows_with_more_than_one_active_open_transition": [],
        "strain_energy_j": 1.0,
        "fe_integrated_strain_energy_j": 1.0,
        "exact_strain_energy_j": 1.0,
        "absolute_strain_energy_difference_j": 0.0,
        "strain_energy_error_norm_j_sqrt": 0.1,
        "support_resultant_error_n": 0.0,
        "support_moment_error_nm": 0.0,
        "contact_resultant_n": 1.0,
        "contact_moment_error_nm": 0.0,
    }
    return {
        "scenario_state": "COMPLETED_DIAGNOSTICS",
        "diagnostics": diagnostics,
        "field_values": {
            "body_displacements_m_node_major_xyz": [[0.0, 0.0, 0.0] for _ in range(4)],
            "contact_node_ids": [0, 1, 2, 3],
            "contact_gaps_m": [0.0] * 4,
            "contact_multipliers_n": [1.0] * 4,
            "production_contact_active_set_flags": [True, True, False, False],
            "contact_pressures_pa": [0.0] * 4,
            "contact_area_weights_m2": [1.0] * 4,
            "support_reactions_n_node_major_xyz": [[0.0, 0.0, 0.0] for _ in range(4)],
            "external_nodal_loads_n_node_major_xyz": [[0.0, 0.0, 0.0] for _ in range(4)],
        },
    }


def test_audit_vector_decode_uses_named_sparse_records_and_physical_sign() -> None:
    decoded = decode_audit_vectors(_valid_vectors(), expected_size=6)
    np.testing.assert_array_equal(decoded["reactions"], [0, 0, 0, 0, 0, 5])
    support = production_support_reactions(decoded, top_nodes=np.asarray([1]))
    # Independent two-node analytic wrench: the extracted support at (1,0,0) gives My=-5 N m.
    coordinates = np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    resultant, moment = resultant_and_moment(coordinates, support)
    np.testing.assert_array_equal(resultant, [0, 0, 5])
    np.testing.assert_array_equal(moment, [0, -5, 0])


def test_fixture_shape_matches_production_solveraudit_vector_serializer() -> None:
    produced = _vector_summary("reactions", np.asarray([0.0, -2.0, 0.0]), include_values=True)
    assert set(produced) == {"name", "size", "norm", "max_abs", "nonzero_count", "nonzero_entries"}
    assert produced["nonzero_entries"] == [{"index": 1, "value": -2.0}]


def test_audit_vector_order_does_not_change_decoding() -> None:
    expected = decode_audit_vectors(_valid_vectors(), expected_size=6)
    actual = decode_audit_vectors(list(reversed(_valid_vectors())), expected_size=6)
    for name in expected:
        np.testing.assert_array_equal(actual[name], expected[name])


@pytest.mark.parametrize("mutation", ["missing_vector", "missing_field", "nan", "infinity", "duplicate_index"])
def test_audit_vector_malformed_or_incomplete_is_rejected(mutation: str) -> None:
    rows = _valid_vectors()
    if mutation == "missing_vector":
        rows = rows[:-1]
    elif mutation == "missing_field":
        del rows[0]["nonzero_entries"]
    elif mutation in {"nan", "infinity"}:
        rows[-1]["nonzero_entries"][0]["value"] = float("nan" if mutation == "nan" else "inf")
    else:
        rows[-1]["nonzero_entries"].append(dict(rows[-1]["nonzero_entries"][0]))
    with pytest.raises(ValueError):
        decode_audit_vectors(rows, expected_size=6)


def test_opposite_sign_is_preserved_and_unbalanced_fixture_is_not_hidden() -> None:
    rows = _valid_vectors()
    rows[-1] = _record("reactions", [0, 0, -5, 0, 0, 0])
    decoded = decode_audit_vectors(rows, expected_size=6)
    assert decoded["reactions"][2] == -5.0
    assert float(decoded["loads"][2] + decoded["reactions"][2]) == -10.0


def _contact_row(gap: float, pressure_force_n: float, *, active: bool = False) -> dict[str, object]:
    return {"gap": gap, "pressure": pressure_force_n, "normal": [0.0, 0.0, 1.0], "active": active}


def test_production_contact_pressure_is_positive_compression_and_open_is_zero() -> None:
    decoded = decode_contact_rows(
        [_contact_row(0.0, 5.0, active=True), _contact_row(1.0e-4, 0.0)],
        contact_nodes=np.asarray([0, 1]),
        area_weights_m2=np.asarray([0.5, 0.25]),
        expected_normals=np.asarray([0.0, 0.0, 1.0]),
    )
    np.testing.assert_array_equal(decoded["multipliers_n"], [5.0, 0.0])
    np.testing.assert_array_equal(decoded["pressure_pa"], [10.0, 0.0])
    np.testing.assert_array_equal(decoded["gaps_m"], [0.0, 1.0e-4])
    np.testing.assert_array_equal(decoded["active_flags"], [True, False])


def test_contact_decode_keeps_partial_active_and_open_classification() -> None:
    decoded = decode_contact_rows(
        [_contact_row(0.0, 2.0, active=True), _contact_row(0.0, 0.0), _contact_row(2.0e-4, 0.0)],
        contact_nodes=np.asarray([0, 1, 2]),
        area_weights_m2=np.ones(3),
        expected_normals=np.asarray([0.0, 0.0, 1.0]),
    )
    active = decoded["multipliers_n"] > 1.0e-7
    opened = decoded["gaps_m"] > 1.0e-10
    assert int(np.count_nonzero(active)) == 1
    assert int(np.count_nonzero(opened)) == 1
    assert not np.all(active) and not np.all(opened)


def test_contact_action_reaction_and_physical_force_moment_balance() -> None:
    slave_contact = contact_force_vectors(
        node_ids=np.asarray([0]),
        normals=np.asarray([[0.0, 0.0, 1.0]]),
        force_magnitudes_n=np.asarray([5.0]),
        node_count=2,
    )
    master_contact = contact_force_vectors(
        node_ids=np.asarray([1]),
        normals=np.asarray([[0.0, 0.0, -1.0]]),
        force_magnitudes_n=np.asarray([5.0]),
        node_count=2,
    )
    np.testing.assert_array_equal(slave_contact[0], -master_contact[1])
    coordinates = np.asarray([[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    slave_resultant, slave_moment = resultant_and_moment(coordinates, slave_contact)
    np.testing.assert_array_equal(slave_resultant, [0.0, 0.0, 5.0])
    np.testing.assert_array_equal(slave_moment, [0.0, -5.0, 0.0])
    resultant, moment = resultant_and_moment(coordinates, slave_contact + master_contact)
    np.testing.assert_array_equal(resultant, np.zeros(3))
    np.testing.assert_array_equal(moment, np.zeros(3))


def test_production_total_force_stationarity_and_energy_have_independent_oracle() -> None:
    # A deliberately specified SPD elastic system, not assembled by the collector.
    stiffness = np.asarray([[4.0, 1.0, 0.0], [1.0, 3.0, 0.0], [0.0, 0.0, 2.0]])
    displacement = np.asarray([0.2, -0.1, 0.3])
    elastic_force = np.asarray([0.7, -0.1, 0.6])  # independently evaluated K @ u
    np.testing.assert_allclose(stiffness @ displacement, elastic_force, rtol=0.0, atol=2.0e-16)

    # Active compression at DOF 0; DOF 1 is open; DOF 2 is constrained.
    contact = np.asarray([0.5, 0.0, 0.0])
    production_total = elastic_force - contact  # production K u - P convention
    loads = np.asarray([0.2, -0.1, -7.0])
    free = np.asarray([0, 1], dtype=int)
    expected_residual = np.asarray([0.0, 0.0])  # total production force balances loads

    assert production_free_stationarity_inf(production_total, loads, free) == pytest.approx(
        np.linalg.norm(expected_residual, ord=np.inf), abs=1.0e-15
    )
    # A large constrained-DOF reaction is correctly masked from free stationarity.
    assert production_free_stationarity_inf(production_total, loads, np.asarray([0, 1])) < 1.0e-15

    # The historical double subtraction and a reversed contact sign fail the same oracle.
    with pytest.raises(AssertionError):
        assert np.linalg.norm((production_total - loads - contact)[free], ord=np.inf) <= 1.0e-12
    with pytest.raises(AssertionError):
        assert np.linalg.norm((production_total + contact - loads)[free], ord=np.inf) <= 1.0e-12

    recovered = recover_elastic_internal_force(production_total, contact)
    np.testing.assert_array_equal(recovered, elastic_force)
    expected_energy = 0.5 * float(displacement @ stiffness @ displacement)
    assert expected_energy == pytest.approx(0.165, abs=1.0e-15)
    assert elastic_strain_energy_from_total_internal(displacement, production_total, contact) == pytest.approx(
        expected_energy, abs=1.0e-15
    )
    # Omitting +P contaminates elastic energy by -1/2 u.P and fails independently.
    with pytest.raises(AssertionError):
        assert 0.5 * float(displacement @ production_total) == pytest.approx(expected_energy, abs=1.0e-12)


def test_force_energy_helpers_cover_no_contact_and_reject_invalid_inputs() -> None:
    stiffness = np.diag([2.0, 3.0])
    displacement = np.asarray([0.25, -0.5])
    elastic = stiffness @ displacement
    zero_contact = np.zeros(2)
    assert elastic_strain_energy_from_total_internal(displacement, elastic, zero_contact) == pytest.approx(
        0.4375
    )
    with pytest.raises(ValueError, match="same shape"):
        recover_elastic_internal_force(np.ones(2), np.ones(3))
    with pytest.raises(ValueError, match="free DOFs"):
        production_free_stationarity_inf(np.ones(2), np.ones(2), np.asarray([True, False]))
    for bad in (np.asarray([np.nan, 1.0]), np.asarray([np.inf, 1.0])):
        with pytest.raises(ValueError, match="finite"):
            elastic_strain_energy_from_total_internal(np.ones(2), bad, np.zeros(2))
    with pytest.raises(ValueError, match="finite"):
        production_free_stationarity_inf(np.ones(2), np.asarray([0.0, np.nan]), np.asarray([0]))


def test_recovered_elastic_energy_matches_independent_bar_quadrature() -> None:
    # Analytic one-dimensional bar: constant strain is integrated at independent
    # Gauss points, without using the collector's stiffness-energy expression.
    youngs_modulus_pa = 20.0
    area_m2 = 0.5
    length_m = 2.0
    displacement = np.asarray([0.0, -0.2])
    strain = (displacement[1] - displacement[0]) / length_m
    gauss_xi = np.asarray([-1.0 / np.sqrt(3.0), 1.0 / np.sqrt(3.0)])
    gauss_weights = np.asarray([1.0, 1.0])
    jacobian = length_m / 2.0
    quadrature_energy = sum(
        0.5 * youngs_modulus_pa * strain**2 * area_m2 * weight * jacobian
        for _xi, weight in zip(gauss_xi, gauss_weights)
    )

    stiffness = youngs_modulus_pa * area_m2 / length_m * np.asarray([[1.0, -1.0], [-1.0, 1.0]])
    elastic_force = stiffness @ displacement
    physical_compression = np.asarray([0.0, 0.7])
    production_total = elastic_force - physical_compression
    recovered = elastic_strain_energy_from_total_internal(
        displacement, production_total, physical_compression
    )
    assert recovered == pytest.approx(quadrature_energy, rel=1.0e-14, abs=1.0e-15)
    with pytest.raises(AssertionError):
        assert 0.5 * float(displacement @ production_total) == pytest.approx(
            quadrature_energy, rel=1.0e-14, abs=1.0e-15
        )


def test_kkt_admissibility_and_complementarity_with_compression_sign() -> None:
    gaps = np.asarray([0.0, 2.0e-4])
    compression = np.asarray([3.0, 0.0])
    assert float(np.min(gaps)) >= -1.0e-10
    assert float(np.min(compression)) >= -1.0e-7
    assert float(np.max(np.abs(gaps * compression))) == 0.0
    inverted = -compression
    assert float(np.min(inverted)) < -1.0e-7


def test_front_trace_brackets_known_partial_contact_without_fem() -> None:
    import importlib.util
    from pathlib import Path

    aj_path = Path(__file__).with_name("test_wpc02_aj_partial_active_contact.py")
    spec = importlib.util.spec_from_file_location("wpc02_aj_front_fixture", aj_path)
    assert spec is not None and spec.loader is not None
    aj = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(aj)
    except ModuleNotFoundError as exc:
        if exc.name == "solveur.contact.experimental_distributed_frozen":
            pytest.skip("historical AJ front helper requires an unintegrated experimental contact module")
        raise
    nodes = np.asarray([0, 1, 2, 3, 4, 5])
    xyz = np.asarray([
        [0.0, 0.0, 0.0], [0.5, 0.0, 0.0], [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0], [0.5, 1.0, 0.0], [1.0, 1.0, 0.0],
    ])
    gaps = np.asarray([0.0, 0.0, 1.0e-4, 0.0, 0.0, 1.0e-4])
    pressure_force = np.asarray([2.0, 0.0, 0.0, 2.0, 0.0, 0.0])
    trace = aj._front_diagnostics(nodes, xyz, np.ones(6), 0.5, 0.5, gaps, pressure_force)
    assert trace["front_bracketed_row_count"] == trace["front_row_count"] == 2
    assert trace["front_error_max_over_hx"] == 1.0


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), -float("inf")])
def test_contact_decoder_rejects_nonfinite_row_data(bad_value: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        decode_contact_rows(
            [_contact_row(0.0, bad_value)],
            contact_nodes=np.asarray([0]),
            area_weights_m2=np.asarray([1.0]),
        )


def test_contact_decoder_rejects_wrong_normal_or_bad_area() -> None:
    with pytest.raises(ValueError, match="normals differ"):
        decode_contact_rows(
            [{"gap": 0.0, "pressure": 1.0, "normal": [0.0, 0.0, -1.0], "active": True}],
            contact_nodes=np.asarray([0]), area_weights_m2=np.asarray([1.0]),
            expected_normals=np.asarray([0.0, 0.0, 1.0]),
        )
    with pytest.raises(ValueError, match="areas"):
        decode_contact_rows(
            [_contact_row(0.0, 1.0)], contact_nodes=np.asarray([0]), area_weights_m2=np.asarray([0.0])
        )


@pytest.mark.parametrize(
    ("force", "active", "message"),
    [
        (-1.0e-4, True, "tensile contact force"),
        (2.0, False, "inactive flag conflicts"),
    ],
)
def test_contact_decoder_rejects_sign_or_active_flag_inconsistency(
    force: float, active: bool, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        decode_contact_rows(
            [_contact_row(0.0, force, active=active)],
            contact_nodes=np.asarray([0]),
            area_weights_m2=np.asarray([1.0]),
            expected_normals=np.asarray([0.0, 0.0, 1.0]),
            active_force_tolerance_n=1.0e-7,
        )
def test_reporter_handles_malformed_partial_missing_and_mixed_scenarios(tmp_path: Path) -> None:
    (tmp_path / "m4_diagnostics.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "m5_diagnostics.json").write_text(json.dumps({
        "scenario_state": "SOLVER_OR_DIAGNOSTIC_EXCEPTION",
        "failure": {"type": "TypeError", "message": "partial collection failure"},
    }), encoding="utf-8")
    report = reporter.render_report(tmp_path)
    assert "ERROR_COLLECTION" in report
    assert "NOT_ACQUIRED" in report
    assert "TypeError" in report


def test_reporter_marks_missing_scenario_not_evaluated(tmp_path: Path) -> None:
    report = reporter.render_report(tmp_path)
    assert "NOT_EVALUATED" in report
    assert "NOT_ACQUIRED" in report


def test_reporter_downgrades_incomplete_completed_record_to_collection_error(tmp_path: Path) -> None:
    (tmp_path / "m4_diagnostics.json").write_text(json.dumps({
        "scenario_state": "COMPLETED_DIAGNOSTICS", "diagnostics": {}, "field_values": {}
    }), encoding="utf-8")
    report = reporter.render_report(tmp_path)
    assert "ERROR_COLLECTION" in report
    assert "completed diagnostics are missing required fields" in report


@pytest.mark.parametrize("missing", ["relative_l2_displacement_error", "pressure_relative_l2_error"])
def test_reporter_rejects_completed_record_missing_endpoint_field(tmp_path: Path, missing: str) -> None:
    record = _complete_record()
    del record["diagnostics"][missing]
    (tmp_path / "m5_diagnostics.json").write_text(json.dumps(record), encoding="utf-8")
    report = reporter.render_report(tmp_path)
    assert "ERROR_COLLECTION" in report
    assert missing in report


def test_reporter_rejects_non_array_fields_and_non_object_failure(tmp_path: Path) -> None:
    complete = _complete_record()
    complete["field_values"]["support_reactions_n_node_major_xyz"] = None
    (tmp_path / "m4_diagnostics.json").write_text(json.dumps(complete), encoding="utf-8")
    (tmp_path / "m5_diagnostics.json").write_text(json.dumps({
        "scenario_state": "SOLVER_OR_DIAGNOSTIC_EXCEPTION", "failure": ["malformed"]
    }), encoding="utf-8")
    report = reporter.render_report(tmp_path)
    assert "ERROR_COLLECTION" in report
    assert "JSON lists" in report
    assert "InvalidFailureRecord" in report


@pytest.mark.parametrize("corruption", ["short_nodal_field", "short_contact_field", "front_count_mismatch"])
def test_reporter_rejects_truncated_fields_and_inconsistent_front_counts(
    tmp_path: Path, corruption: str
) -> None:
    record = _complete_record()
    if corruption == "short_nodal_field":
        record["field_values"]["support_reactions_n_node_major_xyz"].pop()
    elif corruption == "short_contact_field":
        record["field_values"]["contact_multipliers_n"].pop()
    else:
        record["diagnostics"]["false_positive_count"] = 1
    (tmp_path / "m4_diagnostics.json").write_text(json.dumps(record), encoding="utf-8")
    report = reporter.render_report(tmp_path)
    assert "ERROR_COLLECTION" in report


def test_collection_and_reporting_helpers_never_enter_fem(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("FEM solve or assembly was reached from a non-FEM test")

    monkeypatch.setattr(LinearStaticSolver, "solve", forbidden)
    monkeypatch.setattr(GlobalAssembler, "assemble_stiffness", forbidden)
    vectors = decode_audit_vectors(_valid_vectors(), expected_size=6)
    support = production_support_reactions(vectors, top_nodes=np.asarray([0]))
    resultant_and_moment(np.zeros((2, 3)), support)
    reporter.render_report(tmp_path)


@pytest.mark.parametrize(
    ("record", "expected"),
    [
        ({"scenario_state": "COMPLETED_DIAGNOSTICS"}, "PASS"),
        ({"scenario_state": "SOLVER_OR_DIAGNOSTIC_EXCEPTION", "failure": {"type": "NumericalConvergenceError"}}, "FAIL"),
        ({"scenario_state": "SOLVER_OR_DIAGNOSTIC_EXCEPTION", "failure": {"type": "TypeError"}}, "ERROR_COLLECTION"),
        ({"scenario_state": "SOLVER_COMPLETED_RAW_FIELDS"}, "NOT_EVALUATED"),
        ({"scenario_state": "COLLECTION_ERROR"}, "ERROR_COLLECTION"),
        ({"scenario_state": "COLLECTION_ERROR", "_ledger_state": "SCIENTIFIC_CRITERION_FAILURE"}, "FAIL"),
        ({"scenario_state": "DIAGNOSTICS_MISSING", "_ledger_state": "SCIENTIFIC_CRITERION_FAILURE"}, "FAIL"),
        ({"scenario_state": "DIAGNOSTICS_MISSING", "_ledger_state": "WALL_TIMEOUT_EXCEEDED"}, "NOT_EVALUATED"),
    ],
)
def test_reporter_scenario_status_classification(record: dict[str, object], expected: str) -> None:
    checks = {"example": {"passed": True}} if record["scenario_state"] == "COMPLETED_DIAGNOSTICS" else None
    assert reporter._scenario_verdict(record, checks) == expected


def test_reporter_marks_empty_contact_and_front_metrics_not_evaluated_but_keeps_fail() -> None:
    record = _complete_record()
    d = record["diagnostics"]
    d["active_count"] = 0
    d["strict_active_max_gap_m"] = None
    d["front_error_max_abs_m"] = None
    d["front_error_max_over_hx"] = None
    d["front_bracketed_row_count"] = 0
    d["front_bracket_ordered_row_count"] = 0
    d["front_trace_by_y"] = [{
        "front_bracketed_by_observed_states": False,
        "ordered_active_open_bracket": False,
        "contact_states_by_x": [
            {"node": 0, "classification": "UNCLASSIFIED"},
            {"node": 1, "classification": "OPEN"},
            {"node": 2, "classification": "OPEN"},
            {"node": 3, "classification": "OPEN"},
        ],
    }]
    reporter._validate_complete_record(record)
    checks = reporter._level_checks("M4", record, reporter._load(reporter.PLAN_PATH))
    assert checks["partial_contact_active_count"]["status"] == "FAIL"
    assert checks["strict_active_gap_m"]["status"] == "NOT_EVALUATED"
    assert reporter._status(checks) == "FAIL"


def test_reporter_does_not_claim_pass_when_run_ledger_is_unreadable() -> None:
    record = {"scenario_state": "COMPLETED_DIAGNOSTICS", "_ledger_error": "invalid ledger"}
    assert reporter._scenario_verdict(record, {"one": {"passed": True}}) == "ERROR_COLLECTION"
    assert reporter._scenario_verdict(record, {"one": {"passed": False}}) == "FAIL"


def test_campaign_identity_requires_authoritative_run_ledger(tmp_path: Path) -> None:
    (tmp_path / "archive_integrity_manifest.json").write_text("{}", encoding="utf-8")
    entries, error = reporter._load_run_ledger(tmp_path)
    assert entries == {}
    assert error is not None and "MissingLedger" in error
    record = {"scenario_state": "COMPLETED_DIAGNOSTICS", "_ledger_error": error}
    assert reporter._scenario_verdict(record, {"one": {"passed": True}}) == "ERROR_COLLECTION"


@pytest.mark.parametrize("serialization", ["invalid_json", "nan_metric", "missing_record"])
def test_reporter_ledger_scientific_failure_survives_diagnostic_collection_errors(
    tmp_path: Path, serialization: str
) -> None:
    if serialization == "invalid_json":
        (tmp_path / "m4_diagnostics.json").write_text("{broken", encoding="utf-8")
    elif serialization == "nan_metric":
        record = _complete_record()
        record["diagnostics"]["production_stationarity_inf_n"] = float("nan")
        (tmp_path / "m4_diagnostics.json").write_text(json.dumps(record), encoding="utf-8")
    (tmp_path / "run_ledger.json").write_text(json.dumps({"scenarios": [
        {"level": "M4", "state": "SCIENTIFIC_CRITERION_FAILURE", "attempt_count": 1},
        {"level": "M5", "state": "WALL_TIMEOUT_EXCEEDED", "attempt_count": 1},
    ]}), encoding="utf-8")
    report = reporter.render_report(tmp_path)
    assert "**M4** : `FAIL`" in report
    assert "**M5** : `NOT_EVALUATED`" in report
    assert "diagnostics dérivés absents ou invalides sont `NOT_EVALUATED`" in report


def test_reporter_preserves_collection_error_when_no_scientific_failure_was_recorded(tmp_path: Path) -> None:
    (tmp_path / "m4_diagnostics.json").write_text("{broken", encoding="utf-8")
    (tmp_path / "run_ledger.json").write_text(json.dumps({"scenarios": [
        {"level": "M4", "state": "INFRASTRUCTURE_FAILURE_NO_DIAGNOSTIC", "attempt_count": 1},
    ]}), encoding="utf-8")
    record = reporter._load_scenario(
        tmp_path / "m4_diagnostics.json", "M4", reporter._load(reporter.PLAN_PATH),
        reporter._load_run_ledger(tmp_path)[0]["M4"],
    )
    assert record is not None
    assert reporter._scenario_verdict(record) == "NOT_EVALUATED"
    assert record["scenario_state"] == "COLLECTION_ERROR"


def test_n04_archive_remains_readable_and_hash_intact() -> None:
    default_archive = Path(__file__).resolve().parents[4] / ".codex-worktrees" / "wp-c02-n01-remediation" / "qualification" / "0_2_12" / "wpc02_ar_native_campaign_n03_20261023_01"
    archive = Path(os.environ.get("WPC02_AR_N04_ARCHIVE_PATH", default_archive))
    manifest_path = archive / "archive_integrity_manifest.json"
    if not manifest_path.is_file():
        if "WPC02_AR_N04_ARCHIVE_PATH" in os.environ:
            pytest.fail(f"Configured N04 archive is missing: {archive}")
        pytest.skip("external N04 archive is not present in this checkout")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["file_count"] == len(manifest["files"]) == 536
    for entry in manifest["files"]:
        path = archive / entry["path"]
        payload = path.read_bytes()
        assert len(payload) == entry["size_bytes"]
        assert hashlib.sha256(payload).hexdigest() == entry["sha256"]
    assert json.loads((archive / "m4_diagnostics.json").read_text(encoding="utf-8"))["scenario_state"] == "SOLVER_OR_DIAGNOSTIC_EXCEPTION"
    assert json.loads((archive / "m5_diagnostics.json").read_text(encoding="utf-8"))["scenario_state"] == "SOLVER_OR_DIAGNOSTIC_EXCEPTION"
    rendered = reporter.render_report(archive)
    assert "Résultat scientifique global : NOT_ACQUIRED" in rendered
    assert "ERROR_COLLECTION" in rendered
