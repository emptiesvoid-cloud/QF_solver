from __future__ import annotations

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from solveur.core.analyses.dynamic import NewmarkDynamicSolver
from solveur.core.analyses.harmonic import HarmonicResponseSolver
from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.core.solvers.linear import (
    LinearSystemSolver,
    _sparse_matvec_roundoff_bound,
    relative_residual_ratio,
    stable_l2_norm,
    validate_residual_failure_tolerance,
)
from solveur.core.solvers.static import LinearStaticSolver


def _model(analysis_type: str, tolerance_name: str, tolerance: object) -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.3, "density": 1.0}},
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
        loads=[{"node": 1, "dof": "UX", "value": 1.0}],
        analysis={
            "type": analysis_type,
            "parameters": {tolerance_name: tolerance, "dt": 0.01, "steps": 1, "frequencies_hz": [1.0]},
        },
    )


@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), float("-inf"), 0.0, -1.0, True, np.bool_(True), "bad", None, 1.0 + 0.0j],
)
def test_residual_failure_tolerances_must_be_finite_positive_scalars(value: object) -> None:
    with pytest.raises(InputValidationError, match="finite positive number"):
        validate_residual_failure_tolerance({"residual_failure_tolerance": value})


@pytest.mark.parametrize("value", ["1e-7", "0.000001"])
def test_residual_failure_tolerance_rejects_numeric_strings(value: str) -> None:
    with pytest.raises(InputValidationError, match="finite positive number"):
        validate_residual_failure_tolerance({"residual_failure_tolerance": value})


def test_residual_failure_tolerance_accepts_finite_python_and_numpy_numbers() -> None:
    assert validate_residual_failure_tolerance({"residual_failure_tolerance": 1}) == 1.0
    assert validate_residual_failure_tolerance({"residual_failure_tolerance": np.float32(1.0e-5)}) == pytest.approx(1.0e-5)


def test_default_residual_failure_tolerance_and_standard_cg_are_unchanged() -> None:
    assert validate_residual_failure_tolerance({}) == 1.0e-7
    solution, info = LinearSystemSolver().solve(
        csr_matrix([[2.0]]), np.asarray([4.0]), method="cg", parameters={"backend": "scipy"}
    )
    assert solution == pytest.approx(np.asarray([2.0]))
    assert info.converged
    assert info.relative_residual_norm <= 1.0e-7


def test_zero_rhs_and_zero_solution_remain_converged() -> None:
    solution, info = LinearSystemSolver().solve(
        csr_matrix([[1.0]]), np.asarray([0.0]), method="cg", parameters={"backend": "scipy"}
    )

    assert solution == pytest.approx(np.asarray([0.0]))
    assert info.converged
    assert info.residual_norm == 0.0
    assert info.relative_residual_norm == 0.0


def test_roundoff_guard_accepts_well_conditioned_direct_system() -> None:
    solution, info = LinearSystemSolver().solve(
        csr_matrix([[4.0, 1.0], [1.0, 3.0]]),
        np.asarray([6.0, 7.0]),
        method="direct",
        parameters={"backend": "scipy"},
    )

    assert solution == pytest.approx(np.asarray([1.0, 2.0]))
    assert info.converged


def test_cg_rejects_underflowed_residual_instead_of_accepting_bad_solution() -> None:
    matrix = csr_matrix([[1.0e-200]])
    rhs = np.asarray([1.0e-200])

    with pytest.raises(NumericalConvergenceError, match=r"relative=1\.000000e\+00"):
        LinearSystemSolver().solve(matrix, rhs, method="cg", parameters={"backend": "scipy"})


def test_residual_norms_do_not_underflow_or_overflow() -> None:
    tiny_matrix = csr_matrix([[1.0]])
    tiny_rhs = np.asarray([1.0e-200])
    zero_solution = np.asarray([0.0])
    residual, relative = LinearSystemSolver._raw_residual_metrics(tiny_matrix, tiny_rhs, zero_solution)
    assert residual == pytest.approx(1.0e-200)
    assert relative == pytest.approx(1.0)

    large_rhs = np.full(200, 1.0e153)
    inaccurate_solution = large_rhs + 1.0e147
    large_matrix = csr_matrix(np.eye(200))
    residual, relative = LinearSystemSolver._raw_residual_metrics(large_matrix, large_rhs, inaccurate_solution)
    assert np.isfinite(residual)
    assert relative == pytest.approx(1.0e-6, rel=2.0e-3)
    with pytest.raises(NumericalConvergenceError, match=r"relative="):
        LinearSystemSolver._validated_residual_metrics(
            large_matrix, large_rhs, inaccurate_solution, "large-counterexample", {}
        )


def test_unrepresentable_norm_fails_the_residual_gate_conservatively() -> None:
    rhs = np.full(2, 1.7e308)
    matrix = csr_matrix(np.eye(2))

    assert np.isinf(stable_l2_norm(rhs))
    with pytest.raises(NumericalConvergenceError, match="non-finite residual"):
        LinearSystemSolver._validated_residual_metrics(matrix, rhs, np.zeros(2), "overflow-counterexample", {})


def test_stable_l2_norm_handles_complex_harmonic_vectors() -> None:
    tiny = np.asarray([1.0e-200 + 1.0e-200j])
    large = np.full(200, 1.0e153 + 1.0e153j)

    assert stable_l2_norm(tiny) == pytest.approx(np.sqrt(2.0) * 1.0e-200)
    assert stable_l2_norm(large) == pytest.approx(np.sqrt(400.0) * 1.0e153)
    assert np.isfinite(stable_l2_norm(large))


def test_relative_linear_residual_is_not_hidden_by_unit_floor() -> None:
    matrix = csr_matrix([[1.0]])
    rhs = np.asarray([1.0e-12])
    solution = np.asarray([0.0])

    residual, relative = LinearSystemSolver._raw_residual_metrics(matrix, rhs, solution)

    assert residual == pytest.approx(1.0e-12)
    assert relative == pytest.approx(1.0)
    with pytest.raises(NumericalConvergenceError, match=r"relative=1.000000e\+00"):
        LinearSystemSolver._validated_residual_metrics(matrix, rhs, solution, "test", {})


def test_relative_residual_defines_exact_zero_reference() -> None:
    assert relative_residual_ratio(0.0, 0.0) == 0.0
    assert relative_residual_ratio(1.0, 0.0) == float("inf")


def test_direct_solver_still_rejects_singular_matrix() -> None:
    with pytest.raises(NumericalConvergenceError, match="singular"):
        LinearSystemSolver().solve(
            csr_matrix([[0.0]]), np.asarray([0.0]), method="direct", parameters={"backend": "scipy"}
        )


def test_direct_solver_rejects_residual_hidden_by_dot_product_cancellation() -> None:
    matrix = csr_matrix([[1.0e16, 1.0, -1.0e16], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    rhs = np.asarray([0.0, 1.0, 1.0])

    with pytest.raises(NumericalConvergenceError, match="cannot demonstrate residual convergence"):
        LinearSystemSolver().solve(matrix, rhs, method="direct", parameters={"backend": "scipy"})


def test_direct_solver_rejects_int64_minimum_cancellation() -> None:
    matrix = csr_matrix(np.asarray([[-(2**63), 2**63 - 1], [0, 1]], dtype=np.int64))
    rhs = np.asarray([0.0, 1.0])

    with pytest.raises(NumericalConvergenceError, match="cannot demonstrate residual convergence"):
        LinearSystemSolver().solve(matrix, rhs, method="direct", parameters={"backend": "scipy"})


def test_roundoff_bound_handles_exactly_representable_int64_minimum() -> None:
    matrix = csr_matrix(np.asarray([[-(2**63), 2**63 - 1024]], dtype=np.int64))
    solution = np.ones(2)
    rhs = np.zeros(1)
    product = matrix @ solution

    bound = _sparse_matvec_roundoff_bound(matrix, rhs, solution, product)

    assert np.isfinite(bound[0])
    assert bound[0] > 1.0e5


def test_direct_solver_rejects_unrepresentable_integer_rhs() -> None:
    matrix = csr_matrix([[1.0]])
    rhs = np.asarray([2**63 - 1], dtype=np.int64)

    with pytest.raises(NumericalConvergenceError, match="integer input is not exactly representable"):
        LinearSystemSolver().solve(matrix, rhs, method="direct", parameters={"backend": "scipy"})


def test_exact_integer_inputs_remain_supported() -> None:
    matrix = csr_matrix(np.asarray([[2, 0], [0, 4]], dtype=np.int64))
    solution, info = LinearSystemSolver().solve(
        matrix, np.asarray([2, 8], dtype=np.int64), method="direct", parameters={"backend": "scipy"}
    )
    assert solution == pytest.approx([1.0, 2.0])
    assert info.converged


def test_reused_factorization_rejects_unrepresentable_integer_rhs() -> None:
    factor = LinearSystemSolver.factorize(csr_matrix([[1.0]]))
    with pytest.raises(NumericalConvergenceError, match="integer input is not exactly representable"):
        factor.solve(np.asarray([2**63 - 1], dtype=np.int64))


def test_factorization_rejects_unrepresentable_integer_matrix() -> None:
    matrix = csr_matrix(np.asarray([[2**63 - 1]], dtype=np.int64))
    with pytest.raises(NumericalConvergenceError, match="integer input is not exactly representable"):
        LinearSystemSolver.factorize(matrix)


def test_complex_solver_rejects_unrepresentable_unsigned_rhs() -> None:
    matrix = csr_matrix([[1.0 + 0.0j]])
    rhs = np.asarray([2**64 - 1], dtype=np.uint64)
    with pytest.raises(NumericalConvergenceError, match="integer input is not exactly representable"):
        LinearSystemSolver().solve_complex(matrix, rhs)


@pytest.mark.parametrize(
    ("analysis_type", "tolerance_name", "solver_type"),
    [
        ("linear_static", "residual_failure_tolerance", LinearStaticSolver),
        ("harmonic_response", "harmonic_residual_failure_tolerance", HarmonicResponseSolver),
        ("transient_dynamic", "dynamic_residual_failure_tolerance", NewmarkDynamicSolver),
    ],
)
def test_analysis_routes_reject_numeric_string_residual_limits_before_mesh_work(
    analysis_type: str,
    tolerance_name: str,
    solver_type: type[object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = _model(analysis_type, tolerance_name, "1e-7")
    solver = solver_type()

    def fail_if_mesh_validation_runs(*_args: object, **_kwargs: object) -> None:
        pytest.fail("Residual input validation must happen before mesh validation.")

    monkeypatch.setattr(solver.validator, "validate", fail_if_mesh_validation_runs)
    with pytest.raises(InputValidationError, match=tolerance_name):
        solver.solve(model)


@pytest.mark.parametrize(
    ("analysis_type", "tolerance_name", "solver_type"),
    [
        ("linear_static", "residual_failure_tolerance", LinearStaticSolver),
        ("harmonic_response", "harmonic_residual_failure_tolerance", HarmonicResponseSolver),
        ("transient_dynamic", "dynamic_residual_failure_tolerance", NewmarkDynamicSolver),
    ],
)
def test_analysis_routes_reject_nonfinite_residual_limits_before_mesh_work(
    analysis_type: str,
    tolerance_name: str,
    solver_type: type[object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = _model(analysis_type, tolerance_name, float("nan"))
    solver = solver_type()

    def fail_if_mesh_validation_runs(*_args: object, **_kwargs: object) -> None:
        pytest.fail("Residual input validation must happen before mesh validation.")

    monkeypatch.setattr(solver.validator, "validate", fail_if_mesh_validation_runs)
    with pytest.raises(InputValidationError, match=tolerance_name):
        solver.solve(model)
