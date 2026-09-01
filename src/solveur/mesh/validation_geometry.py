"""Element geometry checks shared by the mesh validator."""

from __future__ import annotations

import numpy as np

from solveur.elements.shell.mitc4 import MITC4Element, ShellMaterial
from solveur.elements.shell.mitc3 import Mitc3ShellElement
from solveur.elements.solid.tet10 import Tet10Element
from solveur.mesh.quality import MeshQuality, MeshQualityThresholds
from solveur.mesh.solid_validation import geometry_error


def check_element_geometry(
    thresholds: MeshQualityThresholds,
    index: int,
    element_type: str,
    coords: np.ndarray,
    errors: list[str],
    warnings: list[str],
) -> None:
    """Append fatal geometry findings while preserving the validator contract."""
    if element_type in {"TET4", "TET10"}:
        volume = MeshQuality.tet4_volume(coords)
        if volume <= thresholds.tet_min_signed_volume:
            errors.append(f"Element {index}: invalid {element_type} signed corner volume {volume:.6e}.")
            return
        if element_type == "TET10":
            minimum = float(np.min(Tet10Element.jacobian_determinants(coords)))
            if minimum <= thresholds.tet10_min_sampled_jacobian:
                errors.append(
                    f"Element {index}: invalid TET10 sampled Jacobian {minimum:.6e}; "
                    "the curved mapping is inverted or degenerate."
                )
    else:
        error = geometry_error(index, element_type, coords)
        if error is not None:
            errors.append(error)
        if element_type in {"HEX8", "HEX20", "WEDGE6"}:
            return
    if element_type == "MITC4":
        element = MITC4Element(ShellMaterial(E=1.0, nu=0.3, t=1.0))
        try:
            _, coords_2d = element.project_to_local_midplane(coords)
            element._check_jacobian(coords_2d)
        except ValueError as exc:
            errors.append(f"Element {index}: invalid MITC4 geometry: {exc}")
    elif element_type == "MITC3":
        try:
            Mitc3ShellElement(ShellMaterial(E=1.0, nu=0.3, t=1.0)).project_to_local_midplane(coords)
        except ValueError as exc:
            errors.append(f"Element {index}: invalid MITC3 geometry: {exc}")
    elif element_type == "BEAM2":
        length = float(np.linalg.norm(coords[1] - coords[0]))
        if not np.isfinite(length) or length <= 1.0e-14:
            errors.append(f"Element {index}: invalid BEAM2 length {length:.6e}.")
