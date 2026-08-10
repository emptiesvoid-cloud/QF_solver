"""MITC4 flat-shell finite element package."""

from mitc4.benchmarks import CantileverPlateBenchmark, ScordelisLoBenchmark, ShearLockingStudy
from mitc4.element import MITC4Element, Q4FullShearElement
from mitc4.material import ShellMaterial
from mitc4.model import ShellModel
from mitc4.verification import MechanicalVerifier, VerificationResult

__all__ = [
    "CantileverPlateBenchmark",
    "MITC4Element",
    "MechanicalVerifier",
    "Q4FullShearElement",
    "ScordelisLoBenchmark",
    "ShearLockingStudy",
    "ShellMaterial",
    "ShellModel",
    "VerificationResult",
]
