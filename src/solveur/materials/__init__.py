"""Material models."""

from solveur.materials.beam import BeamSectionMaterial
from solveur.materials.composite import OrthotropicLamina
from solveur.materials.failure import (
    CompositeFailureEvaluator,
    FailureCriterionResult,
    PlyStrainAllowables,
    PlyStrengths,
)
from solveur.materials.laminate import ClassicalLaminate, LaminaPly, LaminateShellMaterial, PlyPointResult
from solveur.materials.orthotropic import OrthotropicSolidMaterial, material_orientation

__all__ = [
    "BeamSectionMaterial",
    "ClassicalLaminate",
    "CompositeFailureEvaluator",
    "FailureCriterionResult",
    "LaminaPly",
    "LaminateShellMaterial",
    "OrthotropicLamina",
    "OrthotropicSolidMaterial",
    "PlyPointResult",
    "PlyStrainAllowables",
    "PlyStrengths",
    "material_orientation",
]
