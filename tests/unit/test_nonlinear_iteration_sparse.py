from __future__ import annotations

import numpy as np
from scipy.sparse import csr_matrix

from solveur.core.errors import NumericalConvergenceError
from solveur.core.nonlinear_contracts import NonlinearFailureReason
from solveur.core.nonlinear_iteration import solve_arc_length_correction
from solveur.core.nonlinear_iteration import solve_full_newton


def test_arc_length_correction_preserves_sparse_augmented_system(monkeypatch) -> None:
    tangent = csr_matrix([[4.0, 0.0], [0.0, 3.0]])

    def fail_toarray(_self: object) -> np.ndarray:
        raise AssertionError("arc-length correction must not densify the global tangent")

    monkeypatch.setattr(csr_matrix, "toarray", fail_toarray)
    correction, delta_factor = solve_arc_length_correction(
        tangent,
        np.array([1.0, 2.0]),
        np.array([0.5, -0.25]),
        np.array([0.1, 0.2]),
        0.3,
        0.02,
        1.0,
    )

    assert correction.shape == (2,)
    assert np.isfinite(delta_factor)
    assert np.all(np.isfinite(correction))


def test_full_newton_failure_contains_convergence_history() -> None:
    class SingularAssembly:
        ndof = 2

        def assemble(self, displacement, *, tangent_required=True):
            return np.zeros(2), csr_matrix((2, 2))

    try:
        solve_full_newton(
            SingularAssembly(),
            np.array([1.0, 0.0]),
            np.array([1]),
            increments=1,
            tolerance=1.0e-8,
            max_iterations=3,
        )
    except NumericalConvergenceError as error:
        assert error.reason is NonlinearFailureReason.SINGULAR_TANGENT
        assert error.diagnostics["solver"] == "full_newton"
        assert error.diagnostics["backend"] == "scipy.sparse.linalg.spsolve"
        assert error.diagnostics["residual_history"] == (1.0,)
        assert error.diagnostics["tolerance"] == 1.0e-8
    else:
        raise AssertionError("singular Full Newton tangent must be reported")


def test_full_newton_success_exports_line_search_diagnostics() -> None:
    class IdentityAssembly:
        ndof = 2

        def assemble(self, displacement, *, tangent_required=True):
            return np.asarray(displacement, dtype=float), csr_matrix(np.eye(2))

    _, diagnostics = solve_full_newton(
        IdentityAssembly(),
        np.array([2.0, 0.0]),
        np.array([1]),
        increments=1,
        tolerance=1.0e-8,
        max_iterations=3,
    )

    step = diagnostics["increments"][0]
    assert step["diagnostics"]["line_search_iterations"] == 0
    assert step["diagnostics"]["solver"] == "full_newton"
    assert step["assembly_seconds"] > 0.0
    assert step["linear_solve_seconds"] > 0.0
    assert step["line_search_seconds"] >= 0.0
