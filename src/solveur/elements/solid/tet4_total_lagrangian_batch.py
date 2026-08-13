"""Vectorized assembly for total-Lagrangian TET4 meshes."""

from __future__ import annotations

import numpy as np
from scipy.sparse import coo_matrix, csr_matrix

from solveur.materials.solid import SolidMaterial


class TotalLagrangianTet4Assembly:
    """Cache reference geometry and assemble finite-kinematics TET4 arrays."""

    def __init__(self, nodes: np.ndarray, elements: np.ndarray, material: SolidMaterial):
        self.nodes = np.asarray(nodes, dtype=float)
        self.elements = np.asarray(elements, dtype=int)
        self.material = material
        self._validate_mesh()
        self.element_dofs = (3 * self.elements[:, :, None] + np.arange(3)).reshape(-1, 12)
        coordinates = self.nodes[self.elements]
        interpolation = np.concatenate(
            (np.ones((self.elements.shape[0], 4, 1)), coordinates), axis=2
        )
        inverse = np.linalg.inv(interpolation)
        self.gradients = np.transpose(inverse[:, 1:, :], (0, 2, 1))
        jacobians = np.stack(
            (
                coordinates[:, 1] - coordinates[:, 0],
                coordinates[:, 2] - coordinates[:, 0],
                coordinates[:, 3] - coordinates[:, 0],
            ),
            axis=2,
        )
        self.volumes = np.linalg.det(jacobians) / 6.0
        if np.any(self.volumes <= 1.0e-14):
            index = int(np.flatnonzero(self.volumes <= 1.0e-14)[0])
            raise ValueError(f"Invalid TET4-TL reference volume at element {index}: {self.volumes[index]:.6e}.")
        self._rows = np.repeat(self.element_dofs, 12, axis=1).ravel()
        self._cols = np.tile(self.element_dofs, (1, 12)).ravel()

    @property
    def ndof(self) -> int:
        return 3 * self.nodes.shape[0]

    def assemble(
        self, displacement: np.ndarray, *, tangent_required: bool = True
    ) -> tuple[np.ndarray, csr_matrix | None]:
        """Assemble internal force and, optionally, the consistent tangent."""
        local_displacement = self._local_displacements(displacement)
        deformation, stress = self._kinematics(local_displacement)
        first_piola = np.einsum("miI,mIJ->miJ", deformation, stress, optimize=True)
        local_internal = self.volumes[:, None, None] * np.einsum(
            "miJ,maJ->mai", first_piola, self.gradients, optimize=True
        )
        internal = np.zeros(self.ndof, dtype=float)
        np.add.at(internal, self.element_dofs.ravel(), local_internal.ravel())
        if not tangent_required:
            return internal, None
        local_tangent = self._consistent_tangents(deformation, stress)
        tangent = coo_matrix(
            (local_tangent.ravel(), (self._rows, self._cols)), shape=(self.ndof, self.ndof)
        ).tocsr()
        return internal, tangent

    def strain_energy(self, displacement: np.ndarray) -> float:
        """Return total Saint-Venant-Kirchhoff energy over the mesh."""
        local_displacement = self._local_displacements(displacement)
        deformation, _ = self._kinematics(local_displacement)
        green = 0.5 * (
            np.einsum("miI,miJ->mIJ", deformation, deformation, optimize=True) - np.eye(3)
        )
        lam, mu = self.lame_constants
        density = 0.5 * lam * np.trace(green, axis1=1, axis2=2) ** 2
        density += mu * np.einsum("mIJ,mIJ->m", green, green, optimize=True)
        return float(np.dot(self.volumes, density))

    def deformation_determinants(self, displacement: np.ndarray) -> np.ndarray:
        """Return det(F) for every element in the current configuration."""
        deformation, _ = self._kinematics(self._local_displacements(displacement))
        return np.linalg.det(deformation)

    def element_states(self, displacement: np.ndarray) -> dict[str, np.ndarray]:
        """Return finite-strain states at the constant TET4 integration point."""
        local_displacement = self._local_displacements(displacement)
        deformation, second_piola = self._kinematics(local_displacement)
        green = 0.5 * (
            np.einsum("miI,miJ->mIJ", deformation, deformation, optimize=True) - np.eye(3)
        )
        determinants = np.linalg.det(deformation)
        cauchy = np.einsum(
            "miI,mIJ,mjJ->mij", deformation, second_piola, deformation, optimize=True
        ) / determinants[:, None, None]
        energy_density = 0.5 * np.einsum(
            "mIJ,mIJ->m", green, second_piola, optimize=True
        )
        return {
            "deformation_gradient": deformation,
            "green_lagrange_strain": green,
            "second_piola_stress": second_piola,
            "cauchy_stress": 0.5 * (cauchy + np.transpose(cauchy, (0, 2, 1))),
            "strain_energy_density": energy_density,
            "det_f": determinants,
        }

    @property
    def lame_constants(self) -> tuple[float, float]:
        young = self.material.E
        poisson = self.material.nu
        lam = young * poisson / ((1.0 + poisson) * (1.0 - 2.0 * poisson))
        mu = young / (2.0 * (1.0 + poisson))
        return lam, mu

    def _kinematics(self, local_displacement: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        deformation = np.eye(3) + np.einsum(
            "mai,maJ->miJ", local_displacement, self.gradients, optimize=True
        )
        determinants = np.linalg.det(deformation)
        if not np.all(np.isfinite(deformation)) or np.any(determinants <= 1.0e-10):
            minimum = float(np.nanmin(determinants))
            raise ValueError(f"Invalid finite deformation gradient determinant {minimum:.6e}.")
        green = 0.5 * (
            np.einsum("miI,miJ->mIJ", deformation, deformation, optimize=True) - np.eye(3)
        )
        lam, mu = self.lame_constants
        traces = np.trace(green, axis1=1, axis2=2)
        stress = lam * traces[:, None, None] * np.eye(3) + 2.0 * mu * green
        return deformation, stress

    def _consistent_tangents(self, deformation: np.ndarray, stress: np.ndarray) -> np.ndarray:
        identity = np.eye(3)
        lam, mu = self.lame_constants
        elasticity = (
            lam * np.einsum("IJ,KL->IJKL", identity, identity)
            + mu * np.einsum("IK,JL->IJKL", identity, identity)
            + mu * np.einsum("IL,JK->IJKL", identity, identity)
        )
        material = np.einsum(
            "miI,IJKL,mkK->miJkL", deformation, elasticity, deformation, optimize=True
        )
        geometric = np.einsum("ik,mLJ->miJkL", identity, stress, optimize=True)
        constitutive = material + geometric
        blocks = self.volumes[:, None, None, None, None] * np.einsum(
            "maJ,miJkL,mbL->maibk", self.gradients, constitutive, self.gradients, optimize=True
        )
        tangent = blocks.reshape(-1, 12, 12)
        return 0.5 * (tangent + np.transpose(tangent, (0, 2, 1)))

    def _local_displacements(self, displacement: np.ndarray) -> np.ndarray:
        values = np.asarray(displacement, dtype=float)
        if values.shape != (self.ndof,) or not np.all(np.isfinite(values)):
            raise ValueError(f"TET4-TL displacement must be a finite vector of size {self.ndof}.")
        return values[self.element_dofs].reshape(-1, 4, 3)

    def _validate_mesh(self) -> None:
        if self.nodes.ndim != 2 or self.nodes.shape[1] != 3 or not np.all(np.isfinite(self.nodes)):
            raise ValueError("TET4-TL nodes must be a finite [n, 3] array.")
        if self.elements.ndim != 2 or self.elements.shape[1] != 4:
            raise ValueError("TET4-TL connectivity must be an [m, 4] array.")
        if self.elements.size == 0 or np.min(self.elements) < 0 or np.max(self.elements) >= self.nodes.shape[0]:
            raise ValueError("TET4-TL connectivity contains an invalid node index.")
        if np.any(np.apply_along_axis(lambda row: np.unique(row).size, 1, self.elements) != 4):
            raise ValueError("TET4-TL elements must reference four distinct nodes.")
