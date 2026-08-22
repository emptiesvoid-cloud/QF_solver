"""Canonical MITC4 formulation for the QF_solver shell-element family.

The historical :mod:`mitc4` package remains a compatibility facade during the
0.2.x series. New product code should import the formulation from this module.
"""

from .adapter import Mitc4ShellElement
from .element import MITC4Element, Q4FullShearElement, ShearScheme, StrainMatrices
from .material import ShellMaterial
from .mesh import MeshFactory, QuadMesh
from .model import ShellModel

__all__ = [
    "MITC4Element",
    "MeshFactory",
    "Mitc4ShellElement",
    "QuadMesh",
    "Q4FullShearElement",
    "ShearScheme",
    "ShellMaterial",
    "ShellModel",
    "StrainMatrices",
]
