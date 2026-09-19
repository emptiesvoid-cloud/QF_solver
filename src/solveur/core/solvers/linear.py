"""Linear system solution methods from the numerical literature."""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import MatrixRankWarning, LinearOperator, bicgstab, cg, gmres, minres, spilu, splu, spsolve

from solveur.core.errors import NumericalConvergenceError
from solveur.core.solvers.backend import select_backend, solve_with_petsc


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
        self.matrix = matrix.tocsr()
        self.parameters = dict(parameters or {})
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
            initial_residual_norm=float(np.linalg.norm(rhs_array)),
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
        normalized = method.lower()
        if normalized == "auto":
            raise ValueError("LinearSystemSolver.solve requires an effective method; resolve 'auto' through LinearSolverPolicy.")
        backend = select_backend(parameters.get("backend", "auto"), problem_size=matrix.shape[0], parameters=parameters)
        if backend.selected == "petsc":
            solution, iterations, _ = solve_with_petsc(matrix, rhs, normalized, parameters)
            residual, relative = self._validated_residual_metrics(matrix, rhs, solution, normalized, parameters)
            initial = float(np.linalg.norm(np.asarray(rhs, dtype=float)))
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
            initial = float(np.linalg.norm(np.asarray(rhs, dtype=float)))
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
            initial_residual_norm=float(np.linalg.norm(np.asarray(rhs, dtype=complex))),
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
            initial_residual_norm=float(np.linalg.norm(np.asarray(rhs, dtype=float))),
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
            initial_residual_norm=float(np.linalg.norm(np.asarray(rhs, dtype=float))),
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
        return float(np.linalg.norm(matrix @ value - rhs))

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
        if steps == 0:
            return solution, 0
        limit = float(parameters.get("residual_failure_tolerance", 1.0e-7))
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
        residual = float(np.linalg.norm(product - rhs))
        reference = max(float(np.linalg.norm(rhs)), float(np.linalg.norm(product)), 1.0)
        return residual, residual / reference

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
        if not np.all(np.isfinite(solution)):
            kind = "nan" if np.any(np.isnan(solution)) else "inf"
            raise NumericalConvergenceError(
                f"{method} produced a non-finite solution.", diagnostics={"nonfinite": kind}
            )
        product = matrix @ solution
        residual, relative = LinearSystemSolver._raw_residual_metrics(matrix, rhs, solution)
        limit = float(parameters.get("residual_failure_tolerance", 1.0e-7))
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
        return residual, relative


def _reported_tolerance(method: str, parameters: dict[str, Any]) -> float | None:
    if method.lower() in {"direct", "spsolve", "splu", "direct_frequency"}:
        return float(parameters.get("residual_failure_tolerance", 1.0e-7))
    return float(parameters.get("rtol", 1.0e-10))
