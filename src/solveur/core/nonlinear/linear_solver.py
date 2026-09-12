"""One auditable sparse linear-solver adapter for nonlinear Newton steps."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import numpy as np
from scipy.sparse import csr_matrix

from solveur.core.errors import NumericalConvergenceError
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.core.nonlinear.robustness import NonlinearRobustnessOptions, solve_scaled_system
from solveur.core.solvers.linear import LinearSystemSolver


@dataclass(frozen=True)
class NonlinearLinearSolverAdapter:
    """Dispatch one reduced Newton correction without owning nonlinear state.

    The adapter deliberately owns only matrix classification, sparse solve
    selection, residual verification and direct fallback.  The caller retains
    transaction, line-search and failure/retry ownership.
    """

    options: NonlinearRobustnessOptions | None = None

    def solve(self, matrix: csr_matrix, rhs: np.ndarray) -> tuple[np.ndarray, dict[str, object]]:
        values = csr_matrix(matrix, dtype=float)
        vector = np.asarray(rhs, dtype=float)
        if values.shape[0] != values.shape[1] or vector.shape != (values.shape[0],):
            raise NumericalConvergenceError(
                "Full Newton reduced tangent has incompatible dimensions.",
                reason=NonlinearFailureReason.LINEAR_SOLVER_FAILURE,
            )
        if not np.all(np.isfinite(values.data)) or not np.all(np.isfinite(vector)):
            raise NumericalConvergenceError(
                "Full Newton reduced tangent or right-hand side is non-finite.",
                reason=NonlinearFailureReason.NAN_DETECTED,
            )

        configuration = self._configuration()
        symmetry_defect = _symmetry_defect(values)
        symmetric = symmetry_defect <= configuration["symmetry_tolerance"]
        requested = configuration["requested_method"]
        method = _effective_method(requested, symmetric, configuration["assume_spd"])
        preconditioner = self._preconditioner(values, method, configuration)
        fallback_used = False
        fallback_reason: str | None = None
        if preconditioner == "invalid_direct_fallback":
            fallback_used = True
            fallback_reason = "Jacobi preconditioner contract was not satisfied"

        try:
            correction, details = self._solve_once(values, vector, method, preconditioner, configuration)
        except NumericalConvergenceError as exc:
            if method == "direct" or not configuration["direct_fallback"]:
                raise self._mapped_failure(exc, method, symmetry_defect) from exc
            fallback_used = True
            fallback_reason = str(exc)
            correction, details = self._solve_once(values, vector, "direct", "none", configuration)

        if not np.all(np.isfinite(correction)):
            reason = NonlinearFailureReason.NAN_DETECTED if np.any(np.isnan(correction)) else NonlinearFailureReason.INF_DETECTED
            raise NumericalConvergenceError(
                "Full Newton linear solver produced a non-finite correction.",
                reason=reason,
                diagnostics={"linear_method": details["method"], "fallback_used": fallback_used},
            )
        residual, relative_residual = _relative_residual(values, vector, correction, configuration["absolute_floor"])
        is_krylov_result = details["method"] != "direct"
        if is_krylov_result and relative_residual > configuration["residual_tolerance"]:
            if method != "direct" and configuration["direct_fallback"] and not fallback_used:
                fallback_used = True
                fallback_reason = "iterative residual contract was not satisfied"
                correction, details = self._solve_once(values, vector, "direct", "none", configuration)
                residual, relative_residual = _relative_residual(
                    values, vector, correction, configuration["absolute_floor"]
                )
            if not np.all(np.isfinite(correction)) or (
                details["method"] != "direct" and relative_residual > configuration["residual_tolerance"]
            ):
                raise NumericalConvergenceError(
                    "Full Newton linear correction failed its residual contract.",
                    reason=NonlinearFailureReason.LINEAR_SOLVER_FAILURE,
                    diagnostics={
                        "linear_method": method,
                        "relative_linear_residual": relative_residual,
                        "residual_tolerance": configuration["residual_tolerance"],
                    },
                )

        diagnostics: dict[str, object] = {
            "linear_backend": details["backend"],
            "linear_method": details["method"],
            "requested_linear_method": requested,
            "preconditioner": details["preconditioner"],
            "krylov_iterations": details["iterations"],
            "linear_residual_norm": residual,
            "linear_relative_residual": relative_residual,
            "matrix_shape": list(values.shape),
            "matrix_nnz": int(values.nnz),
            "symmetry_defect": symmetry_defect,
            "symmetry_tolerance": configuration["symmetry_tolerance"],
            "matrix_symmetric": symmetric,
            "assume_spd": configuration["assume_spd"],
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
        }
        compatibility = details.get("compatibility_diagnostics", {})
        diagnostics.update(cast(dict[str, object], compatibility))
        return np.asarray(correction, dtype=float), diagnostics

    def _configuration(self) -> dict[str, Any]:
        options = self.options
        requested = "direct" if options is None else options.linear_solver
        aliases = {"spsolve": "direct", "splu": "direct"}
        return {
            "requested_method": aliases.get(requested, requested),
            "legacy_solver": requested,
            "preconditioner": "none" if options is None else options.linear_preconditioner,
            "assume_spd": False if options is None else options.linear_assume_spd,
            "rtol": 1.0e-10 if options is None else options.linear_rtol,
            "atol": 1.0e-14 if options is None else options.linear_atol,
            "maxiter": 10_000 if options is None else options.linear_maxiter,
            "residual_tolerance": 1.0e-10 if options is None else options.linear_residual_tolerance,
            "absolute_floor": 1.0e-14 if options is None else options.linear_absolute_floor,
            "symmetry_tolerance": 1.0e-12 if options is None else options.linear_symmetry_tolerance,
            "direct_fallback": True if options is None else options.linear_direct_fallback,
            "jacobi_diagonal_floor": 1.0e-14 if options is None else options.jacobi_diagonal_floor,
        }

    def _preconditioner(
        self, matrix: csr_matrix, method: str, configuration: dict[str, Any]
    ) -> str:
        requested = str(configuration["preconditioner"])
        if requested == "none":
            return "none"
        diagonal = np.asarray(matrix.diagonal(), dtype=float)
        threshold = float(configuration["jacobi_diagonal_floor"]) * max(float(np.max(np.abs(diagonal))), 1.0)
        valid = bool(np.all(np.isfinite(diagonal)) and np.all(np.abs(diagonal) > threshold))
        positive_required = method in {"cg", "minres"}
        if positive_required:
            valid = valid and bool(np.all(diagonal > threshold))
        if valid:
            return "jacobi"
        if configuration["direct_fallback"]:
            return "invalid_direct_fallback"
        return "none"

    def _solve_once(
        self,
        matrix: csr_matrix,
        rhs: np.ndarray,
        method: str,
        preconditioner: str,
        configuration: dict[str, Any],
    ) -> tuple[np.ndarray, dict[str, object]]:
        if preconditioner == "invalid_direct_fallback":
            return self._solve_once(matrix, rhs, "direct", "none", configuration)
        if self.options is not None and method == "direct" and (
            self.options.system_scaling != "none"
            or self.options.residual_scaling != "none"
            or configuration["legacy_solver"] == "splu"
        ):
            correction, compatibility = solve_scaled_system(matrix, rhs, self.options)
            return correction, {
                "backend": str(compatibility["backend"]),
                "method": "direct",
                "preconditioner": "none",
                "iterations": 1,
                "compatibility_diagnostics": compatibility,
            }
        parameters = {
            "rtol": configuration["rtol"],
            "atol": configuration["atol"],
            "maxiter": configuration["maxiter"],
            "preconditioner": preconditioner,
            # Direct sparse LU preserves its historical residual acceptance;
            # the strict 1e-10 post-solve contract is for Krylov candidates.
            "residual_failure_tolerance": (
                max(float(configuration["residual_tolerance"]), 1.0e-7)
                if method == "direct"
                else configuration["residual_tolerance"]
            ),
        }
        info_solver = LinearSystemSolver()
        correction, info = info_solver.solve(matrix, rhs, method=method, parameters=parameters)
        backend = "scipy.sparse.linalg.spsolve" if method == "direct" else f"scipy.sparse.linalg.{method}"
        return correction, {
            "backend": backend,
            "method": method,
            "preconditioner": preconditioner,
            "iterations": int(info.iterations),
        }

    @staticmethod
    def _mapped_failure(
        error: NumericalConvergenceError, method: str, symmetry_defect: float
    ) -> NumericalConvergenceError:
        message = str(error)
        if error.diagnostics.get("nonfinite") == "nan":
            reason = NonlinearFailureReason.NAN_DETECTED
        elif error.diagnostics.get("nonfinite") == "inf":
            reason = NonlinearFailureReason.INF_DETECTED
        else:
            reason = NonlinearFailureReason.SINGULAR_TANGENT if "singular" in message.lower() else NonlinearFailureReason.LINEAR_SOLVER_FAILURE
        backend_error = error.diagnostics.get("backend_error", message.removeprefix("Direct sparse solve failed: "))
        return NumericalConvergenceError(
            f"Full Newton {method} linear solver failed: {message}",
            reason=reason,
            diagnostics={
                "linear_method": method,
                "symmetry_defect": symmetry_defect,
                "backend_error": backend_error,
            },
        )


def _effective_method(requested: str, symmetric: bool, assume_spd: bool) -> str:
    if requested == "auto":
        return "cg" if symmetric and assume_spd else "minres" if symmetric else "gmres"
    if requested not in {"direct", "cg", "minres", "gmres"}:
        raise ValueError(f"Unsupported nonlinear linear solver {requested!r}.")
    return requested


def _symmetry_defect(matrix: csr_matrix) -> float:
    scale = max(float(np.linalg.norm(matrix.data)), 1.0)
    return float(np.linalg.norm((matrix - matrix.T).data)) / scale


def _relative_residual(matrix: csr_matrix, rhs: np.ndarray, solution: np.ndarray, absolute_floor: float) -> tuple[float, float]:
    residual = float(np.linalg.norm(matrix @ solution - rhs))
    return residual, residual / max(float(np.linalg.norm(rhs)), float(absolute_floor))
