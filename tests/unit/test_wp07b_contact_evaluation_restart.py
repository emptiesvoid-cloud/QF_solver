"""WP07-B contracts for pure penalty evaluation and bounded restart metadata."""

from dataclasses import replace

import numpy as np
import pytest

from solveur.contact.evaluation import (
    ACTIVE_SET_MIDSOLVE_RESTART,
    ContactEvaluation,
    PenaltyContactRestartMetadata,
    UPDATED_SEARCH_RESTART,
    contact_configuration_digest,
    evaluate_penalty_contact,
    reject_active_set_mid_solve_restart,
    updated_search_restart_status,
    validate_penalty_contact_restart_metadata,
)
from solveur.contact.solver import assemble_penalty_contact
from solveur.core.dofs import DofManager
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel
from solveur.io.json_reader import JsonModelReader


def _contact_model() -> FiniteElementModel:
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


def _displacements(model: FiniteElementModel) -> tuple[DofManager, np.ndarray, np.ndarray]:
    dofs = model.dof_manager()
    u0 = np.zeros(dofs.ndof)
    u1 = u0.copy()
    u1[dofs.index(3, "UZ")] = -0.2
    return dofs, u0, u1


def _assert_evaluation_equal(first: ContactEvaluation, second: ContactEvaluation) -> None:
    np.testing.assert_array_equal(first.internal_force, second.internal_force)
    np.testing.assert_array_equal(first.tangent.toarray(), second.tangent.toarray())
    assert first.active_contacts == second.active_contacts
    np.testing.assert_array_equal(first.gaps, second.gaps)
    for key in (
        "master_face_indices",
        "normals",
        "search_mode",
        "finite_sliding",
        "contact_active_count",
        "contact_minimum_gap",
        "contact_maximum_penetration",
        "contact_force_norm",
        "contact_tangent_nnz",
        "contact_search_mode",
    ):
        assert first.details[key] == second.details[key]


def test_b1_same_trial_u_is_a_deterministic_contact_evaluation() -> None:
    model = _contact_model()
    dofs, _, trial = _displacements(model)

    first = evaluate_penalty_contact(model, dofs, trial, penalty=1.0e6)
    second = evaluate_penalty_contact(model, dofs, trial, penalty=1.0e6)

    _assert_evaluation_equal(first, second)
    assert first.diagnostics["contact_active_count"] == 1
    assert first.diagnostics["contact_search_mode"] == "initial"


def test_b2_discarded_trial_does_not_contaminate_re_evaluation() -> None:
    model = _contact_model()
    dofs, accepted, trial = _displacements(model)

    before = tuple(model.contacts)
    first = evaluate_penalty_contact(model, dofs, accepted, penalty=1.0e6)
    evaluate_penalty_contact(model, dofs, trial, penalty=1.0e6)
    restored = evaluate_penalty_contact(model, dofs, accepted, penalty=1.0e6)

    _assert_evaluation_equal(first, restored)
    assert tuple(model.contacts) == before


def test_b3_contact_configuration_digest_is_deterministic() -> None:
    first = _contact_model()
    second = _contact_model()

    assert contact_configuration_digest(first, penalty=1.0e6) == contact_configuration_digest(second, penalty=1.0e6)


def test_b4_topology_change_changes_contact_configuration_digest() -> None:
    original = _contact_model()
    changed = _contact_model()
    changed.contacts[0] = replace(changed.contacts[0], master_nodes=(0, 2, 1))

    assert contact_configuration_digest(original, penalty=1.0e6) != contact_configuration_digest(changed, penalty=1.0e6)


def test_b5_compatible_penalty_restart_metadata_is_accepted() -> None:
    model = _contact_model()
    metadata = PenaltyContactRestartMetadata.from_model(
        model,
        penalty=1.0e6,
        accepted_state_digest="accepted-state-001",
    )
    restored = validate_penalty_contact_restart_metadata(
        metadata.to_dict(),
        model,
        penalty=1.0e6,
    )

    assert restored == metadata


def test_b6_incompatible_penalty_restart_metadata_fails_closed() -> None:
    model = _contact_model()
    changed = _contact_model()
    changed.contacts[0] = replace(changed.contacts[0], gap_tolerance=1.0e-8)
    metadata = PenaltyContactRestartMetadata.from_model(model, penalty=1.0e6)

    with pytest.raises(InputValidationError, match="incompatible"):
        metadata.validate_compatible(changed, penalty=1.0e6)


def test_b7_active_set_mid_solve_restart_remains_unsupported() -> None:
    assert ACTIVE_SET_MIDSOLVE_RESTART == "UNSUPPORTED"
    with pytest.raises(InputValidationError, match="MID_SOLVE_ACTIVE_SET_RESTART"):
        reject_active_set_mid_solve_restart()


def test_b8_updated_search_restart_is_unqualified() -> None:
    assert UPDATED_SEARCH_RESTART == "UNQUALIFIED_RESTART"
    assert updated_search_restart_status() == UPDATED_SEARCH_RESTART


def test_b9_evaluation_wrapper_preserves_common_penalty_composition() -> None:
    model = _contact_model()
    dofs, _, trial = _displacements(model)
    legacy_force, legacy_tangent, legacy_details = assemble_penalty_contact(
        model,
        dofs,
        trial,
        penalty=1.0e6,
    )
    evaluation = evaluate_penalty_contact(model, dofs, trial, penalty=1.0e6)

    np.testing.assert_array_equal(evaluation.internal_force, legacy_force)
    np.testing.assert_array_equal(evaluation.tangent.toarray(), legacy_tangent.toarray())
    assert evaluation.details["active_contacts"] == legacy_details["active_contacts"]
    assert list(evaluation.details["gaps"]) == list(legacy_details["gaps"])
    assert evaluation.details["contact_tangent_nnz"] == legacy_details["tangent_nnz"]


def test_b10_legacy_and_normalized_contact_diagnostics_are_both_available() -> None:
    model = _contact_model()
    dofs, _, trial = _displacements(model)
    evaluation = evaluate_penalty_contact(model, dofs, trial, penalty=1.0e6)

    for key in (
        "formulation",
        "search_mode",
        "active_contacts",
        "gaps",
        "master_face_indices",
        "maximum_penetration",
        "contact_force_norm",
        "tangent_nnz",
    ):
        assert key in evaluation.details
    for key in (
        "contact_active_count",
        "contact_minimum_gap",
        "contact_maximum_penetration",
        "contact_force_norm",
        "contact_tangent_nnz",
        "contact_search_mode",
    ):
        assert key in evaluation.diagnostics
