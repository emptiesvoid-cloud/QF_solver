"""WP12-B assembled BEAM2 rotated line-load case (controller only)."""

from __future__ import annotations

import math
import time
from pathlib import Path

import numpy as np

from solveur.core.model import FiniteElementModel
from solveur.core.solver import LinearStaticSolver
from wp12b_test_support import new_attempt_id, require_controller_scope, write_result_before_assertions


E = 210.0e9
NU = 0.3
AREA = 0.01
IZ = 3.0e-6
LENGTH = 2.0
LOAD = 750.0
ANGLE = math.radians(37.0)
NODEID = "tests/unit/test_wp12b_beam2_continuity.py::test_wp12b_beam2_rotated_uniform_line_load"


def test_wp12b_beam2_rotated_uniform_line_load() -> None:
    evidence_root = require_controller_scope(12)
    direction = np.asarray([math.cos(ANGLE), math.sin(ANGLE), 0.0])
    transverse = np.asarray([-math.sin(ANGLE), math.cos(ANGLE), 0.0])
    end = LENGTH * direction
    model = FiniteElementModel.from_raw(
        nodes=[[0.0, 0.0, 0.0], end.tolist()],
        elements=[{"type": "BEAM2", "nodes": [0, 1], "material": "beam"}],
        materials={
            "beam": {
                "type": "beam_isotropic",
                "E": E,
                "nu": NU,
                "A": AREA,
                "Iy": 2.0e-6,
                "Iz": IZ,
                "J": 5.0e-6,
                "reference_vector": transverse.tolist(),
            }
        },
        fixed_dofs=[{"node": 0, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]}],
        distributed_loads=[
            {"type": "line_load", "element": 0, "value": [0.0, LOAD, 0.0], "coordinate_system": "local"}
        ],
        units={"length": "m", "force": "N", "stress": "Pa", "line_load": "N/m"},
    )
    parameters = {
        "units": {"length": "m", "force": "N", "stress": "Pa", "line_load": "N/m"},
        "E_Pa": E,
        "nu": NU,
        "A_m2": AREA,
        "Iz_m4": IZ,
        "L_m": LENGTH,
        "q_N_per_m": LOAD,
    }
    repo_root = Path(__file__).resolve().parents[2]
    sources = [
        Path(__file__),
        Path(__file__).with_name("wp12b_test_support.py"),
        repo_root / "src/solveur/loads/integration.py",
        repo_root / "src/solveur/core/solvers/static.py",
        repo_root / "src/solveur/elements/beam/beam2.py",
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
    assert model.node_count == 2 and len(model.elements) == 1 and result.displacements.size == 12
    assert np.isfinite(result.displacements).all()
    expected_translation = LOAD * LENGTH**4 / (8.0 * E * IZ)
    expected_translation += LOAD * LENGTH**2 / (2.0 * (5.0 / 6.0) * (E / (2.0 * (1.0 + NU))) * AREA)
    tip_translation = float(np.dot(result.displacements[6:9], transverse))
    np.testing.assert_allclose(tip_translation, expected_translation, rtol=1.0e-10, atol=1.0e-14)
    load_audit = result.solver["load_assembly"]
    np.testing.assert_allclose(load_audit["resultant"], LOAD * LENGTH * transverse, rtol=1.0e-12, atol=1.0e-12)
    expected_moment = np.cross(end / 2.0, LOAD * LENGTH * transverse)
    np.testing.assert_allclose(load_audit["moment_about_origin"], expected_moment, rtol=1.0e-12, atol=1.0e-12)
    equilibrium = result.audit.equilibrium
    assert equilibrium["free_relative_residual"] <= 1.0e-10
    assert equilibrium["force_balance_relative_error"] <= 1.0e-12
    assert equilibrium["moment_balance_relative_error"] <= 1.0e-12
    assert equilibrium["linear_energy_identity_relative_error"] <= 1.0e-10
    assert result.solver["converged"] is True
