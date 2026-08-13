"""Element registry used by validation and assembly."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

import numpy as np

from solveur.core.dofs import BEAM_DOFS, SHELL_DOFS, SOLID_DOFS
from solveur.elements.beam.beam2 import Beam2Element
from solveur.elements.shell.mitc3 import Mitc3ShellElement
from solveur.elements.shell.mitc4 import Mitc4ShellElement
from solveur.elements.solid.tet10 import Tet10Element
from solveur.elements.solid.tet4 import Tet4Element


class ElementProtocol(Protocol):
    def stiffness(self, coords: np.ndarray) -> np.ndarray:
        """Return the element stiffness matrix."""


@dataclass(frozen=True)
class ElementSpec:
    name: str
    node_count: int
    dofs: tuple[str, ...]
    material_types: tuple[str, ...]
    factory: Callable[[object], ElementProtocol]


class ElementRegistry:
    """Central list of element families supported by the solver."""

    _specs = {
        "BEAM2": ElementSpec("BEAM2", 2, BEAM_DOFS, ("beam_isotropic",), Beam2Element),
        "MITC3": ElementSpec("MITC3", 3, SHELL_DOFS, ("shell_isotropic", "shell_laminate"), Mitc3ShellElement),
        "MITC4": ElementSpec("MITC4", 4, SHELL_DOFS, ("shell_isotropic", "shell_laminate"), Mitc4ShellElement),
        "TET4": ElementSpec(
            "TET4",
            4,
            SOLID_DOFS,
            (
                "isotropic_3d",
                "orthotropic_3d",
                "composite_orthotropic_3d",
                "nonlinear_isotropic_3d",
                "von_mises_elastoplastic_3d",
            ),
            Tet4Element,
        ),
        "TET10": ElementSpec(
            "TET10",
            10,
            SOLID_DOFS,
            (
                "isotropic_3d",
                "orthotropic_3d",
                "composite_orthotropic_3d",
                "nonlinear_isotropic_3d",
                "von_mises_elastoplastic_3d",
            ),
            Tet10Element,
        ),
    }

    @classmethod
    def get(cls, element_type: str) -> ElementSpec:
        key = str(element_type).upper()
        if key not in cls._specs:
            raise ValueError(f"Unsupported element type {element_type!r}.")
        return cls._specs[key]
