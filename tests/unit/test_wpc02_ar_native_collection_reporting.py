"""Synthetic, non-FEM contract tests for native WP-C02 collection/reporting."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from scripts import report_wpc02_ar_native as reporter
from scripts.wpc02_ar_native_collection import (
    decode_audit_vectors,
    production_support_reactions,
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
    ],
)
def test_reporter_scenario_status_classification(record: dict[str, object], expected: str) -> None:
    checks = {"example": {"passed": True}} if record["scenario_state"] == "COMPLETED_DIAGNOSTICS" else None
    assert reporter._scenario_verdict(record, checks) == expected


def test_n04_archive_remains_readable_and_hash_intact() -> None:
    archive = Path(__file__).resolve().parents[4] / ".codex-worktrees" / "wp-c02-n01-remediation" / "qualification" / "0_2_12" / "wpc02_ar_native_campaign_n03_20261023_01"
    manifest_path = archive / "archive_integrity_manifest.json"
    assert manifest_path.is_file(), "N04 archive is expected to remain beside the N05 worktree"
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
