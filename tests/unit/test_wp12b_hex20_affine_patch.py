"""WP12-B HEX20 affine uniaxial-strain traction patch (controller only)."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from solveur.core.model import FiniteElementModel
from solveur.core.solver import LinearStaticSolver
from wp12b_test_support import new_attempt_id, require_controller_scope, write_result_before_assertions


NODEID = "tests/unit/test_wp12b_hex20_affine_patch.py::test_wp12b_hex20_uniaxial_traction_patch"
YOUNG = 210.0e9
POISSON = 0.3
STRAIN = 1.0e-4


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
        dtype=float,
    )
    edges = ((0, 1), (0, 3), (0, 4), (1, 2), (1, 5), (2, 3), (2, 6), (3, 7), (4, 5), (4, 7), (5, 6), (6, 7))
    return np.vstack([corners, [(corners[first] + corners[second]) / 2.0 for first, second in edges]])


def test_wp12b_hex20_uniaxial_traction_patch() -> None:
    evidence_root = require_controller_scope(60)
    nodes = _hex20_coordinates()
    lame_lambda = YOUNG * POISSON / ((1.0 + POISSON) * (1.0 - 2.0 * POISSON))
    shear_mu = YOUNG / (2.0 * (1.0 + POISSON))
    stress = np.asarray(
        [
            [(lame_lambda + 2.0 * shear_mu) * STRAIN, 0.0, 0.0],
            [0.0, lame_lambda * STRAIN, 0.0],
            [0.0, 0.0, lame_lambda * STRAIN],
        ]
    )
    # Canonical oriented faces 0..4 are loaded; face 5 (x=0) is fixed.
    face_tractions = [
        [0.0, 0.0, -stress[2, 2]],
        [0.0, 0.0, stress[2, 2]],
        [0.0, -stress[1, 1], 0.0],
        [stress[0, 0], 0.0, 0.0],
        [0.0, stress[1, 1], 0.0],
    ]
    model = FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": "HEX20", "nodes": list(range(20)), "material": "steel"}],
        materials={"steel": {"type": "isotropic_3d", "E": YOUNG, "nu": POISSON}},
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in [0, 3, 4, 7, 9, 10, 15, 17]],
        distributed_loads=[
            {"type": "surface_traction", "element": 0, "face": face, "value": traction, "coordinate_system": "global"}
            for face, traction in enumerate(face_tractions)
        ],
        units={"length": "m", "force": "N", "stress": "Pa"},
    )
    parameters = {
        "units": {"length": "m", "force": "N", "stress": "Pa"},
        "E_Pa": YOUNG,
        "nu": POISSON,
        "strain_xx": STRAIN,
        "volume_m3": 1.0,
        "stress_Pa": stress.tolist(),
        "loaded_faces": [0, 1, 2, 3, 4],
        "fixed_face": 5,
    }
    repo_root = Path(__file__).resolve().parents[2]
    sources = [
        Path(__file__),
        Path(__file__).with_name("wp12b_test_support.py"),
        repo_root / "src/solveur/loads/integration.py",
        repo_root / "src/solveur/core/solvers/static.py",
        repo_root / "src/solveur/elements/solid/hex20.py",
    ]
    attempt_id = new_attempt_id()
    started = time.perf_counter()
    result = LinearStaticSolver().solve(model)
    solve_seconds = time.perf_counter() - started
    evidence = write_result_before_assertions(
        evidence_root=evidence_root,
        nodeid=NODEID,
        model=model,
        result=result,
        case_parameters=parameters,
        source_paths=sources,
        repo_root=repo_root,
        solve_seconds=solve_seconds,
        attempt_id=attempt_id,
    )

    assert evidence.is_file()
    assert result.status == "PASS"
    assert result.audit.mesh_status == "PASS"
    assert model.node_count == 20 and len(model.elements) == 1 and result.displacements.size == 60
    assert np.isfinite(result.displacements).all()
    exact_displacements = np.column_stack((STRAIN * nodes[:, 0], np.zeros(20), np.zeros(20))).ravel()
    np.testing.assert_allclose(result.displacements, exact_displacements, rtol=1.0e-10, atol=1.0e-13)
    recovered_stress = np.asarray(result.element_results[0]["stress"], dtype=float)
    expected_voigt_stress = np.asarray([stress[0, 0], stress[1, 1], stress[2, 2], 0.0, 0.0, 0.0])
    np.testing.assert_allclose(recovered_stress, expected_voigt_stress, rtol=1.0e-10, atol=1.0e-4)
    equilibrium = result.audit.equilibrium
    exact_energy = 0.5 * stress[0, 0] * STRAIN
    assert abs(equilibrium["secant_internal_energy"] - exact_energy) <= 1.0e-10 * exact_energy
    assert abs(equilibrium["external_work_at_final_load"] - 2.0 * exact_energy) <= 1.0e-10 * exact_energy
    assert equilibrium["free_relative_residual"] <= 1.0e-10
    assert equilibrium["force_balance_relative_error"] <= 1.0e-12
    assert equilibrium["moment_balance_relative_error"] <= 1.0e-12
    assert equilibrium["linear_energy_identity_relative_error"] <= 1.0e-10
    assert result.solver["converged"] is True
