"""Total-Lagrangian HEX8 assembly for the common geometric nonlinear path."""

from __future__ import annotations

import numpy as np
from scipy.sparse import coo_matrix, csr_matrix

from solveur.elements.solid.hex8 import Hex8Element
from solveur.materials.solid import SolidMaterial


class TotalLagrangianHex8Assembly:
    """Reference-configuration HEX8 assembly with a consistent StVK tangent."""

    def __init__(self, nodes: np.ndarray, elements: np.ndarray, material: SolidMaterial):
        self.nodes = np.asarray(nodes, dtype=float)
        self.elements = np.asarray(elements, dtype=int)
        self.material = material
        self._validate_mesh()
        self.element_dofs = (3 * self.elements[:, :, None] + np.arange(3)).reshape(-1, 24)
        self._rows = np.repeat(self.element_dofs, 24, axis=1).ravel()
        self._cols = np.tile(self.element_dofs, (1, 24)).ravel()
        self._reference_data = tuple(self._element_reference_data(coords) for coords in self.nodes[self.elements])

    @property
    def ndof(self) -> int:
        return 3 * self.nodes.shape[0]

    def assemble(
        self, displacement: np.ndarray, *, tangent_required: bool = True
    ) -> tuple[np.ndarray, csr_matrix | None]:
        """Assemble internal force and, optionally, the sparse consistent tangent."""
        local_displacements = self._local_displacements(displacement)
        internal = np.zeros(self.ndof, dtype=float)
        local_tangents: list[np.ndarray] = []
        for element_index, local_u in enumerate(local_displacements):
            local_internal, local_tangent = self._element_force_tangent(
                element_index, local_u, tangent_required=tangent_required
            )
            np.add.at(internal, self.element_dofs[element_index], local_internal)
            if tangent_required:
                local_tangents.append(local_tangent)
        if not tangent_required:
            return internal, None
        tangent = coo_matrix(
            (np.asarray(local_tangents).ravel(), (self._rows, self._cols)),
            shape=(self.ndof, self.ndof),
        ).tocsr()
        return internal, 0.5 * (tangent + tangent.T)

    def geometric_tangent(self, displacement: np.ndarray) -> csr_matrix:
        """Assemble the initial-stress geometric tangent in sparse form."""
        local_displacements = self._local_displacements(displacement)
        local_tangents: list[np.ndarray] = []
        identity = np.eye(3)
        for element_index, local_u in enumerate(local_displacements):
            local_tangent = np.zeros((24, 24), dtype=float)
            for _, weight, gradients, determinant in self._reference_data[element_index]:
                deformation = self._deformation_gradient(local_u, gradients)
                green = 0.5 * (deformation.T @ deformation - identity)
                second = self._second_piola(green)
                scalar_blocks = np.einsum(
                    "aJ,JL,bL->ab", gradients, second, gradients, optimize=True
                )
                local_tangent += (weight * determinant) * np.einsum(
                    "ab,ik->aibk", scalar_blocks, identity, optimize=True
                ).reshape(24, 24)
            local_tangents.append(0.5 * (local_tangent + local_tangent.T))
        tangent = coo_matrix(
            (np.asarray(local_tangents).ravel(), (self._rows, self._cols)),
            shape=(self.ndof, self.ndof),
        ).tocsr()
        return 0.5 * (tangent + tangent.T)

    def strain_energy(self, displacement: np.ndarray) -> float:
        """Return the integrated Saint-Venant-Kirchhoff energy."""
        local_displacements = self._local_displacements(displacement)
        total = 0.0
        for element_index, local_u in enumerate(local_displacements):
            for point, weight, gradients, determinant in self._reference_data[element_index]:
                deformation = self._deformation_gradient(local_u, gradients)
                green = 0.5 * (deformation.T @ deformation - np.eye(3))
                total += weight * determinant * self._energy_density(green)
        return float(total)

    def deformation_determinants(self, displacement: np.ndarray) -> np.ndarray:
        """Return the minimum current determinant at each element's Gauss points."""
        local_displacements = self._local_displacements(displacement)
        values = []
        for element_index, local_u in enumerate(local_displacements):
            values.append(
                min(
                    float(np.linalg.det(self._deformation_gradient(local_u, gradients)))
                    for _, _, gradients, _ in self._reference_data[element_index]
                )
            )
        return np.asarray(values, dtype=float)

    def element_states(self, displacement: np.ndarray) -> dict[str, np.ndarray]:
        """Return volume-weighted Gauss-point states for post-processing."""
        local_displacements = self._local_displacements(displacement)
        fields = {
            key: []
            for key in ("deformation_gradient", "green_lagrange_strain", "second_piola_stress", "cauchy_stress")
        }
        energy_densities: list[float] = []
        determinants: list[float] = []
        for element_index, local_u in enumerate(local_displacements):
            weighted = 0.0
            averages = {key: np.zeros((3, 3), dtype=float) for key in fields}
            energy = 0.0
            element_dets: list[float] = []
            for point, weight, gradients, determinant in self._reference_data[element_index]:
                deformation = self._deformation_gradient(local_u, gradients)
                current_det = float(np.linalg.det(deformation))
                green = 0.5 * (deformation.T @ deformation - np.eye(3))
                second = self._second_piola(green)
                cauchy = deformation @ second @ deformation.T / current_det
                measure = weight * determinant
                weighted += measure
                for key, value in {
                    "deformation_gradient": deformation,
                    "green_lagrange_strain": green,
                    "second_piola_stress": second,
                    "cauchy_stress": 0.5 * (cauchy + cauchy.T),
                }.items():
                    averages[key] += measure * value
                energy += measure * self._energy_density(green)
                element_dets.append(current_det)
            for key in fields:
                fields[key].append(averages[key] / weighted)
            energy_densities.append(energy / weighted)
            determinants.append(min(element_dets))
        return {
            **{key: np.asarray(value) for key, value in fields.items()},
            "strain_energy_density": np.asarray(energy_densities),
            "det_f": np.asarray(determinants),
        }

    @property
    def lame_constants(self) -> tuple[float, float]:
        young = self.material.E
        poisson = self.material.nu
        lam = young * poisson / ((1.0 + poisson) * (1.0 - 2.0 * poisson))
        mu = young / (2.0 * (1.0 + poisson))
        return lam, mu

    def _element_force_tangent(
        self, element_index: int, local_u: np.ndarray, *, tangent_required: bool
    ) -> tuple[np.ndarray, np.ndarray]:
        internal = np.zeros(24, dtype=float)
        tangent = np.zeros((24, 24), dtype=float)
        for point, weight, gradients, determinant in self._reference_data[element_index]:
            deformation = self._deformation_gradient(local_u, gradients)
            green = 0.5 * (deformation.T @ deformation - np.eye(3))
            second = self._second_piola(green)
            first = deformation @ second
            measure = weight * determinant
            internal += measure * np.einsum("iJ,aJ->ai", first, gradients).reshape(24)
            if tangent_required:
                tangent += measure * self._tangent(deformation, second, gradients)
        return internal, 0.5 * (tangent + tangent.T)

    def _tangent(self, deformation: np.ndarray, stress: np.ndarray, gradients: np.ndarray) -> np.ndarray:
        identity = np.eye(3)
        lam, mu = self.lame_constants
        elasticity = (
            lam * np.einsum("IJ,KL->IJKL", identity, identity)
            + mu * np.einsum("IK,JL->IJKL", identity, identity)
            + mu * np.einsum("IL,JK->IJKL", identity, identity)
        )
        material = np.einsum("iI,IJKL,kK->iJkL", deformation, elasticity, deformation)
        geometric = np.einsum("ik,LJ->iJkL", identity, stress)
        constitutive = material + geometric
        tangent = np.zeros((24, 24), dtype=float)
        for node_a, gradient_a in enumerate(gradients):
            for node_b, gradient_b in enumerate(gradients):
                tangent[3 * node_a : 3 * node_a + 3, 3 * node_b : 3 * node_b + 3] = np.einsum(
                    "J,iJkL,L->ik", gradient_a, constitutive, gradient_b
                )
        return tangent

    def _second_piola(self, green: np.ndarray) -> np.ndarray:
        lam, mu = self.lame_constants
        return lam * float(np.trace(green)) * np.eye(3) + 2.0 * mu * green

    def _energy_density(self, green: np.ndarray) -> float:
        lam, mu = self.lame_constants
        return 0.5 * lam * float(np.trace(green)) ** 2 + mu * float(np.sum(green * green))

    @staticmethod
    def _deformation_gradient(local_u: np.ndarray, gradients: np.ndarray) -> np.ndarray:
        deformation = np.eye(3) + np.asarray(local_u).reshape(8, 3).T @ gradients
        determinant = float(np.linalg.det(deformation))
        if not np.all(np.isfinite(deformation)) or determinant <= 1.0e-10:
            raise ValueError(f"Invalid finite deformation gradient determinant {determinant:.6e}.")
        return deformation

    @staticmethod
    def _element_reference_data(coords: np.ndarray) -> tuple[tuple[tuple[float, float, float], float, np.ndarray, float], ...]:
        Hex8Element.validate_geometry(coords)
        data = []
        for point, weight in zip(Hex8Element.integration_points, (1.0,) * Hex8Element.integration_point_count):
            jacobian = Hex8Element.jacobian(coords, point)
            determinant = float(np.linalg.det(jacobian))
            gradients = Hex8Element.shape_derivatives_reference(point) @ np.linalg.inv(jacobian).T
            data.append((point, weight, gradients, determinant))
        return tuple(data)

    def _local_displacements(self, displacement: np.ndarray) -> np.ndarray:
        values = np.asarray(displacement, dtype=float)
        if values.shape != (self.ndof,) or not np.all(np.isfinite(values)):
            raise ValueError(f"HEX8-TL displacement must be a finite vector of size {self.ndof}.")
        return values[self.element_dofs].reshape(-1, 8, 3)

    def _validate_mesh(self) -> None:
        if self.nodes.ndim != 2 or self.nodes.shape[1] != 3 or not np.all(np.isfinite(self.nodes)):
            raise ValueError("HEX8-TL nodes must be a finite [n, 3] array.")
        if self.elements.ndim != 2 or self.elements.shape[1] != 8:
            raise ValueError("HEX8-TL connectivity must be an [m, 8] array.")
        if self.elements.size == 0 or np.min(self.elements) < 0 or np.max(self.elements) >= self.nodes.shape[0]:
            raise ValueError("HEX8-TL connectivity contains an invalid node index.")
        if np.any(np.apply_along_axis(lambda row: np.unique(row).size, 1, self.elements) != 8):
            raise ValueError("HEX8-TL elements must reference eight distinct nodes.")
