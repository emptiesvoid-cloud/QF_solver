from __future__ import annotations

import numpy as np
import pytest
from dataclasses import replace

from solveur.api import solve_model
from solveur.contact.solver import assemble_penalty_contact
from solveur.io.json_reader import JsonModelReader
from solveur.contact.entities import FrictionlessContact
from solveur.core.errors import InputValidationError
from solveur.verification.robustness_nonlinear_solids import (
    _refinement_model,
    run_contact_recontact_benchmark,
    run_contact_updated_sliding_benchmark,
)


def _contact_model():
    return JsonModelReader().from_dict(
        {
            "analysis": {"type": "linear_static", "method": "direct"},
            "nodes": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.25, 0.25, 0.1]],
            "elements": [],
            "materials": {},
            "fixed_dofs": [],
            "loads": [],
            "springs": [{"node_a": 3, "dofs": ["UZ"], "stiffness": 1000.0}],
            "contacts": [{"name": "plane", "slave_node": 3, "master_nodes": [0, 1, 2]}],
        }
    )


def test_penalty_contact_is_sparse_and_unilateral() -> None:
    model = _contact_model()
    dofs = model.dof_manager()
    separated = np.zeros(dofs.ndof)
    internal_open, tangent_open, details_open = assemble_penalty_contact(
        model, dofs, separated, penalty=1.0e6
    )
    penetrating = separated.copy()
    penetrating[dofs.index(3, "UZ")] = -0.2
    internal_closed, tangent_closed, details_closed = assemble_penalty_contact(
        model, dofs, penetrating, penalty=1.0e6
    )

    assert np.allclose(internal_open, 0.0)
    assert tangent_open.nnz == 0
    assert details_open["active_contacts"] == []
    assert np.linalg.norm(internal_closed) > 0.0
    assert tangent_closed.nnz > 0
    assert details_closed["active_contacts"] == [0]
    assert details_closed["formulation"] == "frictionless_penalty"
    assert details_closed["maximum_penetration"] == 0.1
    assert details_closed["contact_force_norm"] > 0.0
    assert details_closed["tangent_nnz"] == tangent_closed.nnz


def test_penalty_contact_tangent_matches_finite_difference() -> None:
    model = _contact_model()
    dofs = model.dof_manager()
    displacement = np.zeros(dofs.ndof)
    displacement[dofs.index(3, "UZ")] = -0.2
    _, tangent, _ = assemble_penalty_contact(model, dofs, displacement, penalty=1.0e6)

    # A larger centered-difference step avoids cancellation against the
    # 1e6 penalty stiffness while retaining the local tangent check.
    step = 1.0e-4
    numerical = np.zeros((dofs.ndof, dofs.ndof))
    for column in range(dofs.ndof):
        perturbation = np.zeros(dofs.ndof)
        perturbation[column] = step
        plus = assemble_penalty_contact(model, dofs, displacement + perturbation, penalty=1.0e6)[0]
        minus = assemble_penalty_contact(model, dofs, displacement - perturbation, penalty=1.0e6)[0]
        numerical[:, column] = (plus - minus) / (2.0 * step)

    np.testing.assert_allclose(tangent.toarray(), numerical, rtol=1.0e-10, atol=1.0e-6)


@pytest.mark.parametrize("value", [True, "invalid", 0.0, -1.0])
def test_penalty_contact_rejects_invalid_penetration_limit(value: object) -> None:
    model = _contact_model()
    model.analysis = replace(model.analysis, parameters={"contact_max_penetration": value})
    dofs = model.dof_manager()

    with pytest.raises(InputValidationError, match="contact_max_penetration"):
        assemble_penalty_contact(model, dofs, np.zeros(dofs.ndof), penalty=1.0e6)


def test_nonlinear_penalty_contact_uses_the_common_newton_driver() -> None:
    model = _refinement_model("TET4", 1)
    model.contacts.append(FrictionlessContact(slave_node=1, master_nodes=(0, 3, 4)))
    model.analysis = replace(
        model.analysis,
        parameters={
            **model.analysis.parameters,
            "contact_mode": "penalty",
            "contact_penalty": 1.0e6,
            "load_steps": 2,
        },
    )

    result = solve_model(model, enforce_policy=False)

    assert result.status == "PASS"
    assert result.solver["steps"][-1]["relative_residual"] < 1.0e-7
    assert result.solver["contact_mode"] == "penalty"
    assert all("contact_tangent_nnz" in step for step in result.solver["steps"])


def test_finite_kinematic_j2_and_penalty_contact_share_the_common_driver() -> None:
    model = _refinement_model("TET4", 1)
    model.contacts.append(FrictionlessContact(slave_node=1, master_nodes=(0, 3, 4)))
    model.analysis = replace(
        model.analysis,
        parameters={
            **model.analysis.parameters,
            "kinematics": "total_lagrangian_j2",
            "contact_mode": "penalty",
            "contact_penalty": 1.0e6,
            "load_steps": 2,
        },
    )

    result = solve_model(model, enforce_policy=False)

    assert result.status == "PASS"
    assert result.solver["kinematics"] == "total_lagrangian_j2"
    assert result.solver["contact_mode"] == "penalty"
    assert result.solver["steps"][-1]["relative_residual"] < 1.0e-7


def test_common_penalty_contact_can_update_the_geometry_each_iteration() -> None:
    model = _refinement_model("TET4", 1)
    model.contacts.append(FrictionlessContact(slave_node=1, master_nodes=(0, 3, 4)))
    model.analysis = replace(
        model.analysis,
        parameters={
            **model.analysis.parameters,
            "contact_mode": "penalty",
            "contact_search_mode": "updated",
            "contact_penalty": 1.0e6,
            "load_steps": 2,
        },
    )

    result = solve_model(model, enforce_policy=False)

    assert result.status == "PASS"
    assert result.solver["contact_mode"] == "penalty"
    assert result.solver["steps"][-1]["relative_residual"] < 1.0e-7


def test_common_penalty_contact_records_recontact_load_path() -> None:
    summary = run_contact_recontact_benchmark()

    assert summary["status"] == "PASS_INTERNAL_RESEARCH"
    assert summary["active_by_step"] == [False, True, False, True]
    assert summary["expected_active_by_step"] == summary["active_by_step"]
    assert summary["maximum_relative_residual"] <= 1.0e-7


def test_updated_contact_campaign_records_a_bounded_face_crossing() -> None:
    summary = run_contact_updated_sliding_benchmark()

    assert summary["status"] == "PASS_INTERNAL_RESEARCH"
    assert summary["common_driver"] is True
    assert summary["face_sequence"] == [[0], [0], [1], [1]]
    assert summary["face_switch_count"] == 1
    assert summary["maximum_relative_residual"] < 1.0e-7
