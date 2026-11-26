"""Opt-in exact residual acceptance for the bounded EAS static route."""
from dataclasses import replace
import hmac
import json
import math
import secrets

import numpy as np
from scipy.sparse import csr_matrix, isspmatrix_csr
from scipy.sparse.linalg import splu

from solveur.core.errors import NumericalConvergenceError
from solveur.core.solvers.backend import select_backend
from solveur.core.solvers.linear import (
    LinearSystemSolver,
    stable_l2_norm,
    validate_residual_failure_tolerance,
)
from solveur.experimental.eas_residual import bounded_exact_supervisor as supervisor
from solveur.experimental.eas_residual.exact_residual import exact_check

OPTION = "experimental_eas_exact_residual_acceptance"
THRESHOLD = 1e-7
MAX_ROWS = 1500
MAX_NNZ = 100_000
MAX_BYTES = 8 * 2**20
MAX_CORRECTIONS = 3
TIMEOUT = 10.0
RSS_LIMIT = 256 * 2**20


def _signature(key, payload):
    wire = json.dumps(payload, sort_keys=True, allow_nan=False).encode("ascii")
    return hmac.digest(key, wire, "sha256")


def _refine(arrays, shape, threshold):
    data, indices, indptr, rhs, candidate = arrays
    factor = None
    trials = []
    for step in range(MAX_CORRECTIONS + 1):
        evidence = exact_check(data, indices, indptr, shape, rhs, candidate, threshold,
                               max_nnz=MAX_NNZ, correction=step < MAX_CORRECTIONS)
        decision = evidence["decision"]
        trial_id = supervisor.identity((data, indices, indptr, rhs, candidate), shape, threshold)
        trials.append({"identity": trial_id, "decision": decision})
        if decision == "PASS":
            return candidate, trials
        if step == MAX_CORRECTIONS:
            break
        if factor is None:
            factor = splu(csr_matrix((data, indices, indptr), shape=shape).tocsc())
        candidate = candidate + factor.solve(evidence["correction_rhs"])
    return None, trials


def _worker(pipe, arrays, shape, threshold, request_id, key, output):
    try:
        if supervisor.identity(arrays, shape, threshold) != request_id:
            return
        candidate, trials = _refine(arrays, shape, threshold)
        if candidate is not None:
            np.frombuffer(output, dtype=np.float64)[:] = candidate
        payload = {"request_identity": request_id, "trials": trials}
        pipe.send((payload, _signature(key, payload)))
    except (ArithmeticError, RuntimeError, ValueError):
        # No complete reply and therefore no acceptance.
        pass
    finally:
        pipe.close()


def _verified_trials(reply, key, request_id):
    if not isinstance(reply, tuple) or len(reply) != 2:
        return None
    payload, signature = reply
    if not isinstance(payload, dict) or not isinstance(signature, bytes):
        return None
    if not hmac.compare_digest(_signature(key, payload), signature):
        return None
    if set(payload) != {"request_identity", "trials"} or payload["request_identity"] != request_id:
        return None
    trials = payload["trials"]
    if not isinstance(trials, list) or not 1 <= len(trials) <= MAX_CORRECTIONS + 1:
        return None
    for trial in trials:
        if (not isinstance(trial, dict) or set(trial) != {"identity", "decision"}
                or not isinstance(trial["identity"], str) or trial["decision"] not in ("PASS", "FAIL")):
            return None
    if (trials[0]["identity"] != request_id or any(row["decision"] != "FAIL" for row in trials[:-1])
            or (trials[-1]["decision"] == "FAIL" and len(trials) != MAX_CORRECTIONS + 1)):
        return None
    return trials


def recover_candidate(matrix, rhs, initial, threshold):
    """Replay and optionally refine one rejected candidate in one child."""
    if supervisor.psutil is None:
        return None, {"supplemental": "INCONCLUSIVE", "reason": "PSUTIL_UNAVAILABLE"}
    if (threshold != THRESHOLD or not isspmatrix_csr(matrix)
            or not 0 < matrix.shape[0] == matrix.shape[1] <= MAX_ROWS
            or matrix.nnz > MAX_NNZ):
        return None, {"supplemental": "INCONCLUSIVE", "reason": "OUTSIDE_EXPERIMENT_BUDGET"}
    inputs = (matrix.data, matrix.indices, matrix.indptr, rhs, initial)
    if sum(item.nbytes for item in inputs) > MAX_BYTES:
        return None, {"supplemental": "INCONCLUSIVE", "reason": "OUTSIDE_EXPERIMENT_BUDGET"}
    arrays = tuple(item.copy() for item in inputs)
    shape = matrix.shape
    request_id = supervisor.identity(arrays, shape, threshold)
    key = secrets.token_bytes(32)
    output = supervisor.mp.get_context("spawn").RawArray("d", shape[0])
    reply, monitor = supervisor._spawn_monitored(
        _worker, (arrays, shape, threshold, request_id, key, output), TIMEOUT, RSS_LIMIT,
    )
    report = {**monitor, "request_identity": request_id, "threshold_binary64": threshold.hex(),
              "refinement": "sparse_lu_exact_residual", "supplemental": "INCONCLUSIVE"}
    if monitor["reason"] != "CHILD_EXIT" or monitor.get("child_exitcode") != 0:
        return None, report
    trials = _verified_trials(reply, key, request_id)
    if trials is None or supervisor.identity(inputs, shape, threshold) != request_id:
        return None, {**report, "reason": "INVALID_EXACT_RESPONSE"}
    report.update(trials=trials, correction_count=len(trials) - 1)
    if trials[-1]["decision"] == "FAIL":
        return None, {**report, "supplemental": "FAIL", "reason": "CORRECTIONS_EXHAUSTED"}
    candidate = np.frombuffer(output, dtype=np.float64).copy()
    candidate_id = supervisor.identity((*arrays[:-1], candidate), shape, threshold)
    if candidate_id != trials[-1]["identity"] or not np.all(np.isfinite(candidate)):
        return None, {**report, "reason": "INVALID_EXACT_CANDIDATE"}
    return candidate, {**report, "supplemental": "PASS", "reason": "EXACT_CRITERION_MET",
                       "candidate_identity": candidate_id}


class ExperimentalExactLinearSolver(LinearSystemSolver):
    """Return an exact-verified replacement only on the explicitly selected route."""

    def solve(self, matrix, rhs, *, method, parameters=None):
        self.acceptance = None
        self._replacement = None
        parameters = parameters or {}
        if parameters.get("experimental_direct_refinement_steps", 0) != 0:
            raise ValueError(f"{OPTION} cannot be combined with direct refinement before the guard.")
        backend = select_backend(parameters.get("backend"), problem_size=matrix.shape[0], parameters=parameters)
        if method != "direct" or backend.selected != "scipy":
            raise ValueError(f"{OPTION} requires a direct SciPy solve.")
        solution, info = super().solve(matrix, rhs, method=method, parameters=parameters)
        if self._replacement is not None:
            solution = self._replacement
            info = replace(info, termination_reason="experimental_exact_residual_accepted")
        return solution, info

    def _validated_residual_metrics(self, matrix, rhs, solution, method, parameters):
        try:
            return super()._validated_residual_metrics(matrix, rhs, solution, method, parameters)
        except NumericalConvergenceError as rejection:
            threshold = validate_residual_failure_tolerance(parameters)
            prior_ratio = rejection.diagnostics.get("relative_residual", math.inf)
            report = {"supplemental": "INCONCLUSIVE", "reason": "INELIGIBLE_GUARD_REJECTION"}
            if math.isfinite(prior_ratio) and threshold == THRESHOLD:
                try:
                    candidate, report = recover_candidate(matrix, rhs, solution, threshold)
                    if candidate is not None and report["supplemental"] == "PASS":
                        product = matrix @ candidate
                        residual = stable_l2_norm(product - rhs)
                        scale = max(stable_l2_norm(product), stable_l2_norm(rhs))
                        if math.isfinite(residual) and math.isfinite(scale) and scale > 0:
                            self._replacement = candidate
                            self.acceptance = {**report, "historical_decision": "REJECTED",
                                               "historical_diagnostics": dict(rejection.diagnostics)}
                            return residual, residual / scale
                        report.update(supplemental="INCONCLUSIVE", reason="INVALID_FLOATING_METRICS")
                except (Exception, KeyboardInterrupt) as error:
                    report = {"supplemental": "INCONCLUSIVE", "reason": type(error).__name__}
            rejection.diagnostics[OPTION] = {**report, "historical_decision": "REJECTED"}
            raise
