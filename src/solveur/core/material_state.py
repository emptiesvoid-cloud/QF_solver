"""Path-dependent material state storage for nonlinear analyses."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from solveur.core.model import FiniteElementModel
from solveur.elements.registry import ElementRegistry
from solveur.materials.factory import MaterialFactory


MaterialStateTable = dict[int, list[dict[str, Any]]]


def initial_material_states(model: FiniteElementModel) -> MaterialStateTable:
    """Create empty integration-point states for path-dependent materials."""
    table: MaterialStateTable = {}
    for index, definition in enumerate(model.elements):
        material = MaterialFactory.create(model.materials[definition.material])
        if not hasattr(material, "initial_state"):
            continue
        element = ElementRegistry.get(definition.type).factory(material)
        count = int(getattr(element, "integration_point_count", 0))
        if count > 0:
            table[index] = [deepcopy(material.initial_state()) for _ in range(count)]
    return table


def copy_material_states(states: MaterialStateTable | None) -> MaterialStateTable:
    """Return a detached copy safe for trial Newton iterations."""
    return deepcopy(states or {})


def commit_material_states(target: MaterialStateTable, source: MaterialStateTable) -> None:
    """Replace committed states with converged trial states."""
    target.clear()
    target.update(copy_material_states(source))


def material_states_to_dict(states: MaterialStateTable | None) -> list[dict[str, Any]]:
    """Serialize integration-point material states for result JSON."""
    rows: list[dict[str, Any]] = []
    for element_index in sorted((states or {}).keys()):
        points = []
        for point_index, state in enumerate(states[element_index]):
            points.append({"index": point_index, **_jsonable_state(state)})
        rows.append({"element": element_index, "integration_points": points})
    return rows


def _jsonable_state(state: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in state.items():
        if isinstance(value, (bool, str)):
            output[key] = value
        elif isinstance(value, (int, float)):
            output[key] = float(value)
        elif isinstance(value, list):
            output[key] = [float(item) if isinstance(item, (int, float)) else item for item in value]
    return output
