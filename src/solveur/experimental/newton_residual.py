"""Exact supplemental check for the original direct Newton candidate."""

from math import isfinite

import numpy as np
from scipy.sparse import csr_matrix

from solveur.core.errors import NumericalConvergenceError
from solveur.core.solvers.linear import LinearSystemSolver, validate_residual_failure_tolerance
from solveur.experimental.eas_residual.bounded_exact_supervisor import _spawn_monitored, identity
from solveur.experimental.newton_exact_csr import Limits, check_residual

THRESHOLD = 1e-7
LIMITS = Limits()
TIMEOUT = 15.0
RSS_LIMIT = 256 * 2**20
INPUT_LIMIT = 8 * 2**20
MAX_CHECKS = 8
MAX_CONFIGURED_CHECKS = 24
NORMALIZATION = "l2/max(l2(Ax),l2(b))"


def _worker(pipe, arrays, shape, threshold, request_id):
    try:
        if identity(arrays, shape, threshold) != request_id or threshold != THRESHOLD:
            return
        verdict = check_residual(*arrays, tolerance=threshold, limits=LIMITS)
        pipe.send({"identity": request_id, "normalization": NORMALIZATION, **verdict})
    finally:
        pipe.close()


def _validated_response(reply, request_id, dimension, terms):
    if (
        not isinstance(reply, dict)
        or reply.get("identity") != request_id
        or reply.get("normalization") != NORMALIZATION
    ):
        return {"status": "INCONCLUSIVE", "reason": "RESPONSE_IDENTITY_OR_NORMALIZATION"}
    status = reply.get("status")
    if status == "INCONCLUSIVE" and isinstance(reply.get("reason"), str):
        return {"status": status, "reason": reply["reason"]}
    try:
        pair = reply["relative_squared_hex"]
        if (
            status not in ("PASS", "FAIL")
            or reply.get("threshold_hex") != THRESHOLD.hex()
            or reply.get("dimension") != dimension
            or reply.get("stored_terms") != terms
            or not isinstance(pair, list)
            or len(pair) != 2
            or any(not isinstance(v, str) or len(v) > 5000 for v in pair)
        ):
            raise ValueError("Inconsistent result fields")
        numerator, denominator = (int(value, 16) for value in pair)
        tau_num, tau_den = THRESHOLD.as_integer_ratio()
        if numerator < 0 or denominator <= 0:
            raise ValueError("Invalid squared ratio")
        passes = numerator * tau_den**2 <= denominator * tau_num**2
        if passes != (status == "PASS"):
            raise ValueError("Inconsistent exact decision")
    except (ValueError, TypeError, KeyError):
        return {"status": "INCONCLUSIVE", "reason": "INVALID_EXACT_RESULT"}
    return {
        "status": status,
        "relative_squared_hex": pair,
        "threshold_hex": THRESHOLD.hex(),
        "verifier_seconds": reply.get("verifier_seconds"),
    }


def verify_candidate(matrix, rhs, candidate):
    """Check the original binary64 values in a bounded process, without a solve."""
    if not isinstance(matrix, csr_matrix):
        return {"status": "INCONCLUSIVE", "reason": "UNSUPPORTED_MATRIX"}
    live = (matrix.data, matrix.indices, matrix.indptr, rhs, candidate)
    dimension, columns = matrix.shape
    if (
        not 0 < dimension == columns <= LIMITS.dimension
        or matrix.nnz > LIMITS.terms
        or not all(isinstance(a, np.ndarray) for a in live)
        or sum(a.nbytes for a in live) > INPUT_LIMIT
    ):
        return {"status": "INCONCLUSIVE", "reason": "INPUT_LIMIT_OR_TYPE"}
    arrays = tuple(a.copy() for a in live)
    request_id = identity(arrays, matrix.shape, THRESHOLD)
    reply, monitor = _spawn_monitored(
        _worker,
        (arrays, matrix.shape, THRESHOLD, request_id),
        TIMEOUT,
        RSS_LIMIT,
    )
    if monitor.get("reason") != "CHILD_EXIT" or monitor.get("child_exitcode") != 0:
        result = {"status": "INCONCLUSIVE", "reason": monitor.get("reason", "MONITOR_FAILURE")}
        if result["reason"] == "CHILD_EXIT":
            result["reason"] = "CHILD_EXIT_NONZERO"
    else:
        result = _validated_response(reply, request_id, dimension, matrix.nnz)
    if identity((matrix.data, matrix.indices, matrix.indptr, rhs, candidate), matrix.shape, THRESHOLD) != request_id:
        result = {"status": "INCONCLUSIVE", "reason": "INPUT_CHANGED_DURING_CHECK"}
    return {
        **result,
        "identity": request_id,
        "normalization": NORMALIZATION,
        "threshold_hex": THRESHOLD.hex(),
        "monitor": monitor,
    }


def _bound_only(rejection, threshold):
    details = rejection.diagnostics
    raw = details.get("relative_residual")
    upper = details.get("relative_residual_upper_bound")
    return (
        threshold == details.get("residual_failure_tolerance") == THRESHOLD
        and "cannot demonstrate residual convergence within floating-point roundoff" in str(rejection)
        and isinstance(raw, (int, float))
        and isfinite(raw)
        and 0 <= raw <= threshold
        and isinstance(upper, (int, float))
        and isfinite(upper)
        and upper > threshold
    )


class ExactNewtonLinearSolver(LinearSystemSolver):
    """Retain the historical gate and optionally verify its original candidate."""

    def __init__(self, max_checks: int = MAX_CHECKS):
        if type(max_checks) is not int or not 1 <= max_checks <= MAX_CONFIGURED_CHECKS:
            raise ValueError("Exact Newton check budget must be an integer from 1 to 24.")
        self.max_checks = max_checks
        self.checks_used = 0
        self.last_report = None

    def solve(self, matrix, rhs, *, method, parameters=None):
        self.last_report = None
        parameters = parameters or {}
        if (
            method != "direct"
            or parameters.get("backend") != "scipy"
            or validate_residual_failure_tolerance(parameters) != THRESHOLD
            or parameters.get("experimental_direct_refinement_steps", 0) != 0
        ):
            raise ValueError("Exact Newton requires the unrefined direct SciPy path at tolerance 1e-7.")
        return super().solve(matrix, rhs, method=method, parameters=parameters)

    def _validated_residual_metrics(self, matrix, rhs, solution, method, parameters):
        try:
            metrics = super()._validated_residual_metrics(matrix, rhs, solution, method, parameters)
        except NumericalConvergenceError as rejection:
            threshold = validate_residual_failure_tolerance(parameters)
            eligible = method == "direct" and _bound_only(rejection, threshold)
            report = {
                "historical_decision": "REJECTED_BOUND" if eligible else "REJECTED",
                "historical_message": str(rejection),
                "historical_diagnostics": dict(rejection.diagnostics),
                "exact": {"status": "NOT_RUN", "reason": "INELIGIBLE_GUARD_REJECTION"},
                "correction_authorized": False,
            }
            self.last_report = report
            if eligible and self.checks_used >= self.max_checks:
                report["exact"] = {"status": "INCONCLUSIVE", "reason": "CHECK_BUDGET_EXHAUSTED"}
            elif eligible:
                self.checks_used += 1
                try:
                    report["exact"] = verify_candidate(matrix, rhs, solution)
                except (Exception, KeyboardInterrupt) as error:
                    report["exact"] = {"status": "INCONCLUSIVE", "reason": type(error).__name__}
                if report["exact"]["status"] == "PASS":
                    report["correction_authorized"] = True
                    return rejection.diagnostics["residual_norm"], rejection.diagnostics["relative_residual"]
            rejection.diagnostics["experimental_newton_exact_residual"] = report
            raise
        self.last_report = {
            "historical_decision": "ACCEPTED",
            "exact": {"status": "NOT_RUN"},
            "correction_authorized": True,
        }
        return metrics
