"""Deprecated MITC4 compatibility facade for QF_solver 0.2.x."""

from solveur.elements.shell.mitc4 import (
    MITC4Element,
    MeshFactory,
    Q4FullShearElement,
    QuadMesh,
    ShellMaterial,
    ShellModel,
)
from solveur.post.mitc4_visualization import DeformationPlotter
from solveur.verification.mitc4_benchmarks import (
    CantileverPlateBenchmark,
    ScordelisLoBenchmark,
    ShearLockingStudy,
)
from solveur.verification.mitc4_mechanical import MechanicalVerifier, VerificationResult

__all__ = [
    "CantileverPlateBenchmark",
    "DeformationPlotter",
    "MITC4Element",
    "MeshFactory",
    "MechanicalVerifier",
    "Q4FullShearElement",
    "QuadMesh",
    "ScordelisLoBenchmark",
    "ShearLockingStudy",
    "ShellMaterial",
    "ShellModel",
    "VerificationResult",
]
