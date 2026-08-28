from __future__ import annotations

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from solveur.api import list_methods, solve_model
from solveur.core.buckling import LinearBucklingSolver, _indefinite_generalized_critical_factor
from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.core.geometric_assembly import build_total_lagrangian_assembly
from solveur.core.model import FiniteElementModel


def _model(*, load: float = -1.0, analysis: dict[str, object] | None = None) -> FiniteElementModel:
    settings = {
        "type": "linear_buckling",
        "method": "eigsh",
        "preload_factor": 1.0,
        "load_increments": 4,
        "maximum_factor": 100.0,
    }
    settings.update(analysis or {})
    return FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.3}},
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
        loads=[{"node": 1, "dof": "UX", "value": load}],
        analysis=settings,
    )


def test_linear_buckling_is_routed_through_sparse_eigensolver() -> None:
    result = solve_model(_model(), enforce_policy=False)
    assert result.status == "PASS"
    assert result.analysis == "linear_buckling"
    assert result.method == "eigsh"
    assert result.solver["backend"] == "scipy.sparse.linalg.eigsh"
    assert result.solver["critical_factor"] > 0.0
    assert result.solver["critical_bracket"]["lower"] < result.solver["critical_factor"]
    assert result.solver["critical_eigenproblem"] == "(K + lambda * Kg) phi = 0"
    assert result.solver["eigen_formulation"] == "generalized_eigsh"
    assert result.solver["geometric_tangent_source"] == "initial_stress_second_piola"
    assert result.solver["geometric_tangent_nnz"] > 0
    assert result.solver["critical_mode_norm"] == pytest.approx(1.0)
    assert np.isfinite(result.solver["critical_mode_residual_relative"])
    assert result.solver["critical_mode_residual_relative"] < 1.0e-3


def test_linear_buckling_supports_the_hex8_geometric_tangent_path() -> None:
    nodes = [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]]
    model = FiniteElementModel.from_raw(
        nodes=nodes,
        elements=[{"type": "HEX8", "nodes": list(range(8)), "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.3}},
        fixed_dofs=[{"node": index, "dofs": ["UX", "UY", "UZ"]} for index in (0, 3, 4, 7)],
        loads=[{"node": 1, "dof": "UX", "value": -1.0}],
        analysis={"type": "linear_buckling", "load_increments": 4, "maximum_factor": 100.0},
    )
    result = solve_model(model, enforce_policy=False)
    assert result.status == "PASS"
    assert result.solver["critical_factor"] > 0.0
    assert result.solver["critical_mode_free_dof_count"] > 0
    assert result.solver["critical_mode_residual_relative"] < 1.0e-3


@pytest.mark.parametrize("family", ["TET10", "HEX20"])
def test_linear_buckling_supports_high_order_tl_assembly(family: str) -> None:
    if family == "TET10":
        corners = np.asarray(
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        )
        edges = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
        nodes = np.vstack([corners, [(corners[first] + corners[second]) / 2.0 for first, second in edges]])
    else:
        corners = np.asarray(
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
             [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0]]
        )
        edges = ((0, 1), (0, 3), (0, 4), (1, 2), (1, 5), (2, 3), (2, 6), (3, 7),
                 (4, 5), (4, 7), (5, 6), (6, 7))
        nodes = np.vstack([corners, [(corners[first] + corners[second]) / 2.0 for first, second in edges]])
    fixed = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    loaded = np.flatnonzero(np.isclose(nodes[:, 0], 1.0))
    reference_load = -0.1 if family == "TET10" else -10.0
    model = FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": family, "nodes": list(range(len(nodes))), "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.3}},
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed],
        loads=[{"node": int(node), "dof": "UX", "value": reference_load / len(loaded)} for node in loaded],
        analysis={
            "type": "linear_buckling",
            "method": "eigsh",
            "load_increments": 6,
            "maximum_factor": 100.0,
        },
    )

    result = solve_model(model, enforce_policy=False)

    assert result.status == "PASS"
    assert result.solver["critical_factor"] > 0.0
    assert result.solver["critical_mode_residual_relative"] < 1.0e-3
    assert result.solver["scope"].endswith("tet4-tet10-hex8-hex20")


def test_tet4_geometric_tangent_contains_only_initial_stress_contribution() -> None:
    model = _model()
    assembly = build_total_lagrangian_assembly(model)
    displacement = np.zeros(assembly.ndof, dtype=float)
    displacement[3] = -1.0e-3
    displacement[4] = 2.0e-3
    displacement[5] = -1.5e-3
    geometric = assembly.geometric_tangent(displacement).toarray()
    local = assembly._local_displacements(displacement)
    _, stress = assembly._kinematics(local)
    scalar = np.einsum("maJ,mJL,mbL->mab", assembly.gradients, stress, assembly.gradients)
    expected_blocks = assembly.volumes[:, None, None, None, None] * np.einsum(
        "mab,ik->maibk", scalar, np.eye(3)
    )
    expected_local = expected_blocks.reshape(-1, 12, 12)
    expected = np.zeros_like(geometric)
    for element_dofs, local_matrix in zip(assembly.element_dofs, expected_local, strict=True):
        expected[np.ix_(element_dofs, element_dofs)] += local_matrix
    np.testing.assert_allclose(geometric, expected, rtol=1.0e-12, atol=1.0e-12)


def test_linear_buckling_rejects_tension_without_bracket() -> None:
    with pytest.raises(NumericalConvergenceError, match="could not bracket"):
        solve_model(_model(load=1.0), enforce_policy=False)


def test_linear_buckling_rejects_non_isotropic_scope() -> None:
    model = _model()
    model.materials["solid"]["type"] = "nonlinear_isotropic_3d"
    with pytest.raises(InputValidationError, match="isotropic_3d"):
        solve_model(model, enforce_policy=False)


def test_linear_buckling_rejects_invalid_bracketing_controls() -> None:
    model = _model(analysis={"initial_factor": 10.0, "maximum_factor": 10.0})
    with pytest.raises(InputValidationError, match="maximum_factor"):
        solve_model(model, enforce_policy=False)


def test_linear_buckling_reports_sparse_bracket_fallback_for_indefinite_geometric_tangent() -> None:
    initial = csr_matrix(np.diag([2.0, 3.0, 4.0]))
    geometric = csr_matrix(np.diag([-1.0, -1.0, 1.0]))

    factor, mode, bracket = LinearBucklingSolver._critical_factor(
        initial,
        geometric,
        np.arange(3, dtype=int),
        3,
        {"initial_factor": 1.0, "maximum_factor": 10.0},
    )

    assert factor == pytest.approx(2.0, rel=1.0e-6)
    assert np.linalg.norm(mode) == pytest.approx(1.0)
    assert bracket["method"] == "bracketed_sparse_eigenvalue"
    assert "positive-definite" in str(bracket["generalized_fallback_reason"])


def test_linear_buckling_refines_indefinite_tangent_with_sparse_generalized_shift_invert() -> None:
    initial = csr_matrix(np.diag([2.0, 3.0, 4.0, 5.0]))
    geometric = csr_matrix(np.diag([-1.0, -1.0, 1.0, 2.0]))

    factor, mode, bracket = LinearBucklingSolver._critical_factor(
        initial,
        geometric,
        np.arange(4, dtype=int),
        4,
        {"initial_factor": 1.0, "maximum_factor": 10.0},
    )

    assert factor == pytest.approx(2.0, rel=1.0e-6)
    assert np.linalg.norm(mode) == pytest.approx(1.0)
    assert bracket["method"] == "generalized_eigs_shift_invert"
    assert bracket["mass_matrix"] == "-geometric_tangent"
    assert bracket["shift_invert_strategy"] == "strictly_interior_dyadic_bracket"
    assert bracket["lower"] < bracket["shift_invert_sigma"] < bracket["upper"]


def test_indefinite_shift_invert_retries_when_midpoint_is_exactly_singular() -> None:
    initial = csr_matrix(np.diag([2.0, 3.0, 4.0, 5.0]))
    geometric = csr_matrix(np.diag([-1.0, -1.0, 1.0, 2.0]))
    result = _indefinite_generalized_critical_factor(
        initial,
        geometric,
        np.arange(4, dtype=int),
        4,
        lower_factor=1.9999,
        upper_factor=2.0001,
        eigensolver_tolerance=1.0e-8,
        eigensolver_maxiter=1000,
    )

    assert result is not None
    factor, mode, shift, attempted_shifts = result
    assert factor == pytest.approx(2.0, rel=1.0e-8)
    assert attempted_shifts[0] == pytest.approx(2.0)
    assert shift != pytest.approx(2.0)
    assert 1.9999 < shift < 2.0001
    assert np.linalg.norm(initial @ mode + factor * geometric @ mode) < 1.0e-8


def test_indefinite_shift_invert_selects_first_factor_with_multiple_candidates() -> None:
    initial = csr_matrix(np.diag([2.0, 3.0, 4.0, 5.0, 7.0]))
    geometric = csr_matrix(np.diag([-1.0, -1.0, 1.0, 2.0, 3.0]))

    factor, mode, bracket = LinearBucklingSolver._critical_factor(
        initial,
        geometric,
        np.arange(5, dtype=int),
        5,
        {"initial_factor": 1.0, "maximum_factor": 10.0},
    )

    assert factor == pytest.approx(2.0, rel=1.0e-6)
    assert bracket["method"] == "generalized_eigs_shift_invert"
    assert abs(float(mode[0])) == pytest.approx(1.0, abs=1.0e-8)
    assert np.linalg.norm(mode[1:]) < 1.0e-8


def test_linear_buckling_rejects_a_rigid_initial_tangent_mode() -> None:
    initial = csr_matrix(np.diag([0.0, 3.0, 4.0, 5.0]))
    geometric = csr_matrix(np.diag([-1.0, -1.0, 1.0, 2.0]))

    with pytest.raises(NumericalConvergenceError, match="initial constrained tangent is not positive definite"):
        LinearBucklingSolver._critical_factor(
            initial,
            geometric,
            np.arange(4, dtype=int),
            4,
            {"initial_factor": 1.0, "maximum_factor": 10.0},
        )


def test_linear_buckling_is_listed_as_a_bounded_method() -> None:
    assert list_methods()["linear_buckling"] == ("eigsh",)
