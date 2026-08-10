"""Small validation helpers shared by the mesh validation workflow."""

from __future__ import annotations

import numpy as np

from mitc4.element import MITC4Element

from solveur.core.model import FiniteElementModel
from solveur.elements.shell.mitc3 import Mitc3ShellElement
from solveur.loads.entities import BodyLoad, EdgeLoad, GravityLoad, SurfaceLoad


def shell_node_directors(model: FiniteElementModel) -> dict[int, np.ndarray]:
    """Average area-weighted shell directors at connected nodes."""
    weighted: dict[int, np.ndarray] = {}
    for definition in model.elements:
        if definition.type not in {"MITC3", "MITC4"}:
            continue
        coords = model.nodes[list(definition.nodes)]
        if definition.type == "MITC3":
            frame = Mitc3ShellElement.local_frame(coords)
            weight = max(
                float(
                    np.linalg.norm(
                        np.cross(coords[1] - coords[0], coords[2] - coords[0])
                    )
                ),
                1.0e-30,
            )
        else:
            frame = MITC4Element.local_frame(coords)
            weight = max(
                float(
                    np.linalg.norm(
                        np.cross(coords[2] - coords[0], coords[3] - coords[1])
                    )
                ),
                1.0e-30,
            )
        for node in definition.nodes:
            weighted[int(node)] = (
                weighted.get(int(node), np.zeros(3)) + weight * frame[2]
            )
    directors: dict[int, np.ndarray] = {}
    for node, value in weighted.items():
        norm = float(np.linalg.norm(value))
        if norm > 1.0e-14:
            directors[node] = value / norm
    return directors


def distributed_target_elements(
    load: GravityLoad | BodyLoad,
    element_count: int,
    path: str,
    errors: list[str],
) -> tuple[int, ...]:
    """Validate and return the elements selected by a volume/body load."""
    targets = tuple(range(element_count)) if load.elements is None else load.elements
    if not isinstance(targets, tuple) or not targets:
        errors.append(f"{path}: elements must select at least one element.")
        return ()
    valid: list[int] = []
    for element_index in targets:
        if not valid_element_index(element_index, element_count):
            errors.append(f"{path}: invalid target element {element_index!r}.")
        else:
            valid.append(int(element_index))
    if len(valid) != len(set(valid)):
        errors.append(f"{path}: target elements contain duplicates.")
    return tuple(valid)


def distributed_element_indices(load: object, element_count: int) -> tuple[int, ...]:
    if isinstance(load, (GravityLoad, BodyLoad)):
        return tuple(range(element_count)) if load.elements is None else load.elements
    if isinstance(load, (SurfaceLoad, EdgeLoad)):
        return (load.element,)
    return ()


def valid_element_index(value: object, element_count: int) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and 0 <= value < element_count
    )


def is_finite_scalar(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and np.isfinite(float(value))
    )


def is_finite_vector3(value: object) -> bool:
    try:
        vector = np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        return False
    return vector.shape == (3,) and bool(np.all(np.isfinite(vector)))


def finite_float_or_nan(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")
