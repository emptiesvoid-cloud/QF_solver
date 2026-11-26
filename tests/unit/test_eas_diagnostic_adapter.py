import numpy as np
import pytest
from scipy.sparse import csr_matrix

from solveur.experimental.eas_residual.diagnostic_adapter import DiagnosticLinearSolver
from solveur.core.errors import NumericalConvergenceError
from solveur.core.solvers import linear
from solveur.core.solvers.static import LinearStaticSolver
from types import SimpleNamespace


def test_accepted_guard_is_unchanged():
    solver = DiagnosticLinearSolver()
    solution, info = solver.solve(csr_matrix(np.eye(2)), np.ones(2), method="direct")
    np.testing.assert_array_equal(solution, np.ones(2))
    assert info.converged and solver.last_diagnostic is None


def test_rejected_guard_remains_rejected_even_when_exact_passes(monkeypatch):
    matrix = csr_matrix(np.array([[1e16, 1e16], [1e16, 1e16 + 2.0]]))
    rhs = np.array([0.0, -2.0])
    monkeypatch.setattr(linear, "spsolve", lambda *_a, **_k: np.array([1.0, -1.0]))
    solver = DiagnosticLinearSolver()
    with pytest.raises(NumericalConvergenceError) as error:
        solver.solve(matrix, rhs, method="direct")
    assert error.value.diagnostics["experimental_exact_residual_diagnostic"]["supplemental"] == "PASS"
    assert error.value.diagnostics["experimental_exact_residual_diagnostic"]["historical_decision"] == "REJECTED"


def test_diagnostic_failure_does_not_replace_rejection(monkeypatch):
    monkeypatch.setattr(linear, "spsolve", lambda *_a, **_k: np.zeros(2))
    def fail(*_args, **_kwargs):
        raise RuntimeError("diagnostic failed")
    monkeypatch.setattr("solveur.experimental.eas_residual.diagnostic_adapter.supervise", fail)
    with pytest.raises(NumericalConvergenceError) as error:
        DiagnosticLinearSolver().solve(csr_matrix(np.eye(2)), np.ones(2), method="direct")
    assert error.value.diagnostics["experimental_exact_residual_diagnostic"]["supplemental"] == "INCONCLUSIVE"


def test_rejected_guard_and_exact_fail(monkeypatch):
    monkeypatch.setattr(linear, "spsolve", lambda *_a, **_k: np.zeros(2))
    with pytest.raises(NumericalConvergenceError) as error:
        DiagnosticLinearSolver().solve(csr_matrix(np.eye(2)), np.ones(2), method="direct")
    assert error.value.diagnostics["experimental_exact_residual_diagnostic"]["supplemental"] == "FAIL"


def test_static_route_activation_is_explicit_and_restricted(monkeypatch):
    created = []
    monkeypatch.setattr("solveur.experimental.eas_residual.diagnostic_adapter.DiagnosticLinearSolver", lambda: created.append(True))
    solver = LinearStaticSolver()
    def stop(_model):
        raise RuntimeError("stop before FEM")
    monkeypatch.setattr(solver.validator, "validate", stop)
    model = SimpleNamespace(contacts=[], elements=[SimpleNamespace(type="HEX8_EAS_EXPERIMENTAL")],
                            analysis=SimpleNamespace(parameters={}))
    with pytest.raises(RuntimeError, match="stop before FEM"):
        solver.solve(model)
    assert not created
    model.analysis.parameters = {"experimental_eas_exact_residual_diagnostic": True}
    with pytest.raises(RuntimeError, match="stop before FEM"):
        solver.solve(model)
    assert created == [True]
    model.elements[0].type = "HEX8"
    with pytest.raises(ValueError, match="EAS-only"):
        solver.solve(model)
