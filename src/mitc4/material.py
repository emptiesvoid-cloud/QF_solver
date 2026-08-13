"""Material definitions for isotropic shell elements."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ShellMaterial:
    """Linear isotropic Reissner-Mindlin shell material."""

    E: float
    nu: float
    t: float
    shear_factor: float = 5.0 / 6.0
    drilling_scale: float = 1.0e-4
    density: float = 0.0

    def __post_init__(self) -> None:
        if self.E <= 0.0:
            raise ValueError("Young modulus E must be positive.")
        if not (-1.0 < self.nu < 0.5):
            raise ValueError("Poisson ratio nu must be in (-1, 0.5).")
        if self.t <= 0.0:
            raise ValueError("Shell thickness t must be positive.")
        if self.shear_factor <= 0.0:
            raise ValueError("shear_factor must be positive.")
        if self.drilling_scale < 0.0:
            raise ValueError("drilling_scale must be non-negative.")
        if self.density < 0.0:
            raise ValueError("density must be non-negative.")

    @property
    def G(self) -> float:
        return self.E / (2.0 * (1.0 + self.nu))

    @property
    def membrane_matrix(self) -> np.ndarray:
        return self.E * self.t / (1.0 - self.nu**2) * self._plane_stress_matrix()

    @property
    def bending_matrix(self) -> np.ndarray:
        return self.E * self.t**3 / (12.0 * (1.0 - self.nu**2)) * self._plane_stress_matrix()

    @property
    def shear_matrix(self) -> np.ndarray:
        return self.shear_factor * self.G * self.t * np.eye(2)

    @property
    def drilling_stiffness(self) -> float:
        return self.drilling_scale * self.E * self.t

    def _plane_stress_matrix(self) -> np.ndarray:
        return np.array(
            [
                [1.0, self.nu, 0.0],
                [self.nu, 1.0, 0.0],
                [0.0, 0.0, 0.5 * (1.0 - self.nu)],
            ],
            dtype=float,
        )
