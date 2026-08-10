"""Independent closed-form references used by qualification campaigns."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Tet4StaticClosedFormOracle:
    """Scalar oracle for the canonical constrained unit TET4.

    This class intentionally has no dependency on element, assembly or solver
    modules so that it can serve as an independent analytical comparator.
    """

    young_modulus: float
    poisson_ratio: float
    volume: float = 1.0 / 6.0

    def __post_init__(self) -> None:
        if not math.isfinite(self.young_modulus) or self.young_modulus <= 0.0:
            raise ValueError("young_modulus must be finite and positive.")
        if not math.isfinite(self.poisson_ratio) or not -1.0 < self.poisson_ratio < 0.5:
            raise ValueError("poisson_ratio must satisfy -1 < nu < 0.5.")
        if not math.isfinite(self.volume) or self.volume <= 0.0:
            raise ValueError("volume must be finite and positive.")

    @property
    def constrained_modulus(self) -> float:
        """Return lambda + 2 mu for the constrained uniaxial state."""
        young = self.young_modulus
        poisson = self.poisson_ratio
        return young * (1.0 - poisson) / ((1.0 + poisson) * (1.0 - 2.0 * poisson))

    def constrained_uniaxial(self, force_x: float) -> dict[str, float]:
        """Return displacement and stresses for one free axial corner dof."""
        if not math.isfinite(force_x) or force_x == 0.0:
            raise ValueError("force_x must be finite and non-zero.")
        displacement = force_x / (self.volume * self.constrained_modulus)
        stress_x = force_x / self.volume
        lateral_stress = self.poisson_ratio / (1.0 - self.poisson_ratio) * stress_x
        return {
            "ux": float(displacement),
            "stress_x": float(stress_x),
            "lateral_stress": float(lateral_stress),
            "von_mises": float(abs(stress_x - lateral_stress)),
        }

    def consistent_body_force_displacement(self, body_force_x: float) -> float:
        """Return the free-corner displacement under a constant body force."""
        if not math.isfinite(body_force_x) or body_force_x == 0.0:
            raise ValueError("body_force_x must be finite and non-zero.")
        nodal_force = body_force_x * self.volume / 4.0
        axial_stiffness = self.volume * self.constrained_modulus
        return float(nodal_force / axial_stiffness)
