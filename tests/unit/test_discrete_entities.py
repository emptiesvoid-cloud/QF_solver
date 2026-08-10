"""Mechanical and schema checks for springs and concentrated masses."""

from __future__ import annotations

import math

import numpy as np
import pytest

from solveur.core.assembler import GlobalAssembler
from solveur.core.model import FiniteElementModel
from solveur.core.router import AnalysisRouter
from solveur.io.json_reader import JsonModelReader
from solveur.io.model_writer import model_to_dict
from solveur.mesh.validation import MeshValidator


def _spring_mass_model(analysis: str | dict[str, object] = "linear_static") -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=[[0.0, 0.0, 0.0]],
        elements=[],
        materials={},
        springs=[
            {
                "node_a": 0,
                "dofs": ["UX", "UY", "UZ"],
                "stiffness": [1000.0, 4000.0, 9000.0],
            }
        ],
        concentrated_masses=[{"node": 0, "mass": 10.0}],
        loads=[{"node": 0, "dof": "UX", "value": 25.0}],
        analysis=analysis,
    )


def test_ground_spring_static_response_and_energy() -> None:
    model = _spring_mass_model()
    result = AnalysisRouter().solve(model)
    ux = result.displacements[result.dofs.index(0, "UX")]

    assert ux == pytest.approx(25.0 / 1000.0)
    stiffness = GlobalAssembler().assemble_stiffness(model, result.dofs)
    assert 0.5 * float(result.displacements @ stiffness @ result.displacements) == pytest.approx(
        0.5 * 1000.0 * ux**2
    )


def test_two_node_spring_has_opposed_forces_and_rigid_translation() -> None:
    model = FiniteElementModel.from_raw(
        nodes=[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
        elements=[],
        materials={},
        springs=[{"node_a": 0, "node_b": 1, "dofs": ["UX"], "stiffness": 1200.0}],
    )
    dofs = model.dof_manager()
    stiffness = GlobalAssembler().assemble_stiffness(model, dofs)
    rigid = np.ones(2)
    extension = np.array([0.0, 0.01])

    np.testing.assert_allclose(stiffness @ rigid, 0.0, atol=1.0e-12)
    np.testing.assert_allclose(stiffness @ extension, [-12.0, 12.0], atol=1.0e-12)


def test_local_directional_spring_rotates_into_global_axes() -> None:
    model = FiniteElementModel.from_raw(
        nodes=[[0.0, 0.0, 0.0]],
        elements=[],
        materials={},
        springs=[
            {
                "node_a": 0,
                "dofs": ["UX"],
                "stiffness": 500.0,
                "coordinate_system": "local",
                "orientation": [[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]],
            }
        ],
    )
    dofs = model.dof_manager()
    stiffness = GlobalAssembler().assemble_stiffness(model, dofs).toarray()

    assert dofs.ndof == 3
    np.testing.assert_allclose(np.diag(stiffness), [0.0, 500.0, 0.0], atol=1.0e-12)


def test_concentrated_mass_with_offset_builds_physical_spatial_inertia() -> None:
    model = FiniteElementModel.from_raw(
        nodes=[[0.0, 0.0, 0.0]],
        elements=[],
        materials={},
        springs=[{"node_a": 0, "dofs": list(("UX", "UY", "UZ", "RX", "RY", "RZ")), "stiffness": 1.0}],
        concentrated_masses=[
            {
                "node": 0,
                "mass": 2.0,
                "center_of_mass": [0.0, 0.5, 0.0],
                "inertia": [[0.3, 0.0, 0.0], [0.0, 0.2, 0.0], [0.0, 0.0, 0.3]],
            }
        ],
    )
    dofs = model.dof_manager()
    mass = GlobalAssembler().assemble_mass(model, dofs).toarray()

    np.testing.assert_allclose(mass, mass.T, atol=1.0e-12)
    np.testing.assert_allclose(np.diag(mass)[:3], [2.0, 2.0, 2.0], atol=1.0e-12)
    assert np.min(np.linalg.eigvalsh(mass)) > 0.0
    assert mass[dofs.index(0, "UX"), dofs.index(0, "RZ")] == pytest.approx(-1.0)


def test_spatial_mass_is_invariant_under_rigid_rotation_of_input_axes() -> None:
    angle = 0.63
    rotation = np.array(
        [
            [math.cos(angle), -math.sin(angle), 0.0],
            [math.sin(angle), math.cos(angle), 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    center = np.array([0.2, -0.1, 0.3])
    inertia = np.diag([0.4, 0.5, 0.6])

    def matrix(rotated: bool) -> np.ndarray:
        local_center = rotation @ center if rotated else center
        local_inertia = rotation @ inertia @ rotation.T if rotated else inertia
        model = FiniteElementModel.from_raw(
            nodes=[[0.0, 0.0, 0.0]],
            elements=[],
            materials={},
            springs=[{"node_a": 0, "dofs": list(("UX", "UY", "UZ", "RX", "RY", "RZ")), "stiffness": 1.0}],
            concentrated_masses=[
                {
                    "node": 0,
                    "mass": 3.0,
                    "center_of_mass": local_center.tolist(),
                    "inertia": local_inertia.tolist(),
                }
            ],
        )
        dofs = model.dof_manager()
        return GlobalAssembler().assemble_mass(model, dofs).toarray()

    transform = np.zeros((6, 6))
    transform[:3, :3] = rotation
    transform[3:, 3:] = rotation
    np.testing.assert_allclose(matrix(True), transform @ matrix(False) @ transform.T, atol=1.0e-12)


def test_spring_mass_frequency_matches_closed_form() -> None:
    model = _spring_mass_model({"type": "modal", "method": "eigh", "parameters": {"modes": 1}})
    result = AnalysisRouter().solve(model)
    expected = math.sqrt(1000.0 / 10.0) / (2.0 * math.pi)

    assert result.frequencies_hz[0] == pytest.approx(expected, rel=1.0e-12)
    assert result.solver["max_relative_residual"] < 1.0e-12


def test_discrete_entities_round_trip_through_strict_json() -> None:
    model = _spring_mass_model()
    restored = JsonModelReader().from_dict(model_to_dict(model))

    assert restored.springs == model.springs
    assert restored.concentrated_masses == model.concentrated_masses
    assert MeshValidator().validate(restored).status in {"PASS", "WARNING"}


@pytest.mark.parametrize(
    "payload, message",
    [
        (
            {"springs": [{"node_a": 0, "dofs": ["UX"], "stiffness": -1.0}]},
            "positive semidefinite",
        ),
        (
            {
                "springs": [{"node_a": 0, "dofs": ["UX"], "stiffness": 1.0}],
                "concentrated_masses": [
                    {
                        "node": 0,
                        "mass": 1.0,
                        "inertia": [[1.0, 2.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
                    }
                ],
            },
            "inertia must be symmetric",
        ),
    ],
)
def test_strict_schema_rejects_nonphysical_discrete_data(
    payload: dict[str, object],
    message: str,
) -> None:
    data: dict[str, object] = {
        "nodes": [[0.0, 0.0, 0.0]],
        "elements": [],
        "materials": {},
        **payload,
    }
    with pytest.raises(ValueError, match=message):
        JsonModelReader().from_dict(data)
