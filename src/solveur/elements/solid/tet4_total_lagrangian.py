"""Total-Lagrangian TET4 verification kernel for finite kinematics."""

from __future__ import annotations

import numpy as np

from solveur.elements.solid.common import symmetrize, validate_coords_shape
from solveur.elements.solid.tet4 import Tet4Element
from solveur.materials.solid import SolidMaterial


class TotalLagrangianTet4Kernel:
    """Finite-kinematics TET4 with a Saint-Venant-Kirchhoff material."""

    def __init__(self, material: SolidMaterial):
        self.material = material

    def internal_force_and_tangent(
        self, reference_coords: np.ndarray, local_displacement: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return reference-configuration internal force and consistent tangent."""
        coords, displacement, volume, gradients = self._validated_inputs(reference_coords, local_displacement)
        deformation = self.deformation_gradient(coords, displacement)
        strain = self.green_lagrange_strain(deformation)
        stress = self.second_piola_stress(strain)
        first_piola = deformation @ stress
        internal = volume * np.einsum("iJ,aJ->ai", first_piola, gradients).reshape(12)
        tangent = self._consistent_tangent(deformation, stress, gradients, volume)
        return internal, symmetrize(tangent)

    def internal_force(self, reference_coords: np.ndarray, local_displacement: np.ndarray) -> np.ndarray:
        """Return only the internal force, without forming the consistent tangent."""
        coords, displacement, volume, gradients = self._validated_inputs(reference_coords, local_displacement)
        deformation = self.deformation_gradient(coords, displacement)
        strain = self.green_lagrange_strain(deformation)
        first_piola = deformation @ self.second_piola_stress(strain)
        return volume * np.einsum("iJ,aJ->ai", first_piola, gradients).reshape(12)

    def strain_energy(self, reference_coords: np.ndarray, local_displacement: np.ndarray) -> float:
        """Return total Saint-Venant-Kirchhoff strain energy in the reference volume."""
        coords, displacement, volume, _ = self._validated_inputs(reference_coords, local_displacement)
        strain = self.green_lagrange_strain(self.deformation_gradient(coords, displacement))
        lam, mu = self.lame_constants
        density = 0.5 * lam * float(np.trace(strain)) ** 2 + mu * float(np.sum(strain * strain))
        return volume * density

    @staticmethod
    def deformation_gradient(reference_coords: np.ndarray, local_displacement: np.ndarray) -> np.ndarray:
        """Compute F = I + grad_X(u) from reference shape gradients."""
        coords = validate_coords_shape(reference_coords, (4, 3), "TET4-TL")
        displacement = np.asarray(local_displacement, dtype=float).reshape(4, 3)
        deformation = np.eye(3) + displacement.T @ Tet4Element.shape_gradients(coords)
        determinant = float(np.linalg.det(deformation))
        if not np.all(np.isfinite(deformation)) or determinant <= 1.0e-10:
            raise ValueError(f"Invalid finite deformation gradient determinant {determinant:.6e}.")
        return deformation

    @staticmethod
    def green_lagrange_strain(deformation_gradient: np.ndarray) -> np.ndarray:
        """Compute E = 1/2 (F^T F - I)."""
        deformation = np.asarray(deformation_gradient, dtype=float)
        return 0.5 * (deformation.T @ deformation - np.eye(3))

    def second_piola_stress(self, green_strain: np.ndarray) -> np.ndarray:
        """Compute S = lambda tr(E) I + 2 mu E."""
        strain = np.asarray(green_strain, dtype=float)
        lam, mu = self.lame_constants
        return lam * float(np.trace(strain)) * np.eye(3) + 2.0 * mu * strain

    @property
    def lame_constants(self) -> tuple[float, float]:
        young = self.material.E
        poisson = self.material.nu
        lam = young * poisson / ((1.0 + poisson) * (1.0 - 2.0 * poisson))
        mu = young / (2.0 * (1.0 + poisson))
        return lam, mu

    def _consistent_tangent(
        self,
        deformation: np.ndarray,
        stress: np.ndarray,
        gradients: np.ndarray,
        volume: float,
    ) -> np.ndarray:
        identity = np.eye(3)
        lam, mu = self.lame_constants
        elasticity = (
            lam * np.einsum("IJ,KL->IJKL", identity, identity)
            + mu * np.einsum("IK,JL->IJKL", identity, identity)
            + mu * np.einsum("IL,JK->IJKL", identity, identity)
        )
        material_part = np.einsum("iI,IJKL,kK->iJkL", deformation, elasticity, deformation)
        geometric_part = np.einsum("ik,LJ->iJkL", identity, stress)
        constitutive_tangent = material_part + geometric_part
        tangent = np.zeros((12, 12), dtype=float)
        for node_a, gradient_a in enumerate(gradients):
            for node_b, gradient_b in enumerate(gradients):
                block = volume * np.einsum("J,iJkL,L->ik", gradient_a, constitutive_tangent, gradient_b)
                tangent[3 * node_a : 3 * node_a + 3, 3 * node_b : 3 * node_b + 3] = block
        return tangent

    @staticmethod
    def _validated_inputs(
        reference_coords: np.ndarray, local_displacement: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, float, np.ndarray]:
        coords = validate_coords_shape(reference_coords, (4, 3), "TET4-TL")
        displacement = np.asarray(local_displacement, dtype=float)
        if displacement.shape != (12,) or not np.all(np.isfinite(displacement)):
            raise ValueError("TET4-TL local displacement must be a finite 12-vector.")
        volume = Tet4Element.signed_volume(coords)
        if volume <= 1.0e-14:
            raise ValueError(f"Invalid TET4-TL reference volume {volume:.6e}.")
        gradients = Tet4Element.shape_gradients(coords)
        return coords, displacement, volume, gradients
