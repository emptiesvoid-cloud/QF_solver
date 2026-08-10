"""Discrete spring and concentrated-mass mechanics."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from solveur.core.dofs import DOF_ORDER, TRANSLATION_DOFS
from solveur.core.errors import InputValidationError

ROTATION_DOFS = DOF_ORDER[3:]


@dataclass(frozen=True)
class SpringDefinition:
    """Linear generalized spring connected to ground or a second node."""

    node_a: int
    dofs: tuple[str, ...]
    stiffness: tuple[tuple[float, ...], ...]
    node_b: int | None = None
    coordinate_system: str = "global"
    orientation: tuple[tuple[float, float, float], ...] | None = None

    def active_dofs(self) -> tuple[str, ...]:
        if self.coordinate_system == "global":
            return self.dofs
        active: list[str] = []
        if any(name in TRANSLATION_DOFS for name in self.dofs):
            active.extend(TRANSLATION_DOFS)
        if any(name in ROTATION_DOFS for name in self.dofs):
            active.extend(ROTATION_DOFS)
        return tuple(active)

    def nodal_stiffness(self) -> np.ndarray:
        """Return the 6x6 spring matrix expressed in global nodal axes."""
        local = np.asarray(self.stiffness, dtype=float)
        expected = (len(self.dofs), len(self.dofs))
        if local.shape != expected:
            raise InputValidationError(f"Spring stiffness matrix must have shape {expected}.")
        if not np.all(np.isfinite(local)) or not np.allclose(local, local.T, rtol=0.0, atol=1.0e-12):
            raise InputValidationError("Spring stiffness matrix must be finite and symmetric.")
        if np.min(np.linalg.eigvalsh(local)) < -1.0e-12:
            raise InputValidationError("Spring stiffness matrix must be positive semidefinite.")
        basis = np.zeros((6, len(self.dofs)), dtype=float)
        rotation = self.rotation_matrix()
        for column, name in enumerate(self.dofs):
            component = DOF_ORDER.index(name)
            if self.coordinate_system == "global":
                basis[component, column] = 1.0
            elif component < 3:
                basis[:3, column] = rotation[:, component]
            else:
                basis[3:, column] = rotation[:, component - 3]
        return _symmetrize(basis @ local @ basis.T)

    def rotation_matrix(self) -> np.ndarray:
        if self.coordinate_system == "global":
            return np.eye(3)
        if self.orientation is None:
            raise InputValidationError("A local spring requires a 3x3 orientation matrix.")
        rotation = np.asarray(self.orientation, dtype=float)
        if rotation.shape != (3, 3):
            raise InputValidationError("Spring orientation must be a 3x3 matrix.")
        if not np.allclose(rotation.T @ rotation, np.eye(3), rtol=0.0, atol=1.0e-10):
            raise InputValidationError("Spring orientation must be orthonormal.")
        if np.linalg.det(rotation) <= 0.0:
            raise InputValidationError("Spring orientation must be right-handed.")
        return rotation


@dataclass(frozen=True)
class ConcentratedMass:
    """Rigid nodal mass with optional center-of-mass offset and inertia."""

    node: int
    mass: float
    center_of_mass: tuple[float, float, float] = (0.0, 0.0, 0.0)
    inertia: tuple[tuple[float, float, float], ...] | None = None

    def active_dofs(self) -> tuple[str, ...]:
        rotational = self.inertia is not None or np.linalg.norm(self.center_of_mass) > 0.0
        return DOF_ORDER if rotational else TRANSLATION_DOFS

    def matrix(self) -> np.ndarray:
        """Return translational or 6x6 spatial inertia at the attachment node."""
        if self.mass <= 0.0 or not np.isfinite(self.mass):
            raise InputValidationError("Concentrated mass must be finite and strictly positive.")
        if self.active_dofs() == TRANSLATION_DOFS:
            return self.mass * np.eye(3)
        center = np.asarray(self.center_of_mass, dtype=float)
        if center.shape != (3,) or not np.all(np.isfinite(center)):
            raise InputValidationError("Concentrated-mass center_of_mass must contain three finite values.")
        inertia = np.zeros((3, 3), dtype=float) if self.inertia is None else np.asarray(self.inertia, dtype=float)
        if inertia.shape != (3, 3) or not np.allclose(inertia, inertia.T, rtol=0.0, atol=1.0e-12):
            raise InputValidationError("Concentrated-mass inertia must be a symmetric 3x3 matrix.")
        moments = np.linalg.eigvalsh(inertia)
        if np.min(moments) < -1.0e-12:
            raise InputValidationError("Concentrated-mass inertia must be positive semidefinite.")
        tolerance = max(1.0, float(np.max(abs(moments)))) * 1.0e-12
        if moments[-1] > moments[0] + moments[1] + tolerance:
            raise InputValidationError(
                "Concentrated-mass inertia violates the principal-moment triangle inequality."
            )
        skew = np.array(
            [
                [0.0, -center[2], center[1]],
                [center[2], 0.0, -center[0]],
                [-center[1], center[0], 0.0],
            ]
        )
        matrix = np.zeros((6, 6), dtype=float)
        matrix[:3, :3] = self.mass * np.eye(3)
        matrix[:3, 3:] = -self.mass * skew
        matrix[3:, :3] = self.mass * skew
        matrix[3:, 3:] = inertia + self.mass * skew.T @ skew
        return _symmetrize(matrix)


def _symmetrize(matrix: np.ndarray) -> np.ndarray:
    return 0.5 * (matrix + matrix.T)
