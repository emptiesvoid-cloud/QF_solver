"""Linear system solution methods from the numerical literature."""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from math import fsum
from time import perf_counter
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import MatrixRankWarning, LinearOperator, bicgstab, cg, gmres, minres, spilu, splu, spsolve

from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.core.solvers.backend import select_backend, solve_with_petsc


def stable_l2_norm(values: np.ndarray) -> float:
    """Compute a Euclidean norm without squaring unscaled magnitudes."""
    array = np.asarray(values)
    if array.size == 0:
        return 0.0
    if not np.all(np.isfinite(array)):
        return float("inf")

    if np.iscomplexobj(array):
        real = np.asarray(array.real, dtype=float).ravel()
        imag = np.asarray(array.imag, dtype=float).ravel()
        scale = max(
            float(np.max(np.abs(real), initial=0.0)),
            float(np.max(np.abs(imag), initial=0.0)),
        )
        if scale == 0.0:
            return 0.0
        scaled_real = real / scale
        scaled_imag = imag / scale
        sum_squares = float(np.dot(scaled_real, scaled_real) + np.dot(scaled_imag, scaled_imag))
    else:
        flat = np.asarray(array, dtype=float).ravel()
        scale = float(np.max(np.abs(flat), initial=0.0))
        if scale == 0.0:
            return 0.0
        scaled = flat / scale
        sum_squares = float(np.dot(scaled, scaled))

    with np.errstate(over="ignore", invalid="ignore"):
        norm = scale * np.sqrt(sum_squares)
    return float(norm)


def validate_residual_failure_tolerance(parameters: dict[str, Any], key: str = "residual_failure_tolerance") -> float:
    """Return a configured residual limit after requiring a finite positive scalar."""
    raw_value = parameters.get(key, 1.0e-7)
    if isinstance(raw_value, (bool, np.bool_)) or not isinstance(
        raw_value, (int, float, np.integer, np.floating)
    ):
        raise InputValidationError(f"{key} must be a finite positive number.")
    try:
        value = float(raw_value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise InputValidationError(f"{key} must be a finite positive number.") from exc
    if not np.isfinite(value) or value <= 0.0:
        raise InputValidationError(f"{key} must be a finite positive number.")
    return value


def relative_residual_ratio(residual_norm: float, reference_norm: float) -> float:
    """Scale a residual without a unit-dependent floor; define the zero case."""
    if (
        not np.isfinite(residual_norm)
        or not np.isfinite(reference_norm)
        or residual_norm < 0.0
        or reference_norm < 0.0
    ):
        return float("inf")
    if reference_norm == 0.0:
        return 0.0 if residual_norm == 0.0 else float("inf")
    with np.errstate(over="ignore", under="ignore", divide="ignore", invalid="ignore"):
        ratio = float(np.divide(residual_norm, reference_norm))
    if residual_norm > 0.0 and ratio == 0.0:
        return float(np.nextafter(0.0, 1.0))
    return ratio


def _require_exact_integer_input(values: np.ndarray, method: str) -> None:
    """Reject integers whose conversion to the solver's float64 changes their value."""
    array = np.asarray(values)
    if np.issubdtype(array.dtype, np.integer) and any(int(float(value)) != int(value) for value in array.flat):
        raise NumericalConvergenceError(
            f"{method} cannot demonstrate residual convergence: integer input is not exactly representable as float64."
        )


def _sparse_matvec_roundoff_bound(
    matrix: csr_matrix,
    rhs: np.ndarray,
    solution: np.ndarray,
    product: np.ndarray,
) -> np.ndarray:
    """Bound dot-product and final subtraction error row by row.

    The bound uses absolute product sums and a conservative operation-count
    factor. If those sums overflow, convergence cannot be certified.
    """
    eps = np.finfo(float).eps
    smallest = np.nextafter(0.0, 1.0)
    row_bounds = np.zeros(matrix.shape[0], dtype=float)
    matrix = matrix.tocsr()
    vector_values = np.asarray(solution)
    vector_magnitude = np.abs(
        vector_values.astype(float) if np.issubdtype(vector_values.dtype, np.integer) else vector_values
    )
    rhs_values = np.asarray(rhs)
    rhs_magnitude = np.abs(rhs_values.astype(float) if np.issubdtype(rhs_values.dtype, np.integer) else rhs_values)
    product_magnitude = np.abs(product)

    for row in range(matrix.shape[0]):
        start, stop = matrix.indptr[row], matrix.indptr[row + 1]
        columns = matrix.indices[start:stop]
        row_data = matrix.data[start:stop]
        # abs(int64 minimum) overflows in integer arithmetic. Convert first.
        magnitudes = np.abs(row_data.astype(float)) if np.issubdtype(row_data.dtype, np.integer) else np.abs(row_data)
        with np.errstate(over="ignore", under="ignore", invalid="ignore"):
            terms = magnitudes * vector_magnitude[columns]
        if not np.all(np.isfinite(terms)):
            row_bounds[row] = float("inf")
            continue
        try:
            absolute_sum = fsum(float(term) for term in terms)
        except OverflowError:
            row_bounds[row] = float("inf")
            continue
        if not np.isfinite(absolute_sum):
            row_bounds[row] = float("inf")
            continue

        operations = max(stop - start, 1)
        factor = 32.0 * eps * (operations + 1)
        if factor >= 1.0:
            row_bounds[row] = float("inf")
            continue
        nonzero_operands = (magnitudes > 0.0) & (vector_magnitude[columns] > 0.0)
        underflow_terms = int(np.count_nonzero(nonzero_operands & (terms < np.finfo(float).tiny)))
        subtraction_underflow = int(float(rhs_magnitude[row]) > 0.0 or float(product_magnitude[row]) > 0.0)
        with np.errstate(over="ignore", under="ignore", invalid="ignore"):
            bound = (
                factor * absolute_sum
                + 32.0 * eps * (float(rhs_magnitude[row]) + float(product_magnitude[row]))
                + 32.0 * smallest * (underflow_terms + subtraction_underflow)
            )
        if np.isfinite(bound) and bound > 0.0:
            bound = float(np.nextafter(bound * (1.0 + 32.0 * eps), float("inf")))
        row_bounds[row] = bound
    return row_bounds


@dataclass(frozen=True)
class LinearSolveInfo:
    """Metadata for one linear solve."""

    method: str
    iterations: int
    residual_norm: float
    converged: bool
    preconditioner: str = "none"
    residual_history: list[float] = field(default_factory=list)
    backend: str = "scipy"
    initial_residual_norm: float = 0.0
    relative_residual_norm: float = 0.0
    tolerance: float | None = None
    termination_reason: str = "converged"
    direct_refinement_iterations: int = 0

    def to_dict(self) -> dict[str, float | int | str | bool | list[float] | None]:
        return {
            "method": self.method,
            "iterations": self.iterations,
            "residual_norm": self.residual_norm,
            "converged": self.converged,
            "preconditioner": self.preconditioner,
            "residual_history": self.residual_history,
            "backend": self.backend,
            "initial_residual_norm": self.initial_residual_norm,
            "relative_residual_norm": self.relative_residual_norm,
            "tolerance": self.tolerance,
            "termination_reason": self.termination_reason,
            "direct_refinement_iterations": self.direct_refinement_iterations,
        }


class ReusableSparseFactorization:
    """Factorize one sparse matrix once and solve multiple right-hand sides."""

    def __init__(self, matrix: csr_matrix, parameters: dict[str, Any] | None = None) -> None:
        _require_exact_integer_input(matrix.data, "splu_reuse")
        self.matrix = matrix.tocsr()
        self.parameters = dict(parameters or {})
        validate_residual_failure_tolerance(self.parameters)
        self.factorization_count = 1
        self.solve_count = 0
        self.factorization_seconds = 0.0
        self.solve_seconds_total = 0.0
        self.last_solve_seconds = 0.0
        started = perf_counter()
        try:
            self._factor = splu(self.matrix.tocsc())
        except (RuntimeError, ValueError) as exc:
            raise NumericalConvergenceError(f"Sparse LU factorization failed: {exc}") from exc
        self.factorization_seconds = perf_counter() - started

    def solve(self, rhs: np.ndarray) -> tuple[np.ndarray, LinearSolveInfo]:
        """Solve one right-hand side and validate the normalized residual."""
        _require_exact_integer_input(rhs, "splu_reuse")
        started = perf_counter()
        try:
            solution = np.asarray(self._factor.solve(np.asarray(rhs, dtype=float)), dtype=float)
        except (FloatingPointError, RuntimeError, ValueError) as exc:
            raise NumericalConvergenceError(f"Reusable sparse solve failed: {exc}") from exc
        elapsed = perf_counter() - started
        self.solve_count += 1
        self.last_solve_seconds = elapsed
        self.solve_seconds_total += elapsed
        rhs_array = np.asarray(rhs, dtype=float)
        residual, relative = LinearSystemSolver._validated_residual_metrics(
            self.matrix,
            rhs_array,
            solution,
            "splu_reuse",
            self.parameters,
        )
        return solution, LinearSolveInfo(
            "splu_reuse",
            1,
            residual,
            True,
            residual_history=[residual],
            initial_residual_norm=stable_l2_norm(rhs_array),
            relative_residual_norm=relative,
            tolerance=_reported_tolerance("splu_reuse", self.parameters),
        )


class LinearSystemSolver:
    """Solve sparse linear systems with selectable algorithms."""

    @staticmethod
    def factorize(
        matrix: csr_matrix,
        *,
        parameters: dict[str, Any] | None = None,
    ) -> ReusableSparseFactorization:
        """Return a reusable direct sparse factorization."""
        return ReusableSparseFactorization(matrix, parameters)

    def solve(
        self,
        matrix: csr_matrix,
        rhs: np.ndarray,
        *,
        method: str,
        parameters: dict[str, Any] | None = None,
    ) -> tuple[np.ndarray, LinearSolveInfo]:
        parameters = parameters or {}
        _require_exact_integer_input(matrix.data, method)
        _require_exact_integer_input(rhs, method)
        validate_residual_failure_tolerance(parameters)
        normalized = method.lower()
        if normalized == "auto":
            raise ValueError("LinearSystemSolver.solve requires an effective method; resolve 'auto' through LinearSolverPolicy.")
        backend = select_backend(parameters.get("backend", "auto"), problem_size=matrix.shape[0], parameters=parameters)
        if backend.selected == "petsc":
            solution, iterations, _ = solve_with_petsc(matrix, rhs, normalized, parameters)
            residual, relative = self._validated_residual_metrics(matrix, rhs, solution, normalized, parameters)
            initial = stable_l2_norm(np.asarray(rhs, dtype=float))
            return solution, LinearSolveInfo(
                normalized,
                iterations,
                residual,
                True,
                str(parameters.get("preconditioner", "none")),
                residual_history=[residual],
                backend="petsc",
                initial_residual_norm=initial,
                relative_residual_norm=relative,
                tolerance=_reported_tolerance(normalized, parameters),
            )
        if normalized in {"direct", "spsolve"}:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("error", MatrixRankWarning)
                    solution = np.asarray(spsolve(matrix, rhs), dtype=float)
            except MatrixRankWarning as exc:
                raise NumericalConvergenceError("Direct sparse solve failed because the matrix is singular.") from exc
            except (FloatingPointError, RuntimeError, ValueError) as exc:
                raise NumericalConvergenceError(f"Direct sparse solve failed: {exc}") from exc
            solution, refinement_iterations = self._refine_direct_solution(matrix, rhs, solution, parameters)
            try:
                residual, relative = self._validated_residual_metrics(matrix, rhs, solution, normalized, parameters)
            except NumericalConvergenceError as exc:
                exc.diagnostics.update(
                    {
                        "direct_refinement_enabled": refinement_iterations > 0,
                        "direct_refinement_iterations": refinement_iterations,
                    }
                )
                raise
            initial = stable_l2_norm(np.asarray(rhs, dtype=float))
            return solution, LinearSolveInfo(
                normalized,
                1,
                residual,
                True,
                residual_history=[residual],
                initial_residual_norm=initial,
                relative_residual_norm=relative,
                tolerance=_reported_tolerance(normalized, parameters),
                direct_refinement_iterations=refinement_iterations,
            )
        if normalized in {"cg", "conjugate_gradient"}:
            return self._iterative(cg, matrix, rhs, "cg", parameters)
        if normalized == "gmres":
            return self._iterative(gmres, matrix, rhs, "gmres", parameters)
        if normalized == "bicgstab":
            return self._iterative(bicgstab, matrix, rhs, "bicgstab", parameters)
        if normalized == "minres":
            return self._iterative_minres(matrix, rhs, parameters)
        raise ValueError(f"Unsupported linear method {method!r}.")

    def solve_complex(
        self,
        matrix: csr_matrix,
        rhs: np.ndarray,
        *,
        parameters: dict[str, Any] | None = None,
    ) -> tuple[np.ndarray, LinearSolveInfo]:
        """Solve one complex sparse system used by harmonic response."""

        params = parameters or {}
        _require_exact_integer_input(matrix.data, "direct_frequency")
        _require_exact_integer_input(rhs, "direct_frequency")
        validate_residual_failure_tolerance(params)
        backend = select_backend("scipy", problem_size=matrix.shape[0], parameters=params)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", MatrixRankWarning)
                solution = np.asarray(spsolve(matrix.tocsc(), np.asarray(rhs, dtype=complex)), dtype=complex)
        except MatrixRankWarning as exc:
            raise NumericalConvergenceError("Complex sparse solve failed because the matrix is singular.") from exc
        except (FloatingPointError, RuntimeError, ValueError) as exc:
            raise NumericalConvergenceError(f"Complex sparse solve failed: {exc}") from exc
        residual, relative = self._validated_residual_metrics(matrix, rhs, solution, "direct_frequency", params)
        return solution, LinearSolveInfo(
            "direct_frequency",
            1,
            residual,
            True,
            backend=backend.selected,
            initial_residual_norm=stable_l2_norm(np.asarray(rhs, dtype=complex)),
            relative_residual_norm=relative,
            tolerance=_reported_tolerance("direct_frequency", params),
        )

    @staticmethod
    def _iterative(
        solver: object,
        matrix: csr_matrix,
        rhs: np.ndarray,
        method: str,
        parameters: dict[str, Any],
    ) -> tuple[np.ndarray, LinearSolveInfo]:
        iterations = 0
        residual_history: list[float] = []
        preconditioner = LinearSystemSolver._preconditioner(matrix, parameters)

        def callback(state: object) -> None:
            nonlocal iterations
            iterations += 1
            residual_history.append(LinearSystemSolver._callback_residual(matrix, rhs, state))

        kwargs = {
            "rtol": float(parameters.get("rtol", 1.0e-10)),
            "atol": float(parameters.get("atol", 0.0)),
            "maxiter": parameters.get("maxiter"),
            "M": preconditioner,
            "callback": callback,
        }
        if method == "gmres":
            kwargs["callback_type"] = "legacy"
            if parameters.get("restart") is not None:
                kwargs["restart"] = int(parameters["restart"])
        solution, info = solver(matrix, rhs, **kwargs)
        if info != 0:
            reason = "iteration limit reached" if info > 0 else "illegal input or numerical breakdown"
            raise NumericalConvergenceError(
                f"{method} did not converge ({reason}, info={info}).",
                diagnostics={"iterations": iterations, "solver_info": int(info)},
            )
        residual, relative = LinearSystemSolver._validated_residual_metrics(matrix, rhs, solution, method, parameters)
        LinearSystemSolver._append_final_residual(residual_history, residual)
        return solution, LinearSolveInfo(
            method,
            iterations,
            residual,
            True,
            str(parameters.get("preconditioner", "none")),
            residual_history=residual_history,
            initial_residual_norm=stable_l2_norm(np.asarray(rhs, dtype=float)),
            relative_residual_norm=relative,
            tolerance=_reported_tolerance(method, parameters),
        )

    @staticmethod
    def _iterative_minres(
        matrix: csr_matrix,
        rhs: np.ndarray,
        parameters: dict[str, Any],
    ) -> tuple[np.ndarray, LinearSolveInfo]:
        iterations = 0
        residual_history: list[float] = []
        preconditioner = LinearSystemSolver._preconditioner(matrix, parameters)

        def callback(state: object) -> None:
            nonlocal iterations
            iterations += 1
            residual_history.append(LinearSystemSolver._callback_residual(matrix, rhs, state))

        solution, info = minres(
            matrix,
            rhs,
            rtol=float(parameters.get("rtol", 1.0e-10)),
            maxiter=parameters.get("maxiter"),
            M=preconditioner,
            callback=callback,
        )
        if info != 0:
            reason = "iteration limit reached" if info > 0 else "illegal input or numerical breakdown"
            raise NumericalConvergenceError(
                f"minres did not converge ({reason}, info={info}).",
                diagnostics={"iterations": iterations, "solver_info": int(info)},
            )
        residual, relative = LinearSystemSolver._validated_residual_metrics(matrix, rhs, solution, "minres", parameters)
        LinearSystemSolver._append_final_residual(residual_history, residual)
        return solution, LinearSolveInfo(
            "minres",
            iterations,
            residual,
            True,
            str(parameters.get("preconditioner", "none")),
            residual_history=residual_history,
            initial_residual_norm=stable_l2_norm(np.asarray(rhs, dtype=float)),
            relative_residual_norm=relative,
            tolerance=_reported_tolerance("minres", parameters),
        )

    @staticmethod
    def _preconditioner(matrix: csr_matrix, parameters: dict[str, Any]) -> LinearOperator | None:
        supplied = parameters.get("_preconditioner_operator")
        if supplied is not None:
            if not isinstance(supplied, LinearOperator):
                raise ValueError("_preconditioner_operator must be a scipy LinearOperator.")
            return supplied
        name = str(parameters.get("preconditioner", "none")).lower()
        if name in {"none", ""}:
            return None
        if name == "ilu":
            factor = spilu(
                matrix.tocsc(),
                drop_tol=float(parameters.get("ilu_drop_tol", 1.0e-4)),
                fill_factor=float(parameters.get("ilu_fill_factor", 10.0)),
            )

            def matvec_ilu(vector: np.ndarray) -> np.ndarray:
                return factor.solve(vector)

            return LinearOperator(matrix.shape, matvec=matvec_ilu, dtype=float)
        if name != "jacobi":
            raise ValueError(f"Unsupported preconditioner {name!r}.")
        diagonal = matrix.diagonal()
        inverse = np.zeros_like(diagonal, dtype=float)
        mask = np.abs(diagonal) > 1.0e-30
        inverse[mask] = 1.0 / diagonal[mask]

        def matvec(vector: np.ndarray) -> np.ndarray:
            return inverse * vector

        return LinearOperator(matrix.shape, matvec=matvec, dtype=float)

    @staticmethod
    def _callback_residual(matrix: csr_matrix, rhs: np.ndarray, state: object) -> float:
        value = np.asarray(state)
        if value.ndim == 0:
            return float(abs(value.item()))
        return stable_l2_norm(matrix @ value - rhs)

    @staticmethod
    def _append_final_residual(history: list[float], residual: float) -> None:
        if not history or not np.isclose(history[-1], residual, rtol=1.0e-12, atol=1.0e-30):
            history.append(float(residual))

    @staticmethod
    def _refine_direct_solution(
        matrix: csr_matrix,
        rhs: np.ndarray,
        solution: np.ndarray,
        parameters: dict[str, Any],
    ) -> tuple[np.ndarray, int]:
        """Optionally improve a direct solution without changing its gate.

        This is an opt-in R&D aid for ill-conditioned sparse tangents.  It
        never relaxes the residual threshold: the final candidate still goes
        through ``_validated_residual_metrics`` unchanged.  With the default
        of zero iterations the legacy direct path is bit-for-bit unchanged.
        """
        raw_steps = parameters.get("experimental_direct_refinement_steps", 0)
        if isinstance(raw_steps, bool) or not isinstance(raw_steps, (int, np.integer)):
            raise ValueError("experimental_direct_refinement_steps must be a non-negative integer.")
        steps = int(raw_steps)
        if steps < 0:
            raise ValueError("experimental_direct_refinement_steps must be non-negative.")
        limit = validate_residual_failure_tolerance(parameters)
        if steps == 0:
            return solution, 0
        current = np.asarray(solution, dtype=float).copy()
        _, relative = LinearSystemSolver._raw_residual_metrics(matrix, rhs, current)
        if relative <= limit:
            return current, 0
        performed = 0
        for _ in range(steps):
            correction_rhs = np.asarray(rhs, dtype=float) - matrix @ current
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("error", MatrixRankWarning)
                    correction = np.asarray(spsolve(matrix, correction_rhs), dtype=float)
            except MatrixRankWarning as exc:
                raise NumericalConvergenceError(
                    "Direct iterative refinement failed because the matrix is singular.",
                    diagnostics={"direct_refinement_iterations": performed},
                ) from exc
            except (FloatingPointError, RuntimeError, ValueError) as exc:
                raise NumericalConvergenceError(
                    f"Direct iterative refinement failed: {exc}",
                    diagnostics={"direct_refinement_iterations": performed},
                ) from exc
            if not np.all(np.isfinite(correction)):
                raise NumericalConvergenceError(
                    "Direct iterative refinement produced a non-finite correction.",
                    diagnostics={"direct_refinement_iterations": performed + 1},
                )
            current += correction
            performed += 1
            _, relative = LinearSystemSolver._raw_residual_metrics(matrix, rhs, current)
            if relative <= limit:
                break
        return current, performed

    @staticmethod
    def _raw_residual_metrics(
        matrix: csr_matrix,
        rhs: np.ndarray,
        solution: np.ndarray,
    ) -> tuple[float, float]:
        product = matrix @ solution
        residual = stable_l2_norm(product - rhs)
        reference = max(stable_l2_norm(rhs), stable_l2_norm(product))
        return residual, relative_residual_ratio(residual, reference)

    @staticmethod
    def _validated_residual(
        matrix: csr_matrix,
        rhs: np.ndarray,
        solution: np.ndarray,
        method: str,
        parameters: dict[str, Any],
    ) -> float:
        if not np.all(np.isfinite(solution)):
            raise NumericalConvergenceError(f"{method} produced a non-finite solution.")
        residual, _ = LinearSystemSolver._validated_residual_metrics(matrix, rhs, solution, method, parameters)
        return residual

    @staticmethod
    def _validated_residual_metrics(
        matrix: csr_matrix,
        rhs: np.ndarray,
        solution: np.ndarray,
        method: str,
        parameters: dict[str, Any],
    ) -> tuple[float, float]:
        _require_exact_integer_input(matrix.data, method)
        _require_exact_integer_input(rhs, method)
        _require_exact_integer_input(solution, method)
        if np.issubdtype(np.asarray(solution).dtype, np.integer):
            solution = np.asarray(solution, dtype=float)
        if not np.all(np.isfinite(solution)):
            kind = "nan" if np.any(np.isnan(solution)) else "inf"
            raise NumericalConvergenceError(
                f"{method} produced a non-finite solution.", diagnostics={"nonfinite": kind}
            )
        product = matrix @ solution
        residual, relative = LinearSystemSolver._raw_residual_metrics(matrix, rhs, solution)
        limit = validate_residual_failure_tolerance(parameters)
        if not np.isfinite(residual) or not np.isfinite(relative):
            raise NumericalConvergenceError(f"{method} produced a non-finite residual.")
        if relative > limit:
            rhs_inf = float(np.max(np.abs(rhs), initial=0.0))
            solution_inf = float(np.max(np.abs(solution), initial=0.0))
            product_inf = float(np.max(np.abs(product), initial=0.0))
            matrix_inf = float(np.max(np.asarray(np.abs(matrix).sum(axis=1)).ravel(), initial=0.0))
            backward_denominator = matrix_inf * solution_inf + rhs_inf
            backward_error = (
                float(np.max(np.abs(product - rhs), initial=0.0)) / backward_denominator
                if backward_denominator > 0.0
                else float("inf")
            )
            raise NumericalConvergenceError(
                f"{method} residual is abnormal: relative={relative:.6e}, allowed={limit:.6e}.",
                diagnostics={
                    "matrix_shape": list(matrix.shape),
                    "matrix_nnz": int(matrix.nnz),
                    "matrix_inf_norm": matrix_inf,
                    "rhs_inf_norm": rhs_inf,
                    "solution_inf_norm": solution_inf,
                    "product_inf_norm": product_inf,
                    "residual_norm": residual,
                    "relative_residual": relative,
                    "residual_failure_tolerance": limit,
                    "backward_error_eta_inf": backward_error,
                },
            )
        roundoff_vector = _sparse_matvec_roundoff_bound(matrix, rhs, solution, product)
        roundoff_norm = stable_l2_norm(roundoff_vector)
        rhs_norm = stable_l2_norm(rhs)
        product_norm = stable_l2_norm(product)
        norm_factor = 32.0 * np.finfo(float).eps * max(rhs.size, product.size, 1)
        with np.errstate(over="ignore", under="ignore", invalid="ignore"):
            roundoff_norm_upper = roundoff_norm * (1.0 + norm_factor)
            residual_upper_bound = (residual + roundoff_norm_upper) * (1.0 + norm_factor)
            reference_lower_bound = max(
                rhs_norm * (1.0 - norm_factor),
                max(product_norm - roundoff_norm_upper, 0.0) * (1.0 - norm_factor),
            )
            relative_upper_bound = relative_residual_ratio(residual_upper_bound, reference_lower_bound)
        if norm_factor >= 1.0 or not np.isfinite(relative_upper_bound) or relative_upper_bound > limit:
            raise NumericalConvergenceError(
                f"{method} cannot demonstrate residual convergence within floating-point roundoff "
                f"(relative upper bound={relative_upper_bound:.6e}, allowed={limit:.6e}).",
                diagnostics={
                    "residual_norm": residual,
                    "relative_residual": relative,
                    "matvec_roundoff_bound": roundoff_norm,
                    "norm_relative_roundoff_factor": norm_factor,
                    "relative_residual_upper_bound": relative_upper_bound,
                    "residual_failure_tolerance": limit,
                },
            )
        return residual, relative


def _reported_tolerance(method: str, parameters: dict[str, Any]) -> float | None:
    if method.lower() in {"direct", "spsolve", "splu", "direct_frequency"}:
        return float(parameters.get("residual_failure_tolerance", 1.0e-7))
    return float(parameters.get("rtol", 1.0e-10))
