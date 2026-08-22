"""Deprecated compatibility facade for MITC4 convergence studies."""

from solveur.verification.mitc4_convergence import (
    ConvergencePoint,
    Mitc4StructuralConvergence,
    StructuralConvergence,
    cook_large_point,
)

__all__ = [
    "ConvergencePoint",
    "Mitc4StructuralConvergence",
    "StructuralConvergence",
    "cook_large_point",
]
