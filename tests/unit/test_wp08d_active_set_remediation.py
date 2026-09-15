"""Targeted regression tests for WP08-D active-set recovery diagnostics."""

from __future__ import annotations

import numpy as np

from solveur.contact.support import _select_active_set_transition
from solveur.core.telemetry import EventType, MemorySink, TelemetryEmitter
from solveur.core.solver import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader
from solveur.verification.frictionless_contact_structural import FrictionlessStructuralContactCampaign
from solveur.verification.tet4_total_lagrangian_assembly import _structured_tet4_mesh


def _strongly_coupled_friction_model():
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
    data["contacts"] = [{
        "name": "rough_rigid_plane",
        "slave_node": slave,
        "master_nodes": [structural_count, structural_count + 1, structural_count + 2],
        "friction_coefficient": 0.4,
        "tangential_stiffness": 100000.0,
    }]
    return JsonModelReader().from_dict(data)


def test_active_set_cycle_uses_deterministic_single_contact_pivot() -> None:
    next_active, cause = _select_active_set_transition(
        (0, 1),
        (),
        {(0, 1), ()},
    )

    assert next_active == (1,)
    assert cause == "ACTIVE_SET_CYCLE_BROKEN"


def test_friction_route_emits_active_set_cause_and_step_outcome() -> None:
    sink = MemorySink()
    telemetry = TelemetryEmitter("wp08d-remediation", "linear_static", "linear_static", sink)

    result = LinearStaticSolver().solve(_strongly_coupled_friction_model(), telemetry=telemetry)

    assert result.status == "PASS"
    contact_events = [event for event in sink.events if event.event_type is EventType.CONTACT_STATE]
    assert contact_events
    assert all("convergence_cause" in event.metrics for event in contact_events)
    assert any(event.event_type is EventType.STEP_ACCEPTED for event in sink.events)
    assert any(event.metrics.get("strategy") == "active_slip_root" for event in contact_events)
