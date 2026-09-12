"""Focused tests for the nonlinear sparse solver adapter and telemetry."""

from __future__ import annotations

import json

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import spsolve

from solveur.core.nonlinear.iteration import solve_full_newton
from solveur.core.nonlinear.linear_solver import NonlinearLinearSolverAdapter
from solveur.core.nonlinear.robustness import NonlinearRobustnessOptions
from solveur.core.nonlinear.telemetry import JsonlNonlinearTelemetry


def test_direct_adapter_matches_scipy_correction() -> None:
    matrix = csr_matrix([[4.0, 1.0], [1.0, 3.0]])
    rhs = np.array([1.0, 2.0])

    correction, diagnostics = NonlinearLinearSolverAdapter().solve(matrix, rhs)

    assert np.allclose(correction, spsolve(matrix, rhs), rtol=1.0e-12, atol=1.0e-14)
    assert diagnostics["linear_method"] == "direct"
    assert diagnostics["linear_relative_residual"] <= 1.0e-10


def test_auto_adapter_selects_minres_without_spd_declaration() -> None:
    options = NonlinearRobustnessOptions(linear_solver="auto", linear_preconditioner="jacobi")
    correction, diagnostics = NonlinearLinearSolverAdapter(options).solve(
        csr_matrix([[4.0, 1.0], [1.0, 3.0]]), np.array([1.0, 2.0])
    )

    assert diagnostics["linear_method"] == "minres"
    assert diagnostics["matrix_symmetric"] is True
    assert diagnostics["fallback_used"] is False
    assert np.allclose(correction, [1.0 / 11.0, 7.0 / 11.0])


def test_auto_adapter_selects_cg_only_with_explicit_spd_declaration() -> None:
    options = NonlinearRobustnessOptions(
        linear_solver="auto", linear_assume_spd=True, linear_preconditioner="jacobi"
    )
    _, diagnostics = NonlinearLinearSolverAdapter(options).solve(
        csr_matrix([[4.0, 1.0], [1.0, 3.0]]), np.array([1.0, 2.0])
    )

    assert diagnostics["linear_method"] == "cg"
    assert diagnostics["assume_spd"] is True


def test_auto_adapter_selects_gmres_for_nonsymmetric_matrix() -> None:
    options = NonlinearRobustnessOptions(linear_solver="auto")
    _, diagnostics = NonlinearLinearSolverAdapter(options).solve(
        csr_matrix([[3.0, 2.0], [0.0, 1.0]]), np.array([1.0, 2.0])
    )

    assert diagnostics["linear_method"] == "gmres"
    assert diagnostics["matrix_symmetric"] is False


class _LinearAssembly:
    ndof = 2

    def assemble(self, displacement: np.ndarray, *, tangent_required: bool = True):
        tangent = csr_matrix([[2.0, 0.0], [0.0, 1.0]])
        return tangent @ displacement, tangent if tangent_required else None


def test_telemetry_is_emitted_after_iterations_and_acceptance(tmp_path) -> None:
    events: list[dict[str, object]] = []
    solve_full_newton(
        _LinearAssembly(),
        np.array([2.0, 0.0]),
        np.array([1]),
        increments=1,
        tolerance=1.0e-12,
        max_iterations=4,
        telemetry_observer=lambda event: events.append(dict(event)),
    )

    assert [event["event"] for event in events] == ["ITERATION", "ITERATION", "STEP_ACCEPTED", "SOLVE_COMPLETED"]
    iteration = events[0]
    for key in (
        "load_step",
        "target_load_factor",
        "residual_norm",
        "matrix_nnz",
        "linear_backend",
        "RSS_bytes",
    ):
        assert key in iteration

    path = tmp_path / "telemetry.jsonl"
    with JsonlNonlinearTelemetry(path) as writer:
        writer(events[0])
    assert json.loads(path.read_text(encoding="utf-8"))["event"] == "ITERATION"


def test_observer_failure_does_not_change_numerical_result() -> None:
    displacement, diagnostics = solve_full_newton(
        _LinearAssembly(),
        np.array([2.0, 0.0]),
        np.array([1]),
        increments=1,
        tolerance=1.0e-12,
        max_iterations=4,
        telemetry_observer=lambda _: (_ for _ in ()).throw(OSError("diagnostic destination unavailable")),
    )

    assert np.allclose(displacement, [1.0, 0.0])
    assert diagnostics["converged"] is True
