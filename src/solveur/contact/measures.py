"""Reference T3 tributary areas for bounded surface contact regularization."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import numpy as np

from solveur.core.errors import InputValidationError


def reference_surface_areas(
    nodes: np.ndarray,
    faces: Iterable[Sequence[int]],
) -> dict[int, float]:
    """Integrate each linear shape function: A_i = sum(T3 area / 3).

    Return weights for *all* face vertices. Selecting eligible contact nodes
    must not redistribute excluded vertices' area. Geometry is reference
    geometry, not the trial deformed surface; no updated-area claim is made.
    """
    coordinates = np.asarray(nodes, dtype=float)
    if coordinates.ndim != 2 or coordinates.shape[1] != 3 or not np.isfinite(coordinates).all():
        raise InputValidationError("Surface contact requires finite N-by-3 coordinates.")
    areas: dict[int, float] = {}
    seen: set[tuple[int, ...]] = set()
    for raw_face in faces:
        face = tuple(raw_face)
        if len(face) != 3 or any(isinstance(i, (bool, np.bool_)) or not isinstance(i, (int, np.integer)) for i in face):
            raise InputValidationError("Surface contact faces require three integer node indices.")
        if len(set(face)) != 3 or any(i < 0 or i >= len(coordinates) for i in face):
            raise InputValidationError("Surface contact face has repeated or nonexistent nodes.")
        marker = tuple(sorted(int(i) for i in face))
        if marker in seen:
            raise InputValidationError("Surface contact must not repeat a face, including reversed orientation.")
        seen.add(marker)
        xyz = coordinates[list(face)]
        area = 0.5 * float(np.linalg.norm(np.cross(xyz[1] - xyz[0], xyz[2] - xyz[0])))
        if not np.isfinite(area) or area <= 0.0:
            raise InputValidationError("Surface contact face must have finite positive area.")
        for i in face:
            areas[int(i)] = areas.get(int(i), 0.0) + area / 3.0
    if not areas or any(not np.isfinite(a) or a <= 0.0 for a in areas.values()):
        raise InputValidationError("Surface contact requires a nonempty positive-area T3 patch.")
    return areas
