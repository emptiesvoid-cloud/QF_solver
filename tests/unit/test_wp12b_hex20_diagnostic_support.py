"""Synthetic checks for HEX20 diagnostic provenance and evidence helpers (no FEM solve)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.sparse import csr_matrix, diags

from wp12b_hex20_diagnostic_support import (
    ControllerBinding,
    assert_historical_r4_acceptance,
    independent_face_load,
    require_diagnostic_binding,
    residual_metrics,
    write_diagnostic_sidecar,
)


def _hex20_coordinates() -> np.ndarray:
    corners = np.asarray(
        [
            [0, -0.5, -0.5],
            [1, -0.5, -0.5],
            [1, 0.5, -0.5],
            [0, 0.5, -0.5],
            [0, -0.5, 0.5],
            [1, -0.5, 0.5],
            [1, 0.5, 0.5],
            [0, 0.5, 0.5],
        ],
        dtype=np.float64,
    )
    edges = (
        (0, 1),
        (0, 3),
        (0, 4),
        (1, 2),
        (1, 5),
        (2, 3),
        (2, 6),
        (3, 7),
        (4, 5),
        (4, 7),
        (5, 6),
        (6, 7),
    )
    return np.vstack([corners, [(corners[first] + corners[second]) / 2.0 for first, second in edges]])


def test_binding_requires_exact_scope_attempt_and_manifest(tmp_path: Path) -> None:
    run_json_path = tmp_path / "run.json"
    run_json_path.write_text(
        json.dumps(
            {
                "controller_attempt_id": "dev-0123456789ab-attempt-1",
                "state": "RUNNING",
                "worktree_id": "wp12_hex20_affine_diagnostic",
                "series_id": "dev-0123456789ab",
                "attempt": 1,
                "target": [
                    "tests/unit/test_wp12b_hex20_affine_diagnostic.py::test_wp12b_hex20_affine_patch_archives_residual"
                ],
                "identity": {"head": "deadbeef"},
                "execution_manifest": {
                    "authorization_id": "WP12B-HEX20-AFFINE-DIAG-R1",
                    "sha256": "a" * 64,
                },
                "wp12_case_selection": {"selected_dofs": 60},
            }
        ),
        encoding="utf-8",
    )
    environment = {
        "QF_DEVELOPMENT_AUTONOMOUS": "1",
        "QF_DEV_WORKTREE_ID": "wp12_hex20_affine_diagnostic",
        "QF_DEV_SELECTED_DOFS": "60",
        "QF_DEV_ATTEMPT_ID": "dev-0123456789ab-attempt-1",
        "QF_DEV_MANIFEST_ID": "WP12B-HEX20-AFFINE-DIAG-R1",
        "QF_DEV_MANIFEST_SHA256": "a" * 64,
        "QF_DEV_EVIDENCE_ROOT": str(tmp_path),
        "QF_DEV_RUN_JSON_PATH": str(run_json_path),
    }

    binding = require_diagnostic_binding(environment)
    assert binding.worktree_id == "wp12_hex20_affine_diagnostic"
    assert binding.attempt_id == environment["QF_DEV_ATTEMPT_ID"]
    assert binding.manifest_id == environment["QF_DEV_MANIFEST_ID"]
    assert binding.manifest_sha256 == "a" * 64
    assert binding.selected_dofs == 60

    environment["QF_DEV_WORKTREE_ID"] = "wp12_elements_loads_corrective"
    with pytest.raises(RuntimeError, match="QF_DEV_WORKTREE_ID"):
        require_diagnostic_binding(environment)


def test_independent_face_oracle_uses_corner_and_edge_weights() -> None:
    nodes = _hex20_coordinates()
    stress = np.diag([10.0, 20.0, 30.0])
    face = independent_face_load(nodes, face=3, stress=stress)

    assert face["area_m2"] == 1.0
    assert face["corner_nodes"] == [1, 2, 5, 6]
    assert face["midside_nodes"] == [11, 12, 14, 18]
    np.testing.assert_allclose(face["traction_Pa"], [10.0, 0.0, 0.0])
    for node in face["corner_nodes"]:
        np.testing.assert_allclose(face["nodal_forces_N"][node], [-10.0 / 12.0, 0.0, 0.0])
    for node in face["midside_nodes"]:
        np.testing.assert_allclose(face["nodal_forces_N"][node], [10.0 / 3.0, 0.0, 0.0])
    np.testing.assert_allclose(face["resultant_N"], [10.0, 0.0, 0.0])
    np.testing.assert_allclose(face["moment_about_origin_Nm"], [0.0, 0.0, 0.0])


def test_affine_and_residual_oracle_on_synthetic_linear_system() -> None:
    stiffness = diags([2.0, 3.0, 4.0], format="csr")
    affine = np.asarray([1.0, 2.0, 3.0])
    loads = stiffness @ affine
    fixed = np.asarray([0], dtype=np.int64)

    metrics = residual_metrics(stiffness, loads, affine, affine, fixed)

    np.testing.assert_array_equal(metrics["free_indices"], [1, 2])
    np.testing.assert_allclose(metrics["r_affine_N"], [0.0, 0.0, 0.0])
    assert metrics["r_affine_eta_inf"] == 0.0
    np.testing.assert_allclose(metrics["calculated"]["u_difference_from_affine_m"], np.zeros(3))


def test_sidecar_is_atomic_bound_and_refuses_overwrite(tmp_path: Path) -> None:
    model = SimpleNamespace(
        nodes=_hex20_coordinates(),
        elements=[SimpleNamespace(type="HEX20", nodes=tuple(range(20)), material="steel")],
        node_count=20,
        materials={"steel": {"E": 210.0e9, "nu": 0.3}},
        fixed_dofs=[],
        loads=[],
        distributed_loads=[],
    )
    binding = ControllerBinding(
        worktree_id="wp12_hex20_affine_diagnostic",
        attempt_id="dev-0123456789ab-attempt-1",
        manifest_id="WP12B-HEX20-AFFINE-DIAG-R1",
        manifest_sha256="a" * 64,
        selected_dofs=60,
        evidence_root=tmp_path,
        run_json_path=tmp_path / "run.json",
    )
    capture = {
        "stiffness_calls": 0,
        "load_calls": 0,
        "fixed_index_calls": 0,
        "face_integrations": [
            {
                "face": 3,
                "index": 0,
                "indices": np.asarray([], dtype=np.int64),
                "values": np.asarray([], dtype=np.float64),
                "details": {"synthetic": True},
            }
        ],
        "stiffness": csr_matrix((60, 60), dtype=np.float64),
        "loads": np.zeros(60, dtype=np.float64),
        "fixed_indices": np.asarray([], dtype=np.int64),
    }
    stress = np.diag([2.0, 3.0, 4.0])
    equilibrium = {
        "reactions": np.zeros(60),
        "secant_internal_energy": 0.5,
        "external_work_at_final_load": 1.0,
        "linear_energy_identity_relative_error": 0.0,
        "free_relative_residual": 0.0,
        "force_balance_relative_error": 0.0,
        "moment_balance_relative_error": 0.0,
    }
    result = SimpleNamespace(
        status="PASS",
        displacements=np.zeros(60),
        element_results=[{"stress": np.asarray([2.0, 3.0, 4.0, 0.0, 0.0, 0.0])}],
        audit=SimpleNamespace(
            equilibrium=equilibrium,
            mesh_status="PASS",
            mesh_details={"synthetic": True},
            diagnostic={"element_quality": {"synthetic": 1.0}},
        ),
        node_count=20,
        element_count=1,
        solver={"converged": True},
    )
    expected_face = {
        "face": 3,
        "vector_N": np.zeros(60),
        "resultant_N": np.zeros(3),
        "moment_about_origin_Nm": np.zeros(3),
    }
    source = Path(__file__).resolve()
    kwargs = {
        "binding": binding,
        "nodeid": "synthetic::no_fem",
        "model": model,
        "case_parameters": {
            "units": {"length": "m", "force": "N", "stress": "Pa"},
            "volume_m3": 1.0,
        },
        "source_paths": [source],
        "repo_root": source.parents[2],
        "capture": capture,
        "result": result,
        "solve_seconds": 0.0,
        "exception": None,
        "affine_data": {
            "u_affine_m": np.zeros(60, dtype=np.float64),
            "all_six_analytic_boundary_loads_N": np.zeros(60, dtype=np.float64),
            "strain_tensor": np.diag([0.5, 0.0, 0.0]),
            "stress_tensor_Pa": stress,
        },
        "independent_faces": [expected_face],
    }

    path, digest = write_diagnostic_sidecar(**kwargs)
    record = json.loads(path.read_text(encoding="utf-8"))
    assert path.is_file()
    assert len(digest) == 64
    assert record["controller"]["controller_attempt_id"] == binding.attempt_id
    assert record["controller"]["manifest_sha256"] == binding.manifest_sha256
    assert record["schema"] == "qfsolver-wp12b-hex20-affine-diagnostic-v2"
    assert record["assembly"]["K_csr"]["shape"] == [60, 60]
    assert len(record["assembly"]["K_csr"]["sha256_canonical_csr"]) == 64
    assert record["residuals"]["r_affine_N"] == [0.0] * 60
    assert record["units"]["stress"] == "Pa"
    assert record["result"]["recovered_stress_voigt_Pa"] == [2.0, 3.0, 4.0, 0.0, 0.0, 0.0]
    assert record["result"]["historical_r4_energy_reference_J"] == 0.5
    assert record["assembly"]["face_contributions"][0]["comparison_units"] == "N"
    assert record["assembly"]["face_contributions"][0]["acceptance"].startswith("OBSERVATIONAL_ONLY")
    assert record["diagnostic_criteria"]["historical_r4_assertions"]["recovered_stress"]["atol_Pa"] == 1.0e-4
    assert record["diagnostic_criteria"]["proposed_owner_limits_not_active"]["status"] == (
        "OWNER_APPROVAL_REQUIRED; NOT ASSERTED"
    )
    assert "||K[free,:] @ u_affine - F[free]||_inf" in record["residuals"]["r_affine_eta_inf_definition"]
    with pytest.raises(AssertionError):
        assert_historical_r4_acceptance(
            result=result,
            model=model,
            exact_displacements=np.zeros(60),
            expected_stress_voigt=np.asarray([2.1, 3.0, 4.0, 0.0, 0.0, 0.0]),
            exact_energy_j=0.5,
        )
    assert path.is_file()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    with pytest.raises(FileExistsError):
        write_diagnostic_sidecar(**kwargs)


def test_historical_r4_assertions_use_archived_acceptance_values() -> None:
    expected_displacements = np.zeros(60, dtype=np.float64)
    expected_stress = np.asarray([2.0, 3.0, 4.0, 0.0, 0.0, 0.0])
    exact_energy = 0.5
    result = SimpleNamespace(
        status="PASS",
        displacements=expected_displacements.copy(),
        element_results=[{"stress": expected_stress.copy()}],
        audit=SimpleNamespace(
            mesh_status="PASS",
            equilibrium={
                "secant_internal_energy": exact_energy,
                "external_work_at_final_load": 2.0 * exact_energy,
                "free_relative_residual": 1.0e-11,
                "force_balance_relative_error": 1.0e-13,
                "moment_balance_relative_error": 1.0e-13,
                "linear_energy_identity_relative_error": 1.0e-11,
            },
        ),
        solver={"converged": True},
    )
    model = SimpleNamespace(node_count=20, elements=[object()])

    assert_historical_r4_acceptance(
        result=result,
        model=model,
        exact_displacements=expected_displacements,
        expected_stress_voigt=expected_stress,
        exact_energy_j=exact_energy,
    )

    result.element_results[0]["stress"][0] += 1.0e-3
    with pytest.raises(AssertionError):
        assert_historical_r4_acceptance(
            result=result,
            model=model,
            exact_displacements=expected_displacements,
            expected_stress_voigt=expected_stress,
            exact_energy_j=exact_energy,
        )
