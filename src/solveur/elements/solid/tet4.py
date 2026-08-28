"""Linear four-node tetrahedral solid element."""

from __future__ import annotations

import numpy as np

from solveur.elements.solid.common import (
    strain_displacement_from_gradients,
    symmetrize,
    validate_coords_shape,
    von_mises_3d,
)
from solveur.core.nonlinear.contracts import evaluate_constitutive
from solveur.materials.solid import SolidConstitutiveMaterial


class Tet4Element:
    """Constant-strain TET4 element for 3D linear elasticity."""

    integration_point_count = 1

    def __init__(self, material: SolidConstitutiveMaterial):
        self.material = material

    @staticmethod
    def signed_volume(coords: np.ndarray) -> float:
        coords = np.asarray(coords, dtype=float)
        matrix = np.column_stack((coords[1] - coords[0], coords[2] - coords[0], coords[3] - coords[0]))
        return float(np.linalg.det(matrix) / 6.0)

    @staticmethod
    def shape_gradients(coords: np.ndarray) -> np.ndarray:
        coords = np.asarray(coords, dtype=float)
        interpolation = np.column_stack((np.ones(4), coords))
        inv_interp = np.linalg.inv(interpolation)
        return inv_interp[1:, :].T

    @staticmethod
    def strain_displacement_matrix(coords: np.ndarray) -> np.ndarray:
        coords = validate_coords_shape(coords, (4, 3), "TET4")
        gradients = Tet4Element.shape_gradients(coords)
        return strain_displacement_from_gradients(gradients)

    def stiffness(self, coords: np.ndarray) -> np.ndarray:
        coords = validate_coords_shape(coords, (4, 3), "TET4")
        volume = self.signed_volume(coords)
        if volume <= 1.0e-14:
            raise ValueError(f"Invalid TET4 volume {volume:.6e}.")
        b = self.strain_displacement_matrix(coords)
        ke = volume * (b.T @ self.material.elasticity_matrix @ b)
        return symmetrize(ke)

    def internal_force_and_tangent(
        self,
        coords: np.ndarray,
        local_displacement: np.ndarray,
        states: list[dict[str, object]] | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        internal, tangent, _ = self.internal_force_tangent_state(coords, local_displacement, states)
        return internal, tangent

    def internal_force_tangent_state(
        self,
        coords: np.ndarray,
        local_displacement: np.ndarray,
        states: list[dict[str, object]] | None = None,
    ) -> tuple[np.ndarray, np.ndarray, list[dict[str, object]]]:
        volume = self.signed_volume(coords)
        if volume <= 1.0e-14:
            raise ValueError(f"Invalid TET4 volume {volume:.6e}.")
        b = self.strain_displacement_matrix(coords)
        strain = b @ np.asarray(local_displacement, dtype=float)
        updated_states: list[dict[str, object]] = []
        previous = states[0] if states else None
        response = evaluate_constitutive(self.material, strain, previous)
        stress, tangent = response.stress, response.tangent
        if response.diagnostics.get("stateful", False):
            updated_states.append(response.trial_state)
        internal = volume * (b.T @ stress)
        stiffness = volume * (b.T @ tangent @ b)
        return internal, symmetrize(stiffness), updated_states

    def mass(self, coords: np.ndarray) -> np.ndarray:
        if self.material.density <= 0.0:
            raise ValueError("TET4 modal analysis requires a positive material density.")
        volume = self.signed_volume(coords)
        if volume <= 1.0e-14:
            raise ValueError(f"Invalid TET4 volume {volume:.6e}.")
        scalar = self.material.density * volume / 20.0
        mass = np.zeros((12, 12), dtype=float)
        for i in range(4):
            for j in range(4):
                factor = 2.0 if i == j else 1.0
                mass[3 * i : 3 * i + 3, 3 * j : 3 * j + 3] = factor * scalar * np.eye(3)
        return mass

    def strain(self, coords: np.ndarray, local_displacement: np.ndarray) -> np.ndarray:
        return self.strain_displacement_matrix(coords) @ np.asarray(local_displacement, dtype=float)

    def stress(self, coords: np.ndarray, local_displacement: np.ndarray) -> np.ndarray:
        stress, _ = self.material.stress_tangent(self.strain(coords, local_displacement))
        return stress

    @staticmethod
    def von_mises(stress: np.ndarray) -> float:
        return von_mises_3d(stress)
