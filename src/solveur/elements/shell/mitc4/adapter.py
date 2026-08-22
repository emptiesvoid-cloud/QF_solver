"""Adapter around the validated MITC4 shell implementation."""

from __future__ import annotations

import numpy as np

from .element import MITC4Element
from .material import ShellMaterial


class Mitc4ShellElement:
    """Four-node MITC4 shell using the existing validated implementation."""

    def __init__(self, material: ShellMaterial):
        self._element = MITC4Element(material)

    def stiffness(self, coords: np.ndarray) -> np.ndarray:
        return self._element.stiffness(coords)

    def mass(self, coords: np.ndarray) -> np.ndarray:
        return self._element.mass(coords)
