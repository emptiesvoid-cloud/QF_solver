"""Exercise the exact recovery path without assembling a FEM system."""
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from solveur.core.errors import NumericalConvergenceError
from solveur.core.solvers import linear
from solveur.experimental.eas_residual import experimental_acceptance as acceptance


def test_real_child_refines_rejected_candidate(monkeypatch):
    monkeypatch.setattr(linear, "spsolve", lambda *_a: np.zeros(2))
    solver = acceptance.ExperimentalExactLinearSolver()
    matrix, rhs = csr_matrix(np.eye(2)), np.ones(2)
    solution, info = solver.solve(matrix, rhs, method="direct")
    np.testing.assert_array_equal(solution, rhs)
    assert info.termination_reason == "experimental_exact_residual_accepted"
    assert solver.acceptance["historical_decision"] == "REJECTED"
    assert [trial["decision"] for trial in solver.acceptance["trials"]] == ["FAIL", "PASS"]


def test_historical_acceptance_does_not_recover(monkeypatch):
    monkeypatch.setattr(acceptance, "recover_candidate", lambda *_a: pytest.fail("unexpected recovery"))
    solver = acceptance.ExperimentalExactLinearSolver()
    solution, info = solver.solve(csr_matrix(np.eye(2)), np.ones(2), method="direct")
    np.testing.assert_array_equal(solution, np.ones(2))
    assert info.termination_reason == "converged"
    assert solver.acceptance is None


def test_exact_option_disallows_additional_direct_refinement():
    with pytest.raises(ValueError, match="before the guard"):
        acceptance.ExperimentalExactLinearSolver().solve(
            csr_matrix(np.eye(2)), np.ones(2), method="direct",
            parameters={"experimental_direct_refinement_steps": 4},
        )


@pytest.mark.parametrize("fault", ["timeout", "interruption", "incomplete", "response", "matrix", "rhs",
                                    "initial", "threshold", "output"])
def test_fault_retains_original_rejection(monkeypatch, fault):
    monkeypatch.setattr(linear, "spsolve", lambda *_a: np.zeros(2))

    def substituted(_worker, args, *_limits):
        arrays, shape, threshold, request_id, key, output = args
        if fault in {"timeout", "interruption", "incomplete"}:
            return None, {"reason": "TIMEOUT" if fault == "timeout" else "CHILD_EXIT",
                          "child_exitcode": 1 if fault == "interruption" else 0}
        candidate = np.ones(2)
        np.frombuffer(output, dtype=np.float64)[:] = candidate
        altered = [item.copy() for item in arrays]
        if fault in {"matrix", "rhs", "initial"}:
            altered[{"matrix": 0, "rhs": 3, "initial": 4}[fault]][0] += 1
        other_threshold = threshold / 2 if fault == "threshold" else threshold
        altered_id = acceptance.supervisor.identity(altered, shape, other_threshold)
        candidate_id = acceptance.supervisor.identity((*altered[:-1], candidate), shape, other_threshold)
        payload = {"request_identity": altered_id, "trials": [
            {"identity": altered_id, "decision": "FAIL"},
            {"identity": candidate_id, "decision": "PASS"},
        ]}
        tag = acceptance._signature(key, payload)
        if fault == "response":
            payload["trials"][0]["decision"] = "PASS"
        if fault == "output":
            np.frombuffer(output, dtype=np.float64)[0] = 2
        assert request_id == acceptance.supervisor.identity(arrays, shape, threshold)
        return (payload, tag), {"reason": "CHILD_EXIT", "child_exitcode": 0}

    monkeypatch.setattr(acceptance.supervisor, "_spawn_monitored", substituted)
    with pytest.raises(NumericalConvergenceError) as caught:
        acceptance.ExperimentalExactLinearSolver().solve(csr_matrix(np.eye(2)), np.ones(2), method="direct")
    assert caught.value.diagnostics[acceptance.OPTION]["supplemental"] == "INCONCLUSIVE"
    assert caught.value.diagnostics[acceptance.OPTION]["historical_decision"] == "REJECTED"


def test_exhausted_refinement_never_returns_candidate(monkeypatch):
    def no_progress(_matrix):
        return SimpleNamespace(solve=lambda vector: np.zeros_like(vector))
    monkeypatch.setattr(acceptance, "splu", no_progress)
    matrix = csr_matrix(np.eye(2))
    candidate, trials = acceptance._refine(
        (matrix.data, matrix.indices, matrix.indptr, np.ones(2), np.zeros(2)),
        matrix.shape, acceptance.THRESHOLD,
    )
    assert candidate is None
    assert [trial["decision"] for trial in trials] == ["FAIL"] * (acceptance.MAX_CORRECTIONS + 1)

    def completed_failure(_worker, args, *_limits):
        _, _, _, request_id, key, _ = args
        payload = {"request_identity": request_id, "trials": trials}
        return (payload, acceptance._signature(key, payload)), {"reason": "CHILD_EXIT", "child_exitcode": 0}

    monkeypatch.setattr(acceptance.supervisor, "_spawn_monitored", completed_failure)
    monkeypatch.setattr(linear, "spsolve", lambda *_a: np.zeros(2))
    with pytest.raises(NumericalConvergenceError) as caught:
        acceptance.ExperimentalExactLinearSolver().solve(matrix, np.ones(2), method="direct")
    report = caught.value.diagnostics[acceptance.OPTION]
    assert report["reason"] == "CORRECTIONS_EXHAUSTED" and report["supplemental"] == "FAIL"


def test_real_timeout_preserves_guard_exception(monkeypatch):
    monkeypatch.setattr(linear, "spsolve", lambda *_a: np.zeros(2))
    monkeypatch.setattr(acceptance, "TIMEOUT", 1e-6)
    with pytest.raises(NumericalConvergenceError) as caught:
        acceptance.ExperimentalExactLinearSolver().solve(csr_matrix(np.eye(2)), np.ones(2), method="direct")
    assert caught.value.diagnostics[acceptance.OPTION]["reason"] == "TIMEOUT"
    assert caught.value.diagnostics[acceptance.OPTION]["supplemental"] == "INCONCLUSIVE"


def test_missing_extra_retains_rejection(monkeypatch):
    monkeypatch.setattr(linear, "spsolve", lambda *_a: np.zeros(2))
    monkeypatch.setattr(acceptance.supervisor, "psutil", None)
    with pytest.raises(NumericalConvergenceError) as caught:
        acceptance.ExperimentalExactLinearSolver().solve(csr_matrix(np.eye(2)), np.ones(2), method="direct")
    assert caught.value.diagnostics[acceptance.OPTION]["reason"] == "PSUTIL_UNAVAILABLE"
