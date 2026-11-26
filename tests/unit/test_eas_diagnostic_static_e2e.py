"""Static route with synthetic systems and no element assembly or FEM."""
import multiprocessing as mp
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.sparse import csr_matrix

import solveur.experimental.eas_residual.bounded_exact_supervisor as supervisor
import solveur.experimental.eas_residual.diagnostic_adapter as adapter
import solveur.core.solvers.static as static
from solveur.core.errors import NumericalConvergenceError
from solveur.core.solvers import linear


@pytest.fixture
def route(monkeypatch):
    solver = static.LinearStaticSolver()
    monkeypatch.setattr(solver.validator, "validate", lambda model: SimpleNamespace(status="PASS"))
    monkeypatch.setattr(static, "emit_route_event_best_effort", lambda *a, **k: None)
    monkeypatch.setattr(solver.assembler, "prepare_plan", lambda *a: None)
    monkeypatch.setattr(solver.assembler, "assemble_stiffness", lambda *a, **k: csr_matrix(np.eye(2)))
    monkeypatch.setattr(solver.assembler, "assemble_loads", lambda *a: np.ones(2))
    monkeypatch.setattr(solver.assembler, "fixed_indices", lambda *a: np.array([], dtype=int))
    monkeypatch.setattr(static.LinearSolverPolicy, "assess", lambda *a: SimpleNamespace(recommended_method="direct"))
    monkeypatch.setattr(static.LinearSolverPolicy, "enforce_method_contract", lambda *a: None)
    monkeypatch.setattr(static, "select_backend", lambda *a, **k: SimpleNamespace(selected="scipy"))
    model = SimpleNamespace(contacts=[], elements=[SimpleNamespace(type="HEX8_EAS_EXPERIMENTAL")],
                            analysis=SimpleNamespace(method="direct", parameters={"experimental_eas_exact_residual_diagnostic": True}),
                            dof_manager=lambda: SimpleNamespace(ndof=2), linear_constraints=lambda: [], node_count=2)

    def execute(matrix, rhs, candidate, *, enabled=True, family="HEX8_EAS_EXPERIMENTAL"):
        model.elements[0].type = family
        model.analysis.parameters["experimental_eas_exact_residual_diagnostic"] = enabled
        def stop_after_accept(_values):
            raise RuntimeError("ACCEPTED_REACHED_EXPANSION")
        reduction = SimpleNamespace(independent=np.arange(2), matrix=matrix, rhs=rhs, expand=stop_after_accept)
        monkeypatch.setattr(static.ConstraintReduction, "from_system", lambda *a: reduction)
        monkeypatch.setattr(linear, "spsolve", lambda *_a, **_k: candidate.copy())
        return solver.solve(model)
    return execute


def children():
    return {p.pid for p in mp.active_children()}


def test_accepted_route_does_not_run_supplemental(route, monkeypatch):
    monkeypatch.setattr(adapter, "supervise", lambda *a, **k: pytest.fail("unexpected diagnostic"))
    with pytest.raises(RuntimeError, match="ACCEPTED_REACHED_EXPANSION"):
        route(csr_matrix(np.eye(2)), np.ones(2), np.ones(2))


@pytest.mark.parametrize("exact_pass", [True, False])
def test_rejected_route_exact_result_never_promotes(route, exact_pass):
    before = children()
    matrix = csr_matrix(np.array([[1e16, 1e16], [1e16, 1e16 + 2.0]])) if exact_pass else csr_matrix(np.eye(2))
    rhs = np.array([0.0, -2.0]) if exact_pass else np.ones(2)
    candidate = np.array([1.0, -1.0]) if exact_pass else np.zeros(2)
    with pytest.raises(NumericalConvergenceError) as error:
        route(matrix, rhs, candidate)
    diag = error.value.diagnostics["experimental_exact_residual_diagnostic"]
    assert diag["historical_decision"] == "REJECTED"
    assert diag["supplemental"] == ("PASS" if exact_pass else "FAIL")
    assert diag["identity"] == supervisor.identity((matrix.data, matrix.indices, matrix.indptr, rhs, candidate), matrix.shape, 1e-7)
    assert diag["child_exitcode"] == 0 and children() <= before


@pytest.mark.parametrize(
    "failure",
    ["exception", "timeout", "monitor", "substitution", "incomplete", "interrupt", "no_psutil",
     "invalid_result", "replay_mismatch"],
)
def test_rejected_route_failure_is_inconclusive_and_child_reaped(route, monkeypatch, failure):
    before = children()
    original = adapter.supervise
    if failure == "exception":
        def fail(*args, **kwargs):
            raise RuntimeError("broken diagnostic")
        monkeypatch.setattr(adapter, "supervise", fail)
    elif failure == "timeout":
        monkeypatch.setattr(adapter, "supervise", lambda *a: original(*a, timeout=0.000001))
    elif failure == "monitor":
        import psutil
        def fail(_pid):
            raise psutil.AccessDenied()
        monkeypatch.setattr(supervisor.psutil, "Process", fail)
    elif failure == "no_psutil":
        monkeypatch.setattr(supervisor, "psutil", None)
    elif failure == "invalid_result":
        monkeypatch.setattr(adapter, "supervise", lambda *a: None)
    elif failure == "replay_mismatch":
        monkeypatch.setattr(adapter, "supervise", lambda *a: {"historical_decision": "ACCEPTED", "supplemental": "PASS"})
    elif failure in {"substitution", "incomplete"}:
        message = {"identity": "different", "decision": "PASS"} if failure == "substitution" else {"identity": "missing-decision"}
        monkeypatch.setattr(supervisor, "_verified_message", lambda _message, request_id: supervisor_message(message, request_id))
    else:
        real = supervisor.mp.get_context("spawn")
        class InterruptedContext:
            Pipe = staticmethod(real.Pipe)
            @staticmethod
            def Process(*args, **kwargs):
                process = real.Process(*args, **kwargs)
                class Proxy:
                    def start(self):
                        process.start()
                        process.terminate()
                    def __getattr__(self, name):
                        return getattr(process, name)
                return Proxy()
        monkeypatch.setattr(supervisor.mp, "get_context", lambda _method: InterruptedContext())
    with pytest.raises(NumericalConvergenceError) as error:
        route(csr_matrix(np.eye(2)), np.ones(2), np.zeros(2))
    diag = error.value.diagnostics["experimental_exact_residual_diagnostic"]
    assert diag["supplemental"] == "INCONCLUSIVE"
    assert diag["historical_decision"] == "REJECTED"
    if failure == "no_psutil":
        assert diag["historical_decision"] == "REJECTED"
        assert diag["supervisor_guard_replay_decision"] == "NOT_RUN"
        assert diag["reason"] == "PSUTIL_UNAVAILABLE"
    elif failure == "timeout":
        assert diag["reason"] == "TIMEOUT" and diag["child_exitcode"] is not None
    elif failure == "monitor":
        assert diag["reason"] == "MONITOR_ERROR" and diag["child_exitcode"] is not None
    elif failure == "interrupt":
        assert diag["child_exitcode"] not in (None, 0)
    elif failure == "invalid_result":
        assert diag["reason"] == "INVALID_SUPERVISOR_RESULT"
    elif failure == "replay_mismatch":
        assert diag["reason"] == "GUARD_REPLAY_MISMATCH"
    assert children() <= before


supervisor_message = supervisor._verified_message


def test_default_and_non_eas_routes_do_not_activate_diagnostic(route, monkeypatch):
    monkeypatch.setattr(adapter, "supervise", lambda *a, **k: pytest.fail("unexpected diagnostic"))
    for family in ("HEX8_EAS_EXPERIMENTAL", "HEX8"):
        with pytest.raises(NumericalConvergenceError) as error:
            route(csr_matrix(np.eye(2)), np.ones(2), np.zeros(2), enabled=False, family=family)
        assert "experimental_exact_residual_diagnostic" not in error.value.diagnostics


def test_nonfinite_candidate_remains_original_guard_error(route):
    before = children()
    with pytest.raises(NumericalConvergenceError, match="non-finite solution") as error:
        route(csr_matrix(np.eye(2)), np.ones(2), np.array([np.nan, 0.0]))
    assert error.value.diagnostics["experimental_exact_residual_diagnostic"]["supplemental"] == "INCONCLUSIVE"
    assert children() <= before
