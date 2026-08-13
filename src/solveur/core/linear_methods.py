"""Linear system solution methods from the numerical literature."""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import MatrixRankWarning, LinearOperator, bicgstab, cg, gmres, minres, spilu, splu, spsolve

from solveur.core.errors import NumericalConvergenceError


@dataclass(frozen=True)
class LinearSolveInfo:
    """Metadata for one linear solve."""

    method: str
    iterations: int
    residual_norm: float
    converged: bool
    preconditioner: str = "none"
    residual_history: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, float | int | str | bool | list[float]]:
        return {
            "method": self.method,
            "iterations": self.iterations,
            "residual_norm": self.residual_norm,
            "converged": self.converged,
            "preconditioner": self.preconditioner,
            "residual_history": self.residual_history,
        }


class ReusableSparseFactorization:
    """Factorize one sparse matrix once and solve multiple right-hand sides."""

    def __init__(self, matrix: csr_matrix, parameters: dict[str, Any] | None = None) -> None:
        self.matrix = matrix.tocsr()
        self.parameters = dict(parameters or {})
        self.factorization_count = 1
        self.solve_count = 0
        try:
            self._factor = splu(self.matrix.tocsc())
        except (RuntimeError, ValueError) as exc:
            raise NumericalConvergenceError(f"Sparse LU factorization failed: {exc}") from exc

    def solve(self, rhs: np.ndarray) -> tuple[np.ndarray, LinearSolveInfo]:
        """Solve one right-hand side and validate the normalized residual."""
        try:
            solution = np.asarray(self._factor.solve(np.asarray(rhs, dtype=float)), dtype=float)
        except (FloatingPointError, RuntimeError, ValueError) as exc:
            raise NumericalConvergenceError(f"Reusable sparse solve failed: {exc}") from exc
        self.solve_count += 1
        residual = LinearSystemSolver._validated_residual(
            self.matrix,
            np.asarray(rhs, dtype=float),
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
        if normalized in {"direct", "spsolve"}:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("error", MatrixRankWarning)
                    solution = np.asarray(spsolve(matrix, rhs), dtype=float)
            except MatrixRankWarning as exc:
                raise NumericalConvergenceError("Direct sparse solve failed because the matrix is singular.") from exc
            except (FloatingPointError, RuntimeError, ValueError) as exc:
                raise NumericalConvergenceError(f"Direct sparse solve failed: {exc}") from exc
            residual = self._validated_residual(matrix, rhs, solution, normalized, parameters)
            return solution, LinearSolveInfo(normalized, 1, residual, True, residual_history=[residual])
        if normalized in {"cg", "conjugate_gradient"}:
            return self._iterative(cg, matrix, rhs, "cg", parameters)
        if normalized == "gmres":
            return self._iterative(gmres, matrix, rhs, "gmres", parameters)
        if normalized == "bicgstab":
            return self._iterative(bicgstab, matrix, rhs, "bicgstab", parameters)
        if normalized == "minres":
            return self._iterative_minres(matrix, rhs, parameters)
        raise ValueError(f"Unsupported linear method {method!r}.")

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
        solution, info = solver(matrix, rhs, **kwargs)
        if info != 0:
            reason = "iteration limit reached" if info > 0 else "illegal input or numerical breakdown"
            raise NumericalConvergenceError(f"{method} did not converge ({reason}, info={info}).")
        residual = LinearSystemSolver._validated_residual(matrix, rhs, solution, method, parameters)
        LinearSystemSolver._append_final_residual(residual_history, residual)
        return solution, LinearSolveInfo(
            method,
            iterations,
            residual,
            True,
            str(parameters.get("preconditioner", "none")),
            residual_history=residual_history,
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
            raise NumericalConvergenceError(f"minres did not converge ({reason}, info={info}).")
        residual = LinearSystemSolver._validated_residual(matrix, rhs, solution, "minres", parameters)
        LinearSystemSolver._append_final_residual(residual_history, residual)
        return solution, LinearSolveInfo(
            "minres",
            iterations,
            residual,
            True,
            str(parameters.get("preconditioner", "none")),
            residual_history=residual_history,
        )

    @staticmethod
    def _preconditioner(matrix: csr_matrix, parameters: dict[str, Any]) -> LinearOperator | None:
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
    def _validated_residual(
        matrix: csr_matrix,
        rhs: np.ndarray,
        solution: np.ndarray,
        method: str,
        parameters: dict[str, Any],
    ) -> float:
        if not np.all(np.isfinite(solution)):
            raise NumericalConvergenceError(f"{method} produced a non-finite solution.")
        product = matrix @ solution
        residual = float(np.linalg.norm(product - rhs))
        reference = max(float(np.linalg.norm(rhs)), float(np.linalg.norm(product)), 1.0)
        relative = residual / reference
        limit = float(parameters.get("residual_failure_tolerance", 1.0e-7))
        if not np.isfinite(residual) or not np.isfinite(relative):
            raise NumericalConvergenceError(f"{method} produced a non-finite residual.")
        if relative > limit:
            raise NumericalConvergenceError(
                f"{method} residual is abnormal: relative={relative:.6e}, allowed={limit:.6e}."
            )
        return residual
