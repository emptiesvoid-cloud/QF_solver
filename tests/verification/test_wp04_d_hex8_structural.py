"""Executable guards for the frozen WP04-D HEX8 structural campaign."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, cast

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "qualification" / "0_2_9" / "wp04d"


def _load(name: str) -> dict[str, Any]:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def _case(name: str) -> dict[str, Any]:
    campaign = _load("hex8_campaign_result.json")
    cases = cast(dict[str, dict[str, Any]], campaign["cases"])
    return cases[name]


def test_hex8_contract_is_frozen_before_structural_results() -> None:
    contract = _load("hex8_contract.json")

    assert contract["status"] == "FROZEN_BEFORE_RESULT_EXECUTION"
    assert contract["result_execution_started"] is False
    assert contract["frozen_from_sha"] == "0c23b11477140fa64b5dd2a74def3a042bfe3d8e"
    assert contract["branch"] == "0.2.9-unified-nonlinear"
    assert contract["target"]["family"] == "HEX8"
    assert contract["target"]["integration"] == "full 2x2x2 Gauss"
    assert contract["thresholds"]["mesh_h2_to_h3"] == {
        "displacement_relative": 0.02,
        "reaction_relative": 0.02,
        "energy_relative": 0.02,
        "representative_sigma_xx_relative": 0.1,
    }
    assert contract["solver_contract"] == {
        "newton_tolerance": 1e-10,
        "load_increments": 12,
        "line_search": "existing/enabled",
        "linear_solver": "MINRES",
        "preconditioner": "Jacobi",
        "linear_rtol": 1e-11,
        "linear_atol": 1e-14,
        "linear_maxiter": 10000,
        "direct_fallback": False,
        "floor_aware_termination": True,
        "policy_source": "owner-approved C2R6 exact policy; no changes permitted in WP04-D",
        "accepted_state_authority": "UnifiedContinuationController + NonlinearStateTransaction",
        "checkpoint_failure_isolation": True,
    }


def test_required_hex8_meshes_and_consistent_load_are_recorded() -> None:
    contract = _load("hex8_contract.json")
    campaign = _load("hex8_campaign_result.json")
    mesh_sequence = contract["mesh_sequence"]
    assert isinstance(mesh_sequence, dict)
    expected = {
        "H1": ([16, 8, 8], 1377, 1024, 4131),
        "H2": ([24, 12, 12], 4225, 3456, 12675),
        "H3": ([32, 16, 16], 9537, 8192, 28611),
    }
    for label, (cells, nodes, elements, dofs) in expected.items():
        record = mesh_sequence[label]
        assert record["cells"] == cells
        assert record["nodes"] == nodes
        assert record["elements"] == elements
        assert record["dofs"] == dofs

        load_check = campaign["cases"][label]["load_check"]
        assert load_check["equal_share_used"] is False
        assert np.allclose(load_check["resultant"], [0.0, -50.0, 0.0], rtol=0.0, atol=1e-13)
        assert load_check["resultant_relative_error"] <= 1e-15
        assert np.allclose(load_check["reference_moment"], [12.5, 0.0, -200.0], rtol=0.0, atol=1e-12)


def test_h2_to_h3_passes_the_frozen_mesh_thresholds_without_h4() -> None:
    campaign = _load("hex8_campaign_result.json")
    audit = _load("g04_11_audit.json")

    assert campaign["status"] == "PASS_CANDIDATE"
    assert campaign["g04_11_status"] == "PASS"
    assert campaign["h4_status"] == "NOT_RUN_OPTIONAL_RESCUE_NOT_TRIGGERED"
    deltas = campaign["h2_to_h3"]
    assert deltas["threshold_status"] is True
    assert deltas["displacement"] == 0.01999034019793022
    assert deltas["energy"] == 0.019943897062970836
    assert deltas["reaction"] == 9.224898992711293e-14
    assert deltas["representative_sigma_xx"] == 0.046483239095767515
    assert audit["g04_11"] == "PASS"
    assert audit["mesh_convergence"] == deltas


def test_hex8_equilibrium_and_deformation_envelope_pass_for_required_meshes() -> None:
    campaign = _load("hex8_campaign_result.json")
    audit = _load("g04_11_audit.json")
    assert campaign["equilibrium_status"] is True
    assert campaign["deformation_envelope"]["status"] is True
    assert audit["equilibrium"] is True
    assert audit["envelope"]["status"] is True

    for label in ("H1", "H2", "H3"):
        case = _case(label)
        assert case["status"] == "PASS"
        observables = case["observables"]
        equilibrium = observables["equilibrium"]
        assert equilibrium["force_relative_error"] <= 1e-8
        assert equilibrium["moment_relative_error"] <= 1e-8
        assert observables["minimum_det_f"] >= 0.20
        assert 0.75 <= observables["minimum_principal_stretch"]
        assert observables["maximum_principal_stretch"] <= 1.30
        assert observables["maximum_green_lagrange_norm"] <= 0.30
        assert all(math.isfinite(float(value)) for value in equilibrium["reaction_resultant"])


def test_h1_replay_matches_required_observables_and_accepted_path() -> None:
    audit = _load("g04_11_audit.json")
    replay = audit["replay"]
    assert replay["status"] is True
    assert replay["accepted_load_path_equal"] is True
    assert replay["termination_classifications_equal"] is True
    for key in ("tip_displacement_relative", "reaction_relative", "energy_relative", "stress_relative"):
        assert replay[key] <= 1e-14

    first = _case("H1")
    second = _case("H1-replay")
    assert first["accepted_state_digests"] == second["accepted_state_digests"]
    assert first["accepted_load_factors"] == second["accepted_load_factors"]


def test_raw_hex8_arrays_are_reproducible_and_do_not_use_object_arrays() -> None:
    expected_shapes = {
        "h1_raw.npz": {"nodes": (1377, 3), "elements": (1024, 8), "displacement": (4131,)},
        "h1_replay_raw.npz": {"nodes": (1377, 3), "elements": (1024, 8), "displacement": (4131,)},
        "h2_raw.npz": {"nodes": (4225, 3), "elements": (3456, 8), "displacement": (12675,)},
        "h3_raw.npz": {"nodes": (9537, 3), "elements": (8192, 8), "displacement": (28611,)},
    }
    campaign = _load("hex8_campaign_result.json")
    labels = {"h1_raw.npz": "H1", "h1_replay_raw.npz": "H1-replay", "h2_raw.npz": "H2", "h3_raw.npz": "H3"}
    for name, shapes in expected_shapes.items():
        path = EVIDENCE / name
        with np.load(path, allow_pickle=False) as arrays:
            for key, shape in shapes.items():
                assert arrays[key].shape == shape
            for key in arrays.files:
                assert arrays[key].dtype.hasobject is False
                if np.issubdtype(arrays[key].dtype, np.number):
                    assert np.all(np.isfinite(arrays[key]))

        raw_info = campaign["cases"][labels[name]]["raw_npz"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == raw_info["sha256"]
        assert path.stat().st_size == raw_info["size_bytes"]


def test_hex8_telemetry_is_immediate_flush_jsonl_with_no_fallbacks() -> None:
    required_iteration_fields = {
        "case",
        "mesh",
        "load_step",
        "target_load_factor",
        "newton_iteration",
        "residual_norm",
        "relative_residual",
        "correction_norm",
        "line_search_alpha",
        "line_search_iterations",
        "linear_method",
        "krylov_iterations",
        "linear_relative_residual",
        "linear_backward_error_eta_inf",
        "linear_solve_time_s",
        "iteration_wall_time_s",
        "matrix_shape",
        "matrix_nnz",
        "RSS_bytes",
        "private_or_USS_bytes",
        "fallback_used",
        "status",
    }
    for label in ("h1", "h2", "h3"):
        rows = [json.loads(line) for line in (EVIDENCE / f"{label}_telemetry.jsonl").read_text().splitlines()]
        assert {row["event"] for row in rows} == {"ITERATION", "STEP_ACCEPTED", "SOLVE_COMPLETED"}
        iterations = [row for row in rows if row["event"] == "ITERATION"]
        assert iterations
        for row in iterations:
            assert required_iteration_fields <= row.keys()
            assert row["fallback_used"] is False
        linear_rows = [row for row in iterations if row["linear_method"] is not None]
        assert linear_rows
        for row in linear_rows:
            assert row["linear_method"] == "minres"
            assert math.isfinite(float(row["linear_backward_error_eta_inf"]))
        assert rows[-1]["event"] == "SOLVE_COMPLETED"


def test_small_load_support_is_retained_as_explicit_campaign_evidence() -> None:
    checks = _case("H1")["small_load_checks"]
    assert [row["multiplier"] for row in checks] == [0.1, 0.01, 0.001]
    assert all(row["status"] == "PASS" for row in checks)
    assert checks[-1]["displacement_relative_error"] < checks[0]["displacement_relative_error"]
    assert checks[-1]["reaction_relative_error"] < checks[0]["reaction_relative_error"]
