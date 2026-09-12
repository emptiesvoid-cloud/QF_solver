"""One auditable sparse linear-solver adapter for nonlinear Newton steps."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any, cast

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import LinearOperator, spilu

from solveur.core.errors import NumericalConvergenceError
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.core.nonlinear.robustness import NonlinearRobustnessOptions, solve_scaled_system
from solveur.core.nonlinear.telemetry import process_memory_bytes
from solveur.core.solvers.linear import LinearSystemSolver


@dataclass(frozen=True)
class NonlinearLinearSolverAdapter:
    """Dispatch one reduced Newton correction without owning nonlinear state.

    The adapter deliberately owns only matrix classification, sparse solve
    selection, residual verification and direct fallback.  The caller retains
    transaction, line-search and failure/retry ownership.
    """

    options: NonlinearRobustnessOptions | None = None

    def solve(
        self,
        matrix: csr_matrix,
        rhs: np.ndarray,
        *,
        reference_solution: np.ndarray | None = None,
        allow_unverified_krylov: bool = False,
    ) -> tuple[np.ndarray, dict[str, object]]:
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
        configuration["allow_unverified_krylov"] = bool(allow_unverified_krylov)
        symmetry_defect = _symmetry_defect(values)
        symmetric = symmetry_defect <= configuration["symmetry_tolerance"]
        requested = configuration["requested_method"]
        method = _effective_method(requested, symmetric, configuration["assume_spd"])
        try:
            preconditioner, preconditioner_operator, preconditioner_diagnostics = self._prepare_preconditioner(
                values, method, configuration
            )
        except (RuntimeError, ValueError) as exc:
            if method == "direct" or not configuration["direct_fallback"]:
                raise NumericalConvergenceError(
                    f"Nonlinear {method} preconditioner setup failed: {exc}",
                    reason=NonlinearFailureReason.LINEAR_SOLVER_FAILURE,
                    diagnostics={"preconditioner_setup_error": str(exc)},
                ) from exc
            preconditioner = "none"
            preconditioner_operator = None
            preconditioner_diagnostics = {
                "setup_seconds": None,
                "rss_before_bytes": None,
                "rss_after_bytes": None,
                "private_before_bytes": None,
                "private_after_bytes": None,
                "setup_error": str(exc),
            }
        fallback_used = False
        fallback_reason: str | None = None
        if preconditioner == "invalid_direct_fallback":
            fallback_used = True
            fallback_reason = str(preconditioner_diagnostics.get("reason", "preconditioner contract was not satisfied"))

        try:
            correction, details = self._solve_once(
                values, vector, method, preconditioner, configuration, preconditioner_operator
            )
        except NumericalConvergenceError as exc:
            if method == "direct" or not configuration["direct_fallback"]:
                mapped = self._mapped_failure(exc, method, symmetry_defect)
                mapped.diagnostics.update(
                    {
                        "preconditioner_setup_seconds": preconditioner_diagnostics.get("setup_seconds"),
                        "preconditioner_rss_before_bytes": preconditioner_diagnostics.get("rss_before_bytes"),
                        "preconditioner_rss_after_bytes": preconditioner_diagnostics.get("rss_after_bytes"),
                        "preconditioner_private_before_bytes": preconditioner_diagnostics.get("private_before_bytes"),
                        "preconditioner_private_after_bytes": preconditioner_diagnostics.get("private_after_bytes"),
                        "preconditioner": preconditioner,
                    }
                )
                raise mapped from exc
            fallback_used = True
            fallback_reason = str(exc)
            correction, details = self._solve_once(values, vector, "direct", "none", configuration, None)

        if not np.all(np.isfinite(correction)):
            reason = NonlinearFailureReason.NAN_DETECTED if np.any(np.isnan(correction)) else NonlinearFailureReason.INF_DETECTED
            raise NumericalConvergenceError(
                "Full Newton linear solver produced a non-finite correction.",
                reason=reason,
                diagnostics={"linear_method": details["method"], "fallback_used": fallback_used},
            )
        residual, relative_residual, backward_error = _residual_metrics(
            values, vector, correction, configuration["absolute_floor"]
        )
        is_krylov_result = details["method"] != "direct"
        contract_satisfied = not is_krylov_result or backward_error <= configuration["backward_error_tolerance"]
        if is_krylov_result and not contract_satisfied and not allow_unverified_krylov:
            if method != "direct" and configuration["direct_fallback"] and not fallback_used:
                fallback_used = True
                fallback_reason = "iterative residual contract was not satisfied"
                correction, details = self._solve_once(values, vector, "direct", "none", configuration, None)
                residual, relative_residual, backward_error = _residual_metrics(
                    values, vector, correction, configuration["absolute_floor"]
                )
            if not np.all(np.isfinite(correction)) or (
                details["method"] != "direct" and backward_error > configuration["backward_error_tolerance"]
            ):
                raise NumericalConvergenceError(
                    "Full Newton linear correction failed its residual contract.",
                    reason=NonlinearFailureReason.LINEAR_SOLVER_FAILURE,
                    diagnostics={
                        "linear_method": method,
                        "relative_linear_residual": relative_residual,
                        "residual_tolerance": configuration["residual_tolerance"],
                        "backward_error_eta_inf": backward_error,
                        "backward_error_tolerance": configuration["backward_error_tolerance"],
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
            "raw_relative_residual": relative_residual,
            "backward_error_eta_inf": backward_error,
            "backward_error_tolerance": configuration["backward_error_tolerance"],
            "matrix_shape": list(values.shape),
            "matrix_nnz": int(values.nnz),
            "symmetry_defect": symmetry_defect,
            "symmetry_tolerance": configuration["symmetry_tolerance"],
            "matrix_symmetric": symmetric,
            "assume_spd": configuration["assume_spd"],
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
            "post_solve_residual_contract_satisfied": contract_satisfied,
            "allow_unverified_krylov": allow_unverified_krylov,
            "preconditioner_setup_seconds": preconditioner_diagnostics.get("setup_seconds"),
            "preconditioner_rss_before_bytes": preconditioner_diagnostics.get("rss_before_bytes"),
            "preconditioner_rss_after_bytes": preconditioner_diagnostics.get("rss_after_bytes"),
            "preconditioner_private_before_bytes": preconditioner_diagnostics.get("private_before_bytes"),
            "preconditioner_private_after_bytes": preconditioner_diagnostics.get("private_after_bytes"),
            "linear_solve_seconds": details.get("solve_seconds"),
            "gmres_restart": configuration["gmres_restart"],
            "ilu_drop_tol": configuration["ilu_drop_tol"],
            "ilu_fill_factor": configuration["ilu_fill_factor"],
        }
        if reference_solution is not None:
            reference = np.asarray(reference_solution, dtype=float)
            if reference.shape != correction.shape or not np.all(np.isfinite(reference)):
                raise ValueError("reference_solution must be finite and match the linear correction shape.")
            difference = correction - reference
            diagnostics["solution_relative_difference"] = float(
                np.linalg.norm(difference)
                / max(float(np.linalg.norm(reference)), float(configuration["absolute_floor"]))
            )
            if symmetric:
                candidate_energy = float(correction @ (values @ correction))
                reference_energy = float(reference @ (values @ reference))
                diagnostics["quadratic_energy_relative_difference"] = abs(candidate_energy - reference_energy) / max(
                    abs(reference_energy), float(configuration["absolute_floor"])
                )
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
            "backward_error_tolerance": 1.0e-10 if options is None else options.linear_backward_error_tolerance,
            "absolute_floor": 1.0e-14 if options is None else options.linear_absolute_floor,
            "symmetry_tolerance": 1.0e-12 if options is None else options.linear_symmetry_tolerance,
            "direct_fallback": True if options is None else options.linear_direct_fallback,
            "jacobi_diagonal_floor": 1.0e-14 if options is None else options.jacobi_diagonal_floor,
            "ilu_drop_tol": 1.0e-4 if options is None else options.ilu_drop_tol,
            "ilu_fill_factor": 10.0 if options is None else options.ilu_fill_factor,
            "gmres_restart": 50 if options is None else options.gmres_restart,
        }

    def _prepare_preconditioner(
        self,
        matrix: csr_matrix,
        method: str,
        configuration: dict[str, Any],
    ) -> tuple[str, LinearOperator | None, dict[str, object]]:
        requested = str(configuration["preconditioner"])
        rss_before, private_before = process_memory_bytes()
        started = perf_counter()

        def metrics(rss_after: int | None, private_after: int | None) -> dict[str, object]:
            return {
                "setup_seconds": perf_counter() - started,
                "rss_before_bytes": rss_before,
                "rss_after_bytes": rss_after,
                "private_before_bytes": private_before,
                "private_after_bytes": private_after,
            }

        if requested == "none":
            rss_after, private_after = process_memory_bytes()
            return "none", None, metrics(rss_after, private_after)
        diagonal = np.asarray(matrix.diagonal(), dtype=float)
        threshold = float(configuration["jacobi_diagonal_floor"]) * max(
            float(np.max(np.abs(diagonal), initial=0.0)), 1.0
        )
        valid = bool(np.all(np.isfinite(diagonal)) and np.all(np.abs(diagonal) > threshold))
        positive_required = method in {"cg", "minres"}
        if positive_required:
            valid = valid and bool(np.all(diagonal > threshold))
        if requested == "ilu":
            if method != "gmres":
                rss_after, private_after = process_memory_bytes()
                return "invalid_direct_fallback", None, {
                    **metrics(rss_after, private_after),
                    "reason": "ILU is restricted to GMRES in the nonlinear adapter",
                }
            factor = spilu(
                matrix.tocsc(),
                drop_tol=float(configuration["ilu_drop_tol"]),
                fill_factor=float(configuration["ilu_fill_factor"]),
            )

            def matvec_ilu(vector: np.ndarray) -> np.ndarray:
                return factor.solve(vector)

            operator = LinearOperator(matrix.shape, matvec=matvec_ilu, dtype=float)
            rss_after, private_after = process_memory_bytes()
            return "ilu", operator, metrics(rss_after, private_after)
        if requested != "jacobi":
            raise ValueError(f"Unsupported nonlinear preconditioner {requested!r}.")
        if valid:
            inverse = 1.0 / diagonal

            def matvec_jacobi(vector: np.ndarray) -> np.ndarray:
                return inverse * vector

            operator = LinearOperator(matrix.shape, matvec=matvec_jacobi, dtype=float)
            rss_after, private_after = process_memory_bytes()
            return "jacobi", operator, metrics(rss_after, private_after)
        if configuration["direct_fallback"]:
            rss_after, private_after = process_memory_bytes()
            return "invalid_direct_fallback", None, {
                **metrics(rss_after, private_after),
                "reason": "Jacobi preconditioner contract was not satisfied",
            }
        rss_after, private_after = process_memory_bytes()
        return "none", None, metrics(rss_after, private_after)

    def _solve_once(
        self,
        matrix: csr_matrix,
        rhs: np.ndarray,
        method: str,
        preconditioner: str,
        configuration: dict[str, Any],
        preconditioner_operator: LinearOperator | None,
    ) -> tuple[np.ndarray, dict[str, object]]:
        if preconditioner == "invalid_direct_fallback":
            return self._solve_once(matrix, rhs, "direct", "none", configuration, None)
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
                "solve_seconds": None,
                "compatibility_diagnostics": compatibility,
            }
        parameters = {
            "rtol": configuration["rtol"],
            "atol": configuration["atol"],
            "maxiter": configuration["maxiter"],
            "preconditioner": preconditioner,
            "_preconditioner_operator": preconditioner_operator,
            # The generic solver must return the candidate so this adapter can
            # apply the R2 scale-aware backward-error contract.  Raw residual
            # remains diagnostic; nonfinite and SciPy non-convergence errors
            # still fail before this post-solve check.
            "residual_failure_tolerance": (
                1.0e300
                if method != "direct"
                else max(float(configuration["residual_tolerance"]), 1.0e-7)
            ),
        }
        if method == "gmres":
            parameters["restart"] = configuration["gmres_restart"]
        info_solver = LinearSystemSolver()
        started = perf_counter()
        try:
            correction, info = info_solver.solve(matrix, rhs, method=method, parameters=parameters)
        except NumericalConvergenceError as exc:
            exc.diagnostics["solve_seconds"] = perf_counter() - started
            raise
        solve_seconds = perf_counter() - started
        backend = "scipy.sparse.linalg.spsolve" if method == "direct" else f"scipy.sparse.linalg.{method}"
        return correction, {
            "backend": backend,
            "method": method,
            "preconditioner": preconditioner,
            "iterations": int(info.iterations),
            "solve_seconds": solve_seconds,
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
                "solver_info": error.diagnostics.get("solver_info"),
                "krylov_iterations": error.diagnostics.get("iterations"),
                "linear_solve_seconds": error.diagnostics.get("solve_seconds"),
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


def _residual_metrics(
    matrix: csr_matrix, rhs: np.ndarray, solution: np.ndarray, absolute_floor: float
) -> tuple[float, float, float]:
    residual_vector = np.asarray(matrix @ solution - rhs, dtype=float)
    residual = float(np.linalg.norm(residual_vector))
    raw_relative = residual / max(float(np.linalg.norm(rhs)), float(absolute_floor))
    matrix_inf = float(np.max(np.asarray(np.abs(matrix).sum(axis=1)).ravel(), initial=0.0))
    solution_inf = float(np.max(np.abs(solution), initial=0.0))
    rhs_inf = float(np.max(np.abs(rhs), initial=0.0))
    denominator = max(matrix_inf * solution_inf + rhs_inf, float(absolute_floor))
    backward_error = float(np.max(np.abs(residual_vector), initial=0.0)) / denominator
    return residual, raw_relative, backward_error
