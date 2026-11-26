"""Attach opt-in exact diagnostics to the original residual guard rejection."""
from solveur.core.errors import NumericalConvergenceError
from solveur.core.solvers.linear import LinearSystemSolver

from solveur.experimental.eas_residual.bounded_exact_supervisor import supervise


class DiagnosticLinearSolver(LinearSystemSolver):
    """Apply the original guard first and preserve its return or exception."""

    def __init__(self):
        self.last_diagnostic = None

    def _validated_residual_metrics(self, matrix, rhs, solution, method, parameters):
        self.last_diagnostic = None
        try:
            value = LinearSystemSolver._validated_residual_metrics(matrix, rhs, solution, method, parameters)
        except NumericalConvergenceError as exc:
            try:
                threshold = parameters.get("residual_failure_tolerance", 1e-7)
                if threshold != 1e-7:
                    self.last_diagnostic = {"supplemental": "INCONCLUSIVE", "reason": "UNSUPPORTED_THRESHOLD"}
                else:
                    self.last_diagnostic = supervise(matrix.data, matrix.indices, matrix.indptr, matrix.shape, rhs, solution, 1e-7)
                if not isinstance(self.last_diagnostic, dict):
                    self.last_diagnostic = {"supplemental": "INCONCLUSIVE", "reason": "INVALID_SUPERVISOR_RESULT"}
            except (Exception, KeyboardInterrupt) as diagnostic_error:
                self.last_diagnostic = {"supplemental": "INCONCLUSIVE", "reason": type(diagnostic_error).__name__}
            replay_decision = self.last_diagnostic.get("historical_decision", "NOT_RUN")
            if self.last_diagnostic.get("supplemental") in ("PASS", "FAIL") and replay_decision != "REJECTED":
                self.last_diagnostic.update(supplemental="INCONCLUSIVE", reason="GUARD_REPLAY_MISMATCH")
            self.last_diagnostic["supervisor_guard_replay_decision"] = replay_decision
            self.last_diagnostic["historical_decision"] = "REJECTED"
            exc.diagnostics["experimental_exact_residual_diagnostic"] = self.last_diagnostic
            raise
        return value
