"""Prospective one-solve HEX20 patch diagnostic with pre-assertion matrix capture."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
from solveur.core.model import FiniteElementModel
from solveur.core.solver import LinearStaticSolver
from wp12b_hex20_diagnostic_support import (
    DIAGNOSTIC_NODEID,
    DIAGNOSTIC_R2_SCOPE_ID,
    assert_r2_face_nodal_load,
    affine_vector,
    assert_historical_r4_acceptance,
    capture_solver_assembly,
    independent_face_load,
    require_diagnostic_binding,
    write_diagnostic_sidecar,
)


YOUNG_PA = 210.0e9
POISSON = 0.3
STRAIN_XX = 1.0e-4


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


def _isotropic_stress() -> np.ndarray:
    lame_lambda = YOUNG_PA * POISSON / ((1.0 + POISSON) * (1.0 - 2.0 * POISSON))
    shear_mu = YOUNG_PA / (2.0 * (1.0 + POISSON))
    return np.diag(
        [
            (lame_lambda + 2.0 * shear_mu) * STRAIN_XX,
            lame_lambda * STRAIN_XX,
            lame_lambda * STRAIN_XX,
        ]
    )


def _diagnostic_model(nodes: np.ndarray, stress: np.ndarray) -> FiniteElementModel:
    # Five applied faces; the x=0 face is restrained and supplies the analytic reaction oracle.
    face_normals = (
        (0.0, 0.0, -1.0),
        (0.0, 0.0, 1.0),
        (0.0, -1.0, 0.0),
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
    )
    tractions = [stress @ np.asarray(normal) for normal in face_normals]
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": "HEX20", "nodes": list(range(20)), "material": "steel"}],
        materials={"steel": {"type": "isotropic_3d", "E": YOUNG_PA, "nu": POISSON}},
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in (0, 3, 4, 7, 9, 10, 15, 17)],
        distributed_loads=[
            {
                "type": "surface_traction",
                "element": 0,
                "face": face,
                "value": tractions[face].tolist(),
                "coordinate_system": "global",
            }
            for face in range(5)
        ],
        units={"length": "m", "force": "N", "stress": "Pa"},
    )


def test_wp12b_hex20_affine_patch_archives_residual(monkeypatch) -> None:
    binding = require_diagnostic_binding()
    nodes = _hex20_coordinates()
    stress = _isotropic_stress()
    affine = affine_vector(nodes, STRAIN_XX)
    model = _diagnostic_model(nodes, stress)
    parameters = {
        "units": {"length": "m", "force": "N", "stress": "Pa"},
        "E_Pa": YOUNG_PA,
        "nu": POISSON,
        "strain_xx": STRAIN_XX,
        "strain_tensor": np.diag([STRAIN_XX, 0.0, 0.0]),
        "stress_tensor_Pa": stress,
        "volume_m3": 1.0,
        "geometry": "one 1m x 1m x 1m Gmsh-ordered HEX20; x in [0,1]m",
        "fixed_nodes": [0, 3, 4, 7, 9, 10, 15, 17],
        "loaded_faces": [0, 1, 2, 3, 4],
        "restrained_face": 5,
        "face_load_oracle": "geometric plane selection; QUAD8 corner=-A/12, edge-midpoint=+A/3",
    }
    repo_root = Path(__file__).resolve().parents[2]
    source_paths = [
        Path(__file__),
        Path(__file__).with_name("wp12b_hex20_diagnostic_support.py"),
        repo_root / "src/solveur/loads/integration.py",
        repo_root / "src/solveur/core/solvers/static.py",
        repo_root / "src/solveur/core/assembly/assembler.py",
        repo_root / "src/solveur/elements/solid/hex20.py",
    ]

    independent_faces = [independent_face_load(nodes, face, stress) for face in range(6)]
    expected_full_boundary = sum(
        (np.asarray(face["vector_N"], dtype=np.float64) for face in independent_faces), start=np.zeros(60)
    )
    affine_data = {
        "strain_tensor": np.diag([STRAIN_XX, 0.0, 0.0]),
        "stress_tensor_Pa": stress,
        "traction_vectors_by_face_Pa": {str(face["face"]): face["traction_Pa"] for face in independent_faces},
        "u_affine_m": affine,
        "all_six_analytic_boundary_loads_N": expected_full_boundary,
        "all_six_analytic_boundary_resultant_N": sum(
            (np.asarray(face["resultant_N"]) for face in independent_faces), start=np.zeros(3)
        ),
        "all_six_analytic_boundary_moment_Nm": sum(
            (np.asarray(face["moment_about_origin_Nm"]) for face in independent_faces), start=np.zeros(3)
        ),
        "analytic_face_oracles": independent_faces,
        "oracle_independence": (
            "face membership comes from nodal coordinates and axis planes; area from geometric extents; "
            "traction from sigma @ n; no production HEX20 face table or quadrature routine is called"
        ),
    }

    solver = LinearStaticSolver()
    capture = capture_solver_assembly(solver, monkeypatch)
    result = None
    solve_exception = None
    started = time.perf_counter()
    try:
        result = solver.solve(model)
    except Exception as exc:  # Archive captured assembly even if the linear solve raises.
        solve_exception = exc
    solve_seconds = time.perf_counter() - started

    evidence, _evidence_sha256 = write_diagnostic_sidecar(
        binding=binding,
        nodeid=DIAGNOSTIC_NODEID,
        model=model,
        case_parameters=parameters,
        source_paths=source_paths,
        repo_root=repo_root,
        capture=capture,
        result=result,
        solve_seconds=solve_seconds,
        exception=solve_exception,
        affine_data=affine_data,
        independent_faces=independent_faces,
    )
    # No assertion occurs before the raw matrices, vectors and oracle comparisons are archived.
    assert evidence.is_file()
    if solve_exception is not None:
        raise AssertionError("HEX20 diagnostic solve raised after pre-assertion evidence capture.") from solve_exception
    assert result is not None
    assert capture["stiffness_calls"] == 1
    assert capture["load_calls"] == 1
    assert capture["fixed_index_calls"] == 1
    assert len(capture["face_integrations"]) == 5
    assert capture["stiffness"].shape == (60, 60)
    assert capture["loads"].shape == (60,)
    assert np.isfinite(capture["stiffness"].data).all()
    assert np.isfinite(capture["loads"]).all()
    assert result.status == "PASS"
    assert result.displacements.shape == (60,)
    assert np.isfinite(result.displacements).all()

    for actual, expected in zip(capture["face_integrations"], independent_faces[:5], strict=True):
        assert actual["face"] == expected["face"]
        actual_vector = np.zeros(60, dtype=np.float64)
        np.add.at(actual_vector, actual["indices"], actual["values"])
        assert actual_vector.shape == expected["vector_N"].shape
        assert np.isfinite(actual_vector).all()
        if binding.worktree_id == DIAGNOSTIC_R2_SCOPE_ID:
            assert_r2_face_nodal_load(actual_vector, np.asarray(expected["vector_N"]))
    production_faces = np.zeros(60, dtype=np.float64)
    for actual in capture["face_integrations"]:
        np.add.at(production_faces, actual["indices"], actual["values"])
    assert production_faces.shape == capture["loads"].shape
    assert np.isfinite(production_faces).all()

    fixed_nodes = (0, 3, 4, 7, 9, 10, 15, 17)
    expected_fixed_indices = np.asarray(
        [3 * node + component for node in fixed_nodes for component in range(3)], dtype=np.int64
    )
    np.testing.assert_array_equal(capture["fixed_indices"], expected_fixed_indices)

    from wp12b_hex20_diagnostic_support import residual_metrics

    metrics = residual_metrics(
        capture["stiffness"], capture["loads"], affine, result.displacements, capture["fixed_indices"]
    )
    assert metrics["r_affine_N"].shape == (60,)
    assert metrics["r_affine_free_N"].shape == (36,)
    assert metrics["r_affine_fixed_N"].shape == (24,)
    assert np.isfinite(metrics["r_affine_N"]).all()

    expected_stress_voigt = np.asarray([stress[0, 0], stress[1, 1], stress[2, 2], 0.0, 0.0, 0.0])
    exact_energy_j = 0.5 * float(stress[0, 0]) * STRAIN_XX * 1.0
    assert_historical_r4_acceptance(
        result=result,
        model=model,
        exact_displacements=affine,
        expected_stress_voigt=expected_stress_voigt,
        exact_energy_j=exact_energy_j,
    )
