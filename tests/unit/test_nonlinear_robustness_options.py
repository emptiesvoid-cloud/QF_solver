from __future__ import annotations

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from solveur.core.nonlinear.iteration import solve_full_newton
from solveur.core.nonlinear.robustness import (
    NonlinearRobustnessOptions,
    solve_scaled_system,
)


def test_robustness_controls_are_opt_in() -> None:
    assert NonlinearRobustnessOptions.from_parameters({}) is None

    options = NonlinearRobustnessOptions.from_parameters(
        {
            "experimental_linear_solver": "splu",
            "experimental_linear_permutation": "natural",
            "experimental_line_search": "armijo",
        }
    )

    assert options is not None
    assert options.linear_solver == "splu"
    assert options.linear_permutation == "NATURAL"
    assert options.line_search == "armijo"


def test_robustness_controls_reject_conflicting_scaling_modes() -> None:
    with pytest.raises(ValueError, match="one experimental linear scaling"):
        NonlinearRobustnessOptions(
            system_scaling="symmetric_diagonal",
            residual_scaling="row_max",
        ).validate()


@pytest.mark.parametrize(
    "options",
    [
        NonlinearRobustnessOptions(),
        NonlinearRobustnessOptions(system_scaling="symmetric_diagonal"),
        NonlinearRobustnessOptions(residual_scaling="row_max"),
        NonlinearRobustnessOptions(linear_solver="splu", linear_permutation="MMD_AT_PLUS_A"),
    ],
)
def test_experimental_linear_system_controls_preserve_solution(
    options: NonlinearRobustnessOptions,
) -> None:
    matrix = csr_matrix(
        [
            [9.0e4, 2.0, 0.0],
            [2.0, 5.0, 0.3],
            [0.0, 0.3, 2.0e-3],
        ]
    )
    rhs = np.array([1.0, -2.0, 0.5])

    solution, diagnostics = solve_scaled_system(matrix, rhs, options)
    expected = np.linalg.solve(matrix.toarray(), rhs)

    np.testing.assert_allclose(solution, expected, rtol=1.0e-11, atol=1.0e-12)
    assert diagnostics["permutation"] == options.linear_permutation
    assert diagnostics["scaling"] in {"none", "symmetric_diagonal", "row_max"}


def test_experimental_splu_is_reported_by_full_newton() -> None:
    class IdentityAssembly:
        ndof = 2

        def assemble(self, displacement: np.ndarray, *, tangent_required: bool = True):
            return np.asarray(displacement, dtype=float), csr_matrix(np.eye(2))

    _, diagnostics = solve_full_newton(
        IdentityAssembly(),
        np.array([2.0, 0.0]),
        np.array([1]),
        increments=1,
        tolerance=1.0e-8,
        max_iterations=3,
        robustness_options=NonlinearRobustnessOptions(
            linear_solver="splu",
            line_search="off",
        ),
    )

    step = diagnostics["increments"][0]
    assert step["diagnostics"]["backend"] == "scipy.sparse.linalg.splu"
    assert step["diagnostics"]["linear_system_diagnostics"][0]["backend"] == (
        "scipy.sparse.linalg.splu"
    )
    assert step["diagnostics"]["robustness_options"]["line_search"] == "off"
