"""Structural regression test for safeguarded frictional-contact convergence."""

from __future__ import annotations

import numpy as np
import pytest

from solveur.contact import slip_root
from solveur.core.errors import NumericalConvergenceError
from solveur.core.solver import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader
from solveur.verification.frictionless_contact_structural import FrictionlessStructuralContactCampaign
from solveur.verification.tet4_total_lagrangian_assembly import _structured_tet4_mesh


def test_strongly_coupled_structural_sliding_converges_with_traced_root() -> None:
    """Use the declared active-slip fallback only when direct sliding oscillates."""
    nodes, elements = _structured_tet4_mesh(4, 2, 2, 1.0, 1.0, 1.0)
    nodes[:, 0] += 0.1
    structural_count = len(nodes)
    nodes = np.vstack((nodes, [[0.0, -1.0, -1.0], [0.0, 1.0, -1.0], [0.0, -1.0, 1.0]]))
    slave = FrictionlessStructuralContactCampaign._slave_node(nodes[:structural_count])
    data = FrictionlessStructuralContactCampaign._model_data(nodes, elements, structural_count, slave)
    data["analysis"] = {
        "type": "linear_static",
        "method": "direct",
        "contact_max_iterations": 25,
        "contact_friction_tolerance": 1.0e-10,
    }
    data["loads"] = [
        {"node": slave, "dof": "UX", "value": -4000.0},
        {"node": slave, "dof": "UZ", "value": 1500.0},
    ]
    data["contacts"] = [
        {
            "name": "rough_rigid_plane",
            "slave_node": slave,
            "master_nodes": [structural_count, structural_count + 1, structural_count + 2],
            "friction_coefficient": 0.4,
            "tangential_stiffness": 100000.0,
        }
    ]

    result = LinearStaticSolver().solve(JsonModelReader().from_dict(data))
    contact = result.solver["contact"]
    row = contact["contacts"][0]

    assert row["tangential_state"] == "slip"
    assert row["tangential_force_norm"] == pytest.approx(row["friction_limit"], rel=1.0e-8)
    assert any(item["strategy"] == "active_slip_root" for item in contact["history"])


def test_consistent_slip_fallback_recovers_when_hybrid_root_is_unavailable(monkeypatch) -> None:
    """A consistent active-branch Newton fallback follows a hybrid-root failure."""
    nodes, elements = _structured_tet4_mesh(4, 2, 2, 1.0, 1.0, 1.0)
    nodes[:, 0] += 0.1
    structural_count = len(nodes)
    nodes = np.vstack((nodes, [[0.0, -1.0, -1.0], [0.0, 1.0, -1.0], [0.0, -1.0, 1.0]]))
    slave = FrictionlessStructuralContactCampaign._slave_node(nodes[:structural_count])
    data = FrictionlessStructuralContactCampaign._model_data(nodes, elements, structural_count, slave)
    data["analysis"] = {"type": "linear_static", "method": "direct", "contact_max_iterations": 25}
    data["loads"] = [{"node": slave, "dof": "UX", "value": -4000.0}, {"node": slave, "dof": "UZ", "value": 1500.0}]
    data["contacts"] = [{
        "name": "rough_rigid_plane", "slave_node": slave,
        "master_nodes": [structural_count, structural_count + 1, structural_count + 2],
        "friction_coefficient": 0.4, "tangential_stiffness": 100000.0,
    }]

    class FailedRoot:
        success = False
        message = "forced hybrid failure"
        nfev = 1

        def __init__(self, vector: np.ndarray) -> None:
            self.x = vector

    monkeypatch.setattr(slip_root, "root", lambda _fun, vector, **_kwargs: FailedRoot(vector))
    result = LinearStaticSolver().solve(JsonModelReader().from_dict(data))
    history = result.solver["contact"]["history"]
    assert any(item["strategy"] == "active_slip_consistent_newton" for item in history)


def test_least_squares_slip_fallback_remains_available_after_newton_failure(monkeypatch) -> None:
    """Trust-region least squares remains the final recovery path."""
    nodes, elements = _structured_tet4_mesh(4, 2, 2, 1.0, 1.0, 1.0)
    nodes[:, 0] += 0.1
    structural_count = len(nodes)
    nodes = np.vstack((nodes, [[0.0, -1.0, -1.0], [0.0, 1.0, -1.0], [0.0, -1.0, 1.0]]))
    slave = FrictionlessStructuralContactCampaign._slave_node(nodes[:structural_count])
    data = FrictionlessStructuralContactCampaign._model_data(nodes, elements, structural_count, slave)
    data["analysis"] = {"type": "linear_static", "method": "direct", "contact_max_iterations": 25}
    data["loads"] = [{"node": slave, "dof": "UX", "value": -4000.0}, {"node": slave, "dof": "UZ", "value": 1500.0}]
    data["contacts"] = [{
        "name": "rough_rigid_plane", "slave_node": slave,
        "master_nodes": [structural_count, structural_count + 1, structural_count + 2],
        "friction_coefficient": 0.4, "tangential_stiffness": 100000.0,
    }]

    class FailedRoot:
        success = False
        message = "forced hybrid failure"
        nfev = 1

        def __init__(self, vector: np.ndarray) -> None:
            self.x = vector

    def failed_newton(*_args, **_kwargs):
        raise NumericalConvergenceError("forced Newton failure")

    monkeypatch.setattr(slip_root, "root", lambda _fun, vector, **_kwargs: FailedRoot(vector))
    monkeypatch.setattr(slip_root, "_semismooth_newton_solution", failed_newton)
    result = LinearStaticSolver().solve(JsonModelReader().from_dict(data))
    history = result.solver["contact"]["history"]
    assert any(item["strategy"] == "active_slip_least_squares" for item in history)


def test_semismooth_newton_uses_a_supplied_consistent_jacobian() -> None:
    """A caller-provided branch derivative avoids finite-difference assembly."""
    calls = 0

    def residual(vector: np.ndarray) -> np.ndarray:
        return np.array([vector[0] ** 2 - 4.0])

    def jacobian(vector: np.ndarray) -> np.ndarray:
        nonlocal calls
        calls += 1
        return np.array([[2.0 * vector[0]]])

    solution, _, residual_norm = slip_root._semismooth_newton_solution(
        residual,
        np.array([1.0]),
        1.0e-12,
        jacobian=jacobian,
    )

    assert solution[0] == pytest.approx(2.0)
    assert residual_norm <= 1.0e-12
    assert calls > 0
