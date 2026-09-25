"""Tests for area-weighted penalty integration on explicit contact patches."""

from __future__ import annotations

import numpy as np
import pytest

from solveur.contact.solver import assemble_penalty_contact
from solveur.core.dofs import DofManager
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel


PENALTY = 1.0e8


def _patch_model(integration: str | None = None) -> FiniteElementModel:
    parameters = {} if integration is None else {"contact_penalty_integration": integration}
    return FiniteElementModel.from_raw(
        nodes=[
            [0.0, 0.0, 0.1],
            [2.0, 0.0, 0.1],
            [0.0, 1.0, 0.1],
            [2.0, 1.0, 0.1],
            [0.0, 0.0, 0.0],
            [4.0, 0.0, 0.0],
            [0.0, 2.0, 0.0],
        ],
        elements=[],
        materials={},
        contacts=[
            {
                "name": "two_triangle_slave_patch",
                "slave_nodes": [0, 1, 2, 3],
                "slave_patch_faces": [[0, 1, 2], [1, 3, 2]],
                "master_nodes": [4, 5, 6],
            }
        ],
        analysis={
            "type": "linear_static",
            "method": "direct",
            "parameters": parameters,
        },
    )


def _penetrating_displacement(model: FiniteElementModel) -> tuple[DofManager, np.ndarray]:
    dofs = model.dof_manager()
    displacement = np.zeros(dofs.ndof, dtype=float)
    for node in (0, 1, 2, 3):
        displacement[dofs.index(node, "UZ")] = -0.2
    return dofs, displacement


def test_surface_lumped_penalty_uses_normalized_slave_tributary_areas() -> None:
    model = _patch_model("surface_lumped")
    dofs, displacement = _penetrating_displacement(model)

    internal, tangent, details = assemble_penalty_contact(model, dofs, displacement, penalty=PENALTY)

    weights = np.array([1.0 / 6.0, 1.0 / 3.0, 1.0 / 3.0, 1.0 / 6.0])
    effective = PENALTY * weights
    np.testing.assert_allclose(details["penalty_integration_weights"], weights, rtol=0.0, atol=1.0e-15)
    np.testing.assert_allclose(details["effective_penalties"], effective, rtol=0.0, atol=1.0e-8)
    assert details["penalty_integration"] == "surface_lumped"
    for node, local_penalty in zip((0, 1, 2, 3), effective, strict=True):
        assert internal[dofs.index(node, "UZ")] == pytest.approx(local_penalty * -0.1)
        assert tangent[dofs.index(node, "UZ"), dofs.index(node, "UZ")] == pytest.approx(local_penalty)


def test_surface_lumped_penalty_tangent_matches_finite_difference() -> None:
    model = _patch_model("surface_lumped")
    dofs, displacement = _penetrating_displacement(model)
    _, tangent, _ = assemble_penalty_contact(model, dofs, displacement, penalty=PENALTY)
    step = 1.0e-6
    numerical = np.zeros((dofs.ndof, dofs.ndof), dtype=float)

    for column in range(dofs.ndof):
        perturbation = np.zeros(dofs.ndof, dtype=float)
        perturbation[column] = step
        plus = assemble_penalty_contact(model, dofs, displacement + perturbation, penalty=PENALTY)[0]
        minus = assemble_penalty_contact(model, dofs, displacement - perturbation, penalty=PENALTY)[0]
        numerical[:, column] = (plus - minus) / (2.0 * step)

    np.testing.assert_allclose(tangent.toarray(), numerical, rtol=1.0e-9, atol=1.0e-2)


def test_default_and_explicit_nodal_penalty_preserve_legacy_per_node_stiffness() -> None:
    default_model = _patch_model()
    explicit_model = _patch_model("nodal")
    default_dofs, default_displacement = _penetrating_displacement(default_model)
    explicit_dofs, explicit_displacement = _penetrating_displacement(explicit_model)

    default_internal, default_tangent, default_details = assemble_penalty_contact(
        default_model, default_dofs, default_displacement, penalty=PENALTY
    )
    explicit_internal, explicit_tangent, explicit_details = assemble_penalty_contact(
        explicit_model, explicit_dofs, explicit_displacement, penalty=PENALTY
    )

    np.testing.assert_array_equal(default_internal, explicit_internal)
    np.testing.assert_array_equal(default_tangent.toarray(), explicit_tangent.toarray())
    np.testing.assert_array_equal(default_details["effective_penalties"], [PENALTY] * 4)
    assert default_details["penalty_integration"] == "nodal"
    assert explicit_details["penalty_integration"] == "nodal"


def test_surface_lumped_penalty_requires_explicit_slave_faces() -> None:
    model = _patch_model("surface_lumped")
    model.contacts[0] = model.contacts[0].__class__(
        slave_node=model.contacts[0].slave_node,
        master_nodes=model.contacts[0].master_nodes,
        slave_patch_nodes=model.contacts[0].slave_patch_nodes,
    )
    dofs, displacement = _penetrating_displacement(model)

    with pytest.raises(InputValidationError, match="slave_patch_faces"):
        assemble_penalty_contact(model, dofs, displacement, penalty=PENALTY)


def test_parser_retains_slave_patch_faces_for_contact_assembly() -> None:
    model = _patch_model("surface_lumped")

    assert model.contacts[0].slave_patch_faces == ((0, 1, 2), (1, 3, 2))
