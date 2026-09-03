from __future__ import annotations

import copy

import numpy as np
import pytest

from solveur.compat.mitc4.element import MITC4Element

from solveur.api import solve_model
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel
from solveur.io.schema import JsonSchemaValidator
from solveur.materials.factory import MaterialFactory


COORDS = np.array(
    [[0.0, 0.0, 0.0], [1.2, 0.0, 0.0], [1.2, 0.8, 0.0], [0.0, 0.8, 0.0]]
)


def _definition(angle: float = 0.0) -> dict[str, object]:
    return {
        "type": "shell_laminate",
        "plies": [
            {
                "name": "ply-1",
                "E1": 135.0e9,
                "E2": 10.0e9,
                "nu12": 0.3,
                "G12": 5.0e9,
                "G13": 4.5e9,
                "G23": 3.8e9,
                "density": 1600.0,
                "thickness": 1.0e-2,
                "angle_deg": angle,
            }
        ],
    }


def test_projected_reference_direction_matches_equivalent_local_ply_angle():
    angle = np.deg2rad(30.0)
    projected = _definition(10.0)
    projected["reference_direction"] = [np.cos(angle), np.sin(angle), 0.0]
    local = _definition(40.0)

    projected_stiffness = MITC4Element(MaterialFactory.create(projected)).stiffness(COORDS)
    local_stiffness = MITC4Element(MaterialFactory.create(local)).stiffness(COORDS)

    assert np.allclose(projected_stiffness, local_stiffness, rtol=2.0e-13, atol=1.0e-5)


def test_reference_direction_is_objective_when_geometry_and_axis_rotate_together():
    definition = _definition(15.0)
    definition["reference_direction"] = [0.8, 0.6, 0.0]
    angle = np.deg2rad(37.0)
    rotation = np.array(
        [
            [np.cos(angle), 0.0, np.sin(angle)],
            [0.0, 1.0, 0.0],
            [-np.sin(angle), 0.0, np.cos(angle)],
        ]
    )
    rotated_definition = copy.deepcopy(definition)
    rotated_definition["reference_direction"] = (
        rotation @ np.asarray(definition["reference_direction"])
    ).tolist()

    reference = MITC4Element(MaterialFactory.create(definition)).stiffness(COORDS)
    rotated = MITC4Element(MaterialFactory.create(rotated_definition)).stiffness(
        COORDS @ rotation.T
    )

    assert np.allclose(
        np.linalg.eigvalsh(reference),
        np.linalg.eigvalsh(rotated),
        rtol=2.0e-10,
        atol=1.0e-4,
    )


def test_parallel_reference_direction_is_rejected_on_the_affected_facet():
    definition = _definition()
    definition["reference_direction"] = [0.0, 0.0, 1.0]
    with pytest.raises(ValueError, match="parallel to the shell normal"):
        MITC4Element(MaterialFactory.create(definition)).stiffness(COORDS)


def test_schema_rejects_zero_laminate_reference_direction():
    definition = _definition()
    definition["reference_direction"] = [0.0, 0.0, 0.0]
    raw = {
        "nodes": COORDS.tolist(),
        "elements": [{"type": "MITC4", "nodes": [0, 1, 2, 3], "material": "laminate"}],
        "materials": {"laminate": definition},
    }
    with pytest.raises(InputValidationError, match="non-zero norm"):
        JsonSchemaValidator().validate(raw)


def test_postprocessing_reports_projected_material_axes():
    definition = _definition(20.0)
    definition["reference_direction"] = [1.0, 1.0, 0.0]
    model = FiniteElementModel.from_raw(
        nodes=COORDS,
        elements=[{"type": "MITC4", "nodes": [0, 1, 2, 3], "material": "laminate"}],
        materials={"laminate": definition},
        fixed_dofs=[
            {"node": node, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]}
            for node in (0, 3)
        ],
        loads=[
            {"node": 1, "dof": "UX", "value": 1000.0},
            {"node": 2, "dof": "UX", "value": 1000.0},
        ],
    )
    result = solve_model(model)
    element = result.element_results[0]

    assert element["material_angle_offset_deg"] == pytest.approx(45.0)
    assert np.allclose(
        element["material_reference_direction"],
        [np.sqrt(0.5), np.sqrt(0.5), 0.0],
    )
    direction = np.asarray(element["ply_directions_global"][0])
    expected = np.array([np.cos(np.deg2rad(65.0)), np.sin(np.deg2rad(65.0)), 0.0])
    assert np.allclose(direction, expected)
