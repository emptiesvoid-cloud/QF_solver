"""HEX-specific mesh validation helpers."""

from __future__ import annotations

from typing import Any

import numpy as np

from solveur.elements.solid.hex20 import Hex20Element
from solveur.elements.solid.hex8 import Hex8Element
from solveur.mesh.quality import MeshQuality


def quality_details(
    index: int, element_type: str, coords: np.ndarray
) -> tuple[dict[str, Any], list[str]] | None:
    """Return quality details for HEX20, or ``None`` for other element families."""
    if element_type != "HEX20":
        return None
    metrics = MeshQuality.hex20_metrics(coords)
    warnings: list[str] = []
    if metrics["mid_edge_deviation_ratio_max"] > 5.0e-2:
        warnings.append(
            f"Element {index}: curved or misplaced HEX20 midside node; maximum relative "
            f"edge deviation {metrics['mid_edge_deviation_ratio_max']:.3e}."
        )
    if metrics["sampled_jacobian_ratio"] < 5.0e-2:
        warnings.append(
            f"Element {index}: high HEX20 Jacobian variation; sampled ratio "
            f"{metrics['sampled_jacobian_ratio']:.3e}."
        )
    return {"index": index, "type": element_type, **metrics}, warnings


def geometry_error(index: int, element_type: str, coords: np.ndarray) -> str | None:
    """Return a portable geometry error for HEX8/HEX20, if any."""
    element = {"HEX8": Hex8Element, "HEX20": Hex20Element}.get(element_type)
    if element is None:
        return None
    try:
        element.validate_geometry(coords)
    except ValueError as exc:
        return f"Element {index}: invalid {element_type} geometry: {exc}"
    return None


def maximum_surface_face(element_type: str) -> int | None:
    """Return the last valid face index for a solid family."""
    if element_type in {"HEX8", "HEX20"}:
        return 5
    if element_type in {"TET4", "TET10"}:
        return 3
    return None
