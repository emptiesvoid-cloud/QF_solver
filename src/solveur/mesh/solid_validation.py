"""Solid-element mesh validation helpers."""

from __future__ import annotations

from typing import Any

import numpy as np

from solveur.elements.solid.hex20 import Hex20Element
from solveur.elements.solid.hex8 import Hex8Element
from solveur.mesh.quality import MeshQuality
from solveur.mesh.quality_contract import assess_element, wedge6_jacobian_certificate


def quality_details(
    index: int, element_type: str, coords: np.ndarray
) -> tuple[dict[str, Any], list[str]] | None:
    """Return family-specific details that need more than the legacy metrics."""
    if element_type == "WEDGE6":
        assessment = assess_element(index, element_type, coords)
        warnings = [f"Element {index}: {warning}." for warning in assessment.warnings]
        return (
            {
                "index": index,
                "type": element_type,
                **assessment.metrics,
                "quality_classification": assessment.classification,
                "quality_fatal_findings": list(assessment.fatal_findings),
            },
            warnings,
        )
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
    """Return a portable geometry error for supported solid families, if any."""
    if element_type == "WEDGE6":
        try:
            certificate = wedge6_jacobian_certificate(coords)
            if not certificate["valid"]:
                return (
                    f"Element {index}: invalid WEDGE6 geometry: "
                    "WEDGE6_JACOBIAN_ORIENTATION_INVALID "
                    f"(certified minimum detJ {certificate['minimum_detJ']:.6e})."
                )
        except (TypeError, ValueError, np.linalg.LinAlgError) as exc:
            return f"Element {index}: invalid WEDGE6 geometry: {exc}"
        return None
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
