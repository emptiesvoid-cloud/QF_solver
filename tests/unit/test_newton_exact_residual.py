"""Synthetic tests of the Newton correction gate, with no FEM assembly."""

import os
from time import sleep
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from solveur.core.analyses.geometric_nonlinear import GeometricNonlinearStaticSolver
from solveur.core.analyses.settings import AnalysisSettings
from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.core.nonlinear.iteration import solve_full_newton
from solveur.core.nonlinear.linear_solver import NonlinearLinearSolverAdapter
from solveur.core.nonlinear.robustness import (
    NEWTON_EXACT_MAX_CHECKS_OPTION,
    NEWTON_EXACT_OPTION,
    NonlinearRobustnessOptions,
)
from solveur.core.nonlinear.state import NonlinearState
from solveur.core.router import AnalysisRouter
from solveur.experimental import newton_residual as exact
from solveur.experimental.eas_residual import bounded_exact_supervisor as supervisor

PARAMS = {"backend": "scipy", "residual_failure_tolerance": 1e-7}


def _bound_system():
    return csr_matrix([[1e9, -1e9], [0.0, 1.0]]), np.array([0.0, 1.0])


def _slow(pipe, *args):
    sleep(30)


def _interrupted(pipe, *args):
    os._exit(7)


def test_accepted_and_disabled_do_not_start_check(monkeypatch):
    def unexpected(*args):
        pytest.fail("Unexpected exact verification")

    monkeypatch.setattr(exact, "verify_candidate", unexpected)
    enabled = NonlinearLinearSolverAdapter(NonlinearRobustnessOptions(exact_residual=True))
    x, diagnostics = enabled.solve(csr_matrix(np.eye(2)), np.ones(2))
    np.testing.assert_array_equal(x, np.ones(2))
    assert diagnostics[NEWTON_EXACT_OPTION] == {
        "historical_decision": "ACCEPTED",
        "exact": {"status": "NOT_RUN"},
        "correction_authorized": True,
    }
    assert NonlinearRobustnessOptions.from_parameters({NEWTON_EXACT_OPTION: False}) is None
    with pytest.raises(NumericalConvergenceError) as failure:
        NonlinearLinearSolverAdapter().solve(*_bound_system())
    assert NEWTON_EXACT_OPTION not in failure.value.diagnostics


def test_exact_check_budget_is_default_eight_and_experimentally_bounded_at_24():
    default = NonlinearRobustnessOptions.from_parameters({NEWTON_EXACT_OPTION: True})
    assert default is not None and default.exact_residual_max_checks == 8

    extended = NonlinearRobustnessOptions.from_parameters(
        {NEWTON_EXACT_OPTION: True, NEWTON_EXACT_MAX_CHECKS_OPTION: 24}
    )
    assert extended is not None and extended.exact_residual_max_checks == 24
    assert NonlinearLinearSolverAdapter(extended)._exact_solver.max_checks == 24

    for invalid in (0, 25, None, True, 24.0, "24"):
        with pytest.raises(ValueError, match="integer from 1 to 24"):
            NonlinearRobustnessOptions.from_parameters(
                {NEWTON_EXACT_OPTION: True, NEWTON_EXACT_MAX_CHECKS_OPTION: invalid}
            )
    with pytest.raises(ValueError, match="requires"):
        NonlinearRobustnessOptions.from_parameters({NEWTON_EXACT_MAX_CHECKS_OPTION: 24})
    with pytest.raises(ValueError, match="requires"):
        NonlinearRobustnessOptions.from_parameters({NEWTON_EXACT_MAX_CHECKS_OPTION: 8})


def test_bound_pass_returns_original_without_refinement():
    adapter = NonlinearLinearSolverAdapter(NonlinearRobustnessOptions(exact_residual=True))
    x, diagnostics = adapter.solve(*_bound_system())
    np.testing.assert_array_equal(x, np.ones(2))
    report = diagnostics[NEWTON_EXACT_OPTION]
    assert report["historical_decision"] == "REJECTED_BOUND"
    assert report["historical_diagnostics"]["relative_residual_upper_bound"] > 1e-7
    assert report["exact"]["status"] == "PASS"
    assert report["correction_authorized"]


def test_cancellation_above_exact_threshold_preserves_rejection(monkeypatch):
    matrix = csr_matrix([[2.0**53, 1.0, -(2.0**53)], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    rhs = np.array([0.0, 1.0, 1.0])
    # Inject the suspect finite binary64 candidate. Sparse matvec loses the 1.
    monkeypatch.setattr("solveur.core.solvers.linear.spsolve", lambda *_: np.ones(3))
    adapter = NonlinearLinearSolverAdapter(NonlinearRobustnessOptions(exact_residual=True))
    with pytest.raises(NumericalConvergenceError) as failure:
        adapter.solve(matrix, rhs)
    report = failure.value.diagnostics[NEWTON_EXACT_OPTION]
    assert report["historical_decision"] == "REJECTED_BOUND"
    assert report["exact"]["status"] == "FAIL"
    assert not report["correction_authorized"]


def test_foreign_candidate_rejected_without_check(monkeypatch):
    a, b = _bound_system()
    # x belongs to the same A with b=[0, 1]; raise the first component of b.
    solver = exact.ExactNewtonLinearSolver()
    monkeypatch.setattr("solveur.core.solvers.linear.spsolve", lambda *_: np.ones(2))
    with pytest.raises(NumericalConvergenceError, match="residual is abnormal") as failure:
        solver.solve(a, b + [1e-6, 0], method="direct", parameters=PARAMS)
    assert solver.checks_used == 0
    assert failure.value.diagnostics[NEWTON_EXACT_OPTION]["exact"]["status"] == "NOT_RUN"


def test_identity_normalization_and_threshold_mismatch_refuse():
    candidate_id = "system_a"
    valid = {
        "identity": candidate_id,
        "normalization": exact.NORMALIZATION,
        "status": "PASS",
        "threshold_hex": exact.THRESHOLD.hex(),
        "dimension": 2,
        "stored_terms": 3,
        "relative_squared_hex": ["0x0", "0x1"],
    }
    assert exact._validated_response(valid, candidate_id, 2, 3)["status"] == "PASS"
    for change in (
        {"identity": "system_b"},
        {"normalization": "rhs_only"},
        {"threshold_hex": (1e-6).hex()},
        {"relative_squared_hex": ["0x1", "0x1"]},
        {"relative_squared_hex": ["0x0", "0x0"]},
    ):
        assert exact._validated_response({**valid, **change}, candidate_id, 2, 3)["status"] == "INCONCLUSIVE"
    with pytest.raises(ValueError, match="1e-7"):
        exact.ExactNewtonLinearSolver().solve(
            *_bound_system(), method="direct", parameters={**PARAMS, "residual_failure_tolerance": 1e-6}
        )


def test_real_child_timeout_preserves_rejection(monkeypatch):
    monkeypatch.setattr(exact, "TIMEOUT", 0.2)
    monkeypatch.setattr(exact, "_worker", _slow)
    with pytest.raises(NumericalConvergenceError) as failure:
        exact.ExactNewtonLinearSolver().solve(*_bound_system(), method="direct", parameters=PARAMS)
    result = failure.value.diagnostics[NEWTON_EXACT_OPTION]["exact"]
    assert result["status"] == "INCONCLUSIVE" and result["reason"] == "TIMEOUT"
    assert result["monitor"]["child_exitcode"] is not None


def test_real_child_abnormal_exit_preserves_rejection(monkeypatch):
    monkeypatch.setattr(exact, "_worker", _interrupted)
    with pytest.raises(NumericalConvergenceError) as failure:
        exact.ExactNewtonLinearSolver().solve(*_bound_system(), method="direct", parameters=PARAMS)
    result = failure.value.diagnostics[NEWTON_EXACT_OPTION]["exact"]
    assert result["status"] == "INCONCLUSIVE" and result["reason"] == "CHILD_EXIT_NONZERO"
    assert result["monitor"]["child_exitcode"] == 7


def test_missing_monitor_preserves_state_before_correction(monkeypatch):
    monkeypatch.setattr(supervisor, "psutil", None)
    a, b = _bound_system()

    class Assembly:
        ndof = 2

        def assemble(self, displacement, **kwargs):
            np.testing.assert_array_equal(displacement, np.zeros(2))
            return a @ displacement, a

    state = NonlinearState(np.zeros(2), material_state={"history": [1, 2]})
    before = state.digest
    with pytest.raises(NumericalConvergenceError) as failure:
        solve_full_newton(
            Assembly(),
            b,
            np.array([], dtype=int),
            increments=1,
            tolerance=1e-8,
            max_iterations=2,
            initial_state=state,
            robustness_options=NonlinearRobustnessOptions(exact_residual=True),
        )
    report = failure.value.diagnostics[NEWTON_EXACT_OPTION]
    assert report["exact"]["reason"] == "PSUTIL_UNAVAILABLE"
    assert not report["correction_authorized"]
    assert state.digest == before


def test_budget_persists_across_adapter_calls(monkeypatch):
    adapter = NonlinearLinearSolverAdapter(
        NonlinearRobustnessOptions(exact_residual=True, exact_residual_max_checks=1)
    )
    adapter.solve(*_bound_system())
    with pytest.raises(NumericalConvergenceError) as failure:
        adapter.solve(*_bound_system())
    assert adapter._exact_solver.checks_used == 1
    report = failure.value.diagnostics[NEWTON_EXACT_OPTION]
    assert report["exact"]["reason"] == "CHECK_BUDGET_EXHAUSTED"
    assert not report["correction_authorized"]
    next_call = NonlinearLinearSolverAdapter(adapter.options)
    assert next_call._exact_solver.checks_used == 0
    assert next_call._exact_solver.max_checks == 1


@pytest.mark.parametrize("budget", [8, 24])
def test_check_budget_is_shared_across_fixed_increments(monkeypatch, budget):
    a, b = _bound_system()
    replies = []
    accepted = []

    class Assembly:
        ndof = 2

        def assemble(self, displacement, *, tangent_required=True):
            return a @ displacement, a if tangent_required else None

    def run_worker(target, args, timeout, rss_limit):
        # Exercise the actual worker and response validation synchronously.
        target(SimpleNamespace(send=replies.append, close=lambda: None), *args)
        return replies[-1], {"reason": "CHILD_EXIT", "child_exitcode": 0}

    monkeypatch.setattr(exact, "_spawn_monitored", run_worker)
    state = NonlinearState(np.zeros(2))
    with pytest.raises(NumericalConvergenceError) as failure:
        solve_full_newton(
            Assembly(),
            32 * b,
            np.array([], dtype=int),
            increments=32,
            tolerance=1e-8,
            max_iterations=3,
            initial_state=state,
            robustness_options=NonlinearRobustnessOptions(exact_residual=True, exact_residual_max_checks=budget),
            accepted_state_callback=lambda step, snapshot: accepted.append(
                (step, snapshot.load_factor, snapshot.displacement.copy())
            ),
        )

    assert len(replies) == len(accepted) == budget
    assert all(reply["status"] == "PASS" for reply in replies)
    assert [step for step, _, _ in accepted] == list(range(1, budget + 1))
    assert accepted[-1][1] == budget / 32
    np.testing.assert_array_equal(accepted[-1][2], [float(budget), float(budget)])
    np.testing.assert_array_equal(state.displacement, [0.0, 0.0])
    report = failure.value.diagnostics[NEWTON_EXACT_OPTION]
    assert report["historical_decision"] == "REJECTED_BOUND"
    assert report["exact"]["reason"] == "CHECK_BUDGET_EXHAUSTED"
    assert not report["correction_authorized"]


def test_router_rejects_exact_opt_in_on_linear_static():
    model = SimpleNamespace(
        analysis=AnalysisSettings.from_raw({"type": "linear_static", "parameters": {NEWTON_EXACT_OPTION: True}})
    )
    with pytest.raises(InputValidationError, match="requires geometric_nonlinear_static"):
        AnalysisRouter().solve(model)


def test_router_rejects_check_budget_key_on_linear_static():
    model = SimpleNamespace(
        analysis=AnalysisSettings.from_raw(
            {
                "type": "linear_static",
                "parameters": {NEWTON_EXACT_MAX_CHECKS_OPTION: 8},
            }
        )
    )
    with pytest.raises(InputValidationError, match="experimental_newton_exact_residual_max_checks"):
        AnalysisRouter().solve(model)


def test_scope_rejects_incompatible_routes_before_assembly(monkeypatch):
    with pytest.raises(ValueError, match="unscaled"):
        NonlinearRobustnessOptions.from_parameters({NEWTON_EXACT_OPTION: True, "experimental_linear_solver": "cg"})
    with pytest.raises(ValueError, match="boolean"):
        NonlinearRobustnessOptions.from_parameters({NEWTON_EXACT_OPTION: "true"})
    monkeypatch.setattr(GeometricNonlinearStaticSolver, "_validate_scope", lambda *_: None)
    model = SimpleNamespace(
        analysis=SimpleNamespace(parameters={NEWTON_EXACT_OPTION: True, "adaptive_load_steps": True}),
        elements=[SimpleNamespace(type="TET10")],
        contacts=[],
    )
    with pytest.raises(InputValidationError, match="fixed-step"):
        GeometricNonlinearStaticSolver().solve(model)


def test_input_changed_after_check_is_not_authorized(monkeypatch):
    a, b = _bound_system()
    candidate = np.ones(2)

    def altered(target, args, timeout, rss_limit):
        arrays, shape, threshold, request_id = args
        assert arrays[3][0] == 0.0
        b[0] = 1e-6
        return (
            {
                "identity": request_id,
                "normalization": exact.NORMALIZATION,
                "status": "PASS",
                "threshold_hex": threshold.hex(),
                "dimension": shape[0],
                "stored_terms": a.nnz,
                "relative_squared_hex": ["0x0", "0x1"],
            },
            {"reason": "CHILD_EXIT", "child_exitcode": 0},
        )

    monkeypatch.setattr(exact, "_spawn_monitored", altered)
    result = exact.verify_candidate(a, b, candidate)
    assert result["status"] == "INCONCLUSIVE" and result["reason"] == "INPUT_CHANGED_DURING_CHECK"
    assert exact._validated_response(None, "no-reply", 2, 3)["status"] == "INCONCLUSIVE"


def test_sampled_rss_limit_terminates_real_child(monkeypatch):
    monkeypatch.setattr(exact, "RSS_LIMIT", 1024)
    monkeypatch.setattr(exact, "_worker", _slow)
    with pytest.raises(NumericalConvergenceError) as failure:
        exact.ExactNewtonLinearSolver().solve(*_bound_system(), method="direct", parameters=PARAMS)
    result = failure.value.diagnostics[NEWTON_EXACT_OPTION]["exact"]
    assert result["status"] == "INCONCLUSIVE" and result["reason"] == "SAMPLED_RSS_LIMIT"
    assert result["monitor"]["sampled_peak_rss_bytes"] > 1024
    assert result["monitor"]["child_exitcode"] is not None
