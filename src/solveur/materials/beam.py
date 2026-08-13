"""Isotropic section properties for two-node beam elements."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class BeamSectionMaterial:
    """Elastic isotropic beam section expressed in its local principal axes."""

    E: float
    G: float
    A: float
    Iy: float
    Iz: float
    J: float
    density: float = 0.0
    kappa_y: float = 5.0 / 6.0
    kappa_z: float = 5.0 / 6.0
    reference_vector: tuple[float, float, float] | None = None

    def __post_init__(self) -> None:
        for name in ("E", "G", "A", "Iy", "Iz", "J", "kappa_y", "kappa_z"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value <= 0.0:
                raise ValueError(f"Beam section {name} must be finite and positive.")
        if not np.isfinite(self.density) or self.density < 0.0:
            raise ValueError("Beam section density must be finite and non-negative.")
        if self.reference_vector is not None:
            vector = np.asarray(self.reference_vector, dtype=float)
            if vector.shape != (3,) or not np.all(np.isfinite(vector)):
                raise ValueError("Beam reference_vector must contain three finite values.")
            if np.linalg.norm(vector) <= 1.0e-14:
                raise ValueError("Beam reference_vector must be non-zero.")

    @property
    def mass_per_length(self) -> float:
        return float(self.density * self.A)

