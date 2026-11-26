"""Synthetic static result path; no FEM element assembly is performed."""
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest
from scipy.sparse import csr_matrix

import solveur.experimental.eas_residual.diagnostic_adapter as adapter
import solveur.core.solvers.static as static
from solveur.core.solvers import linear
from solveur.core.results import SolveResult


@pytest.mark.parametrize("enabled,family", [(True, "HEX8_EAS_EXPERIMENTAL"), (False, "HEX8_EAS_EXPERIMENTAL"), (False, "HEX8")])
def test_static_accepted_path_returns_result_and_calls_postprocessor(monkeypatch, enabled, family):
    solver = static.LinearStaticSolver()
    monkeypatch.setattr(adapter, "supervise", lambda *a, **k: pytest.fail("unexpected supplemental check"))
    monkeypatch.setattr(solver.validator, "validate", lambda model: SimpleNamespace(status="PASS"))
    monkeypatch.setattr(static, "emit_route_event_best_effort", lambda *a, **k: None)
    monkeypatch.setattr(solver.assembler, "prepare_plan", lambda *a: None)
    monkeypatch.setattr(solver.assembler, "assemble_stiffness", lambda *a, **k: csr_matrix(np.eye(2)))
    monkeypatch.setattr(solver.assembler, "assemble_loads", lambda *a: np.ones(2))
    monkeypatch.setattr(solver.assembler, "fixed_indices", lambda *a: np.array([], dtype=int))
    monkeypatch.setattr(solver.assembler, "ground_spring_internal_force", lambda *a: np.zeros(2))
    monkeypatch.setattr(linear, "spsolve", lambda *a, **k: np.ones(2))
    selection = SimpleNamespace(recommended_method="direct", to_dict=lambda **k: {})
    monkeypatch.setattr(static.LinearSolverPolicy, "assess", lambda *a: selection)
    monkeypatch.setattr(static.LinearSolverPolicy, "enforce_method_contract", lambda *a: None)
    monkeypatch.setattr(static, "select_backend", lambda *a, **k: SimpleNamespace(selected="scipy", fallback_used=False, to_dict=lambda: {}))
    reduction = SimpleNamespace(independent=np.arange(2), matrix=csr_matrix(np.eye(2)), rhs=np.ones(2),
                                expand=lambda x: x.copy(), transform=csr_matrix(np.eye(2)), diagnostics={})
    monkeypatch.setattr(static.ConstraintReduction, "from_system", lambda *a: reduction)
    monkeypatch.setattr(static, "recover_constraint_forces", lambda *a, **k: (np.zeros(2), np.zeros(2), {}))
    monkeypatch.setattr(static, "static_equilibrium_summary", lambda **k: {})
    monkeypatch.setattr("solveur.loads.integration.load_balance", lambda *a: (np.zeros(3), np.zeros(3)))
    monkeypatch.setattr(static.SolverAudit, "from_state", lambda **k: None)
    post = Mock(return_value=[{"stress": "synthetic"}])
    nodal = Mock(return_value=[{"node": 1}])
    monkeypatch.setattr(solver.post, "element_results", post)
    monkeypatch.setattr(solver.post, "nodal_results", nodal)
    monkeypatch.setattr(solver.post_auditor, "element_audits", lambda *a: [])
    model = SimpleNamespace(contacts=[], elements=[SimpleNamespace(type=family)],
                            analysis=SimpleNamespace(method="direct", parameters={"experimental_eas_exact_residual_diagnostic": enabled}),
                            dof_manager=lambda: SimpleNamespace(ndof=2), linear_constraints=lambda: [], node_count=2)
    result = solver.solve(model)
    assert isinstance(result, SolveResult) and result.status == "PASS"
    np.testing.assert_array_equal(result.displacements, np.ones(2))
    assert result.element_results == [{"stress": "synthetic"}] and result.nodal_results == [{"node": 1}]
    np.testing.assert_array_equal(post.call_args.args[2], result.displacements)
    nodal.assert_called_once()
