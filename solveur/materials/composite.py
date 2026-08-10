"""Linear orthotropic lamina constitutive law for composite preparation."""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, isfinite, radians, sin

import numpy as np


@dataclass(frozen=True)
class OrthotropicLamina:
    """Plane-stress orthotropic lamina expressed in material axes 1-2.

    Axis 1 follows the fibres, axis 2 is transverse in the ply plane and axis
    3 is the through-thickness direction. Engineering shear strain ``gamma12``
    is used in all public vectors.
    """

    E1: float
    E2: float
    nu12: float
    G12: float
    density: float = 0.0
    G13: float | None = None
    G23: float | None = None

    def __post_init__(self) -> None:
        values = (self.E1, self.E2, self.nu12, self.G12, self.density)
        if not all(isfinite(value) for value in values):
            raise ValueError("Orthotropic lamina constants must be finite.")
        if self.E1 <= 0.0 or self.E2 <= 0.0 or self.G12 <= 0.0:
            raise ValueError("E1, E2 and G12 must be positive.")
        if self.density < 0.0:
            raise ValueError("density must be non-negative.")
        if self.reciprocity_denominator <= 0.0:
            raise ValueError("Orthotropic constants must satisfy 1 - nu12 * nu21 > 0.")
        if (self.G13 is None) != (self.G23 is None):
            raise ValueError("G13 and G23 must be defined together.")
        if self.G13 is not None and (
            not isfinite(self.G13) or not isfinite(self.G23) or self.G13 <= 0.0 or self.G23 <= 0.0
        ):
            raise ValueError("G13 and G23 must be positive and finite when provided.")

    @property
    def nu21(self) -> float:
        """Return the reciprocal Poisson ratio imposed by elastic symmetry."""
        return self.nu12 * self.E2 / self.E1

    @property
    def reciprocity_denominator(self) -> float:
        return 1.0 - self.nu12 * self.nu21

    @property
    def reduced_stiffness(self) -> np.ndarray:
        """Return the material-axis plane-stress matrix ``Q``."""
        denominator = self.reciprocity_denominator
        return np.array(
            [
                [self.E1 / denominator, self.nu12 * self.E2 / denominator, 0.0],
                [self.nu12 * self.E2 / denominator, self.E2 / denominator, 0.0],
                [0.0, 0.0, self.G12],
            ],
            dtype=float,
        )

    def transformed_stiffness(self, angle_deg: float) -> np.ndarray:
        """Return ``Qbar`` in element axes for a counter-clockwise ply angle."""
        transform = _material_basis(angle_deg)
        columns: list[np.ndarray] = []
        for strain in np.eye(3):
            local_strain = _strain_vector(transform.T @ _strain_tensor(strain) @ transform)
            local_stress = self.reduced_stiffness @ local_strain
            global_stress = transform @ _stress_tensor(local_stress) @ transform.T
            columns.append(_stress_vector(global_stress))
        matrix = np.column_stack(columns)
        return 0.5 * (matrix + matrix.T)

    def strain_in_material_axes(self, strain: np.ndarray, angle_deg: float) -> np.ndarray:
        """Transform element engineering strain to material axes 1-2."""
        values = _vector3(strain, "strain")
        transform = _material_basis(angle_deg)
        return _strain_vector(transform.T @ _strain_tensor(values) @ transform)

    def stress_in_element_axes(self, strain: np.ndarray, angle_deg: float) -> np.ndarray:
        """Evaluate stress in element axes for an element-axis strain."""
        values = _vector3(strain, "strain")
        return self.transformed_stiffness(angle_deg) @ values

    def transformed_transverse_shear(self, angle_deg: float) -> np.ndarray:
        """Return the rotated ``G13/G23`` transverse-shear matrix."""
        if self.G13 is None or self.G23 is None:
            raise ValueError("Transverse shear requires positive G13 and G23 values.")
        transform = _material_basis(angle_deg)
        matrix = transform @ np.diag([self.G13, self.G23]) @ transform.T
        return 0.5 * (matrix + matrix.T)


def _material_basis(angle_deg: float) -> np.ndarray:
    if not isfinite(angle_deg):
        raise ValueError("Ply angle must be finite.")
    angle = radians(angle_deg)
    m = cos(angle)
    n = sin(angle)
    return np.array([[m, -n], [n, m]], dtype=float)


def _vector3(value: np.ndarray, name: str) -> np.ndarray:
    values = np.asarray(value, dtype=float)
    if values.shape != (3,) or not np.all(np.isfinite(values)):
        raise ValueError(f"{name} must contain three finite components.")
    return values


def _strain_tensor(vector: np.ndarray) -> np.ndarray:
    return np.array([[vector[0], 0.5 * vector[2]], [0.5 * vector[2], vector[1]]], dtype=float)


def _strain_vector(tensor: np.ndarray) -> np.ndarray:
    return np.array([tensor[0, 0], tensor[1, 1], 2.0 * tensor[0, 1]], dtype=float)


def _stress_tensor(vector: np.ndarray) -> np.ndarray:
    return np.array([[vector[0], vector[2]], [vector[2], vector[1]]], dtype=float)


def _stress_vector(tensor: np.ndarray) -> np.ndarray:
    return np.array([tensor[0, 0], tensor[1, 1], tensor[0, 1]], dtype=float)
