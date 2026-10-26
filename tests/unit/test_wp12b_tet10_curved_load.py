"""WP12-B TET10 curved pressure solve with an independent face oracle."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from solveur.core.model import FiniteElementModel
from solveur.core.solver import LinearStaticSolver
from wp12b_test_support import new_attempt_id, require_controller_scope, write_result_before_assertions


NODEID = "tests/unit/test_wp12b_tet10_curved_load.py::test_wp12b_tet10_curved_face_pressure_solve"
PRESSURE = 2.0


def _independent_pressure_resultant_moment(nodes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Integrate -p*n dA on the quadratic face using independent 8x8 Duffy-Gauss."""
    # Face order is explicitly encoded here rather than imported from production topology.
    face = nodes[np.asarray([0, 3, 2, 7, 9, 6])]
    abscissae, weights = np.polynomial.legendre.leggauss(8)
    abscissae = (abscissae + 1.0) / 2.0
    weights = weights / 2.0
    force = np.zeros(3)
    moment = np.zeros(3)
    for i, a in enumerate(abscissae):
        for j, b in enumerate(abscissae):
            r = float(a)
            s = float((1.0 - a) * b)
            lam = np.asarray([1.0 - r - s, r, s])
            shape = np.asarray(
                [lam[k] * (2.0 * lam[k] - 1.0) for k in range(3)]
                + [4.0 * lam[0] * lam[1], 4.0 * lam[1] * lam[2], 4.0 * lam[2] * lam[0]]
            )
            dndr = np.asarray(
                [1.0 - 4.0 * lam[0], 4.0 * lam[1] - 1.0, 0.0, 4.0 * (lam[0] - lam[1]), 4.0 * lam[2], -4.0 * lam[2]]
            )
            dnds = np.asarray(
                [1.0 - 4.0 * lam[0], 0.0, 4.0 * lam[2] - 1.0, -4.0 * lam[1], 4.0 * lam[1], 4.0 * (lam[0] - lam[2])]
            )
            point = shape @ face
            tangent_r = dndr @ face
            tangent_s = dnds @ face
            area_vector = np.cross(tangent_r, tangent_s)
            # Pressure acts inward, opposite to the oriented outward area vector.
            differential_force = -PRESSURE * area_vector * float(weights[i] * weights[j] * (1.0 - a))
            force += differential_force
            moment += np.cross(point, differential_force)
    return force, moment


def test_wp12b_tet10_curved_face_pressure_solve() -> None:
    evidence_root = require_controller_scope(30)
    nodes = np.asarray(
        [
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
            [0.5, 0, 0],
            [0.5, 0.5, 0],
            [0, 0.5, 0],
            [0, 0, 0.5],
            [0.5, 0, 0.5],
            [0, 0.5, 0.5],
        ],
        dtype=float,
    )
    nodes[4:] += np.asarray(
        [[0, 0.04, 0.01], [0.02, 0.02, 0.03], [0.03, 0, 0.01], [0.03, 0.01, 0], [0.01, 0.03, 0.02], [0.02, 0.01, 0.03]]
    )
    # Face 0 support: (1,2,3,5,9,8); face 1 load: (0,3,2,7,9,6).
    support_nodes = [1, 2, 3, 5, 9, 8]
    shared_face_nodes = set(support_nodes).intersection({0, 3, 2, 7, 9, 6})
    model = FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": "TET10", "nodes": list(range(10)), "material": "steel"}],
        materials={"steel": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3}},
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in support_nodes],
        distributed_loads=[{"type": "pressure", "element": 0, "face": 1, "value": PRESSURE}],
        units={"length": "m", "force": "N", "stress": "Pa", "pressure": "Pa"},
    )
    parameters = {
        "units": {"length": "m", "force": "N", "stress": "Pa", "pressure": "Pa"},
        "E_Pa": 210.0e9,
        "nu": 0.3,
        "pressure_Pa": PRESSURE,
        "loaded_face_local_nodes": [0, 3, 2, 7, 9, 6],
        "support_face_local_nodes": support_nodes,
    }
    repo_root = Path(__file__).resolve().parents[2]
    sources = [
        Path(__file__),
        Path(__file__).with_name("wp12b_test_support.py"),
        repo_root / "src/solveur/loads/integration.py",
        repo_root / "src/solveur/core/solvers/static.py",
        repo_root / "src/solveur/elements/solid/tet10.py",
    ]
    independent_force, independent_moment = _independent_pressure_resultant_moment(nodes)
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
    assert model.node_count == 10 and len(model.elements) == 1 and result.displacements.size == 30
    assert shared_face_nodes == {2, 3, 9}
    assert np.isfinite(result.displacements).all()
    load_audit = result.solver["load_assembly"]
    np.testing.assert_allclose(load_audit["resultant"], independent_force, rtol=1.0e-12, atol=1.0e-13)
    np.testing.assert_allclose(load_audit["moment_about_origin"], independent_moment, rtol=1.0e-12, atol=1.0e-13)
    np.testing.assert_allclose(
        independent_force, [1.0266666666666666, 0.013333333333333334, 0.013333333333333326], rtol=0.0, atol=1.0e-12
    )
    np.testing.assert_allclose(
        independent_moment, [0.00021333333333333504, 0.35365333333333343, -0.3532266666666668], rtol=0.0, atol=1.0e-12
    )
    equilibrium = result.audit.equilibrium
    assert equilibrium["free_relative_residual"] <= 1.0e-10
    assert equilibrium["force_balance_relative_error"] <= 1.0e-12
    assert equilibrium["moment_balance_relative_error"] <= 1.0e-12
    assert equilibrium["linear_energy_identity_relative_error"] <= 1.0e-10
    assert result.solver["converged"] is True
