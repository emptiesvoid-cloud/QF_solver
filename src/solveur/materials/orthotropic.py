"""Small-strain oriented orthotropic elasticity for three-dimensional solids."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any

import numpy as np


@dataclass(frozen=True)
class OrthotropicSolidMaterial:
    """Linear orthotropic solid with material axes expressed in global coordinates."""

    E1: float
    E2: float
    E3: float
    nu12: float
    nu13: float
    nu23: float
    G12: float
    G13: float
    G23: float
    density: float = 0.0
    orientation: np.ndarray = field(default_factory=lambda: np.eye(3))
    material_type: str = "orthotropic_3d"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        constants = np.array(
            [self.E1, self.E2, self.E3, self.G12, self.G13, self.G23],
            dtype=float,
        )
        poissons = np.array([self.nu12, self.nu13, self.nu23], dtype=float)
        if not np.all(np.isfinite(constants)) or np.any(constants <= 0.0):
            raise ValueError("Orthotropic elastic and shear moduli must be finite and positive.")
        if not np.all(np.isfinite(poissons)):
            raise ValueError("Orthotropic Poisson ratios must be finite.")
        if not np.isfinite(self.density) or self.density < 0.0:
            raise ValueError("Density must be finite and non-negative.")
        basis = validate_material_orientation(self.orientation)
        object.__setattr__(self, "orientation", basis)
        if self.material_type not in {"orthotropic_3d", "composite_orthotropic_3d"}:
            raise ValueError(f"Unsupported orthotropic solid material type {self.material_type!r}.")
        eigenvalues = np.linalg.eigvalsh(self.compliance_matrix)
        if float(np.min(eigenvalues)) <= 0.0:
            raise ValueError("Orthotropic compliance matrix must be positive definite.")

    @property
    def nu21(self) -> float:
        return self.nu12 * self.E2 / self.E1

    @property
    def nu31(self) -> float:
        return self.nu13 * self.E3 / self.E1

    @property
    def nu32(self) -> float:
        return self.nu23 * self.E3 / self.E2

    @cached_property
    def compliance_matrix(self) -> np.ndarray:
        """Return material-axis compliance using engineering shear strains."""
        matrix = np.zeros((6, 6), dtype=float)
        matrix[0, 0] = 1.0 / self.E1
        matrix[1, 1] = 1.0 / self.E2
        matrix[2, 2] = 1.0 / self.E3
        matrix[0, 1] = matrix[1, 0] = -self.nu12 / self.E1
        matrix[0, 2] = matrix[2, 0] = -self.nu13 / self.E1
        matrix[1, 2] = matrix[2, 1] = -self.nu23 / self.E2
        matrix[3, 3] = 1.0 / self.G12
        matrix[4, 4] = 1.0 / self.G23
        matrix[5, 5] = 1.0 / self.G13
        return matrix

    @cached_property
    def material_elasticity_matrix(self) -> np.ndarray:
        """Return the material-axis stiffness without repeated explicit inversion."""
        identity = np.eye(6)
        matrix = np.linalg.solve(self.compliance_matrix, identity)
        return 0.5 * (matrix + matrix.T)

    @cached_property
    def elasticity_matrix(self) -> np.ndarray:
        """Return the global-axis stiffness with exact engineering-shear mapping."""
        matrix = np.empty((6, 6), dtype=float)
        for column in range(6):
            global_strain = np.zeros(6, dtype=float)
            global_strain[column] = 1.0
            local_strain = self.strain_material_axes(global_strain)
            local_stress = self.material_elasticity_matrix @ local_strain
            matrix[:, column] = self.stress_global_axes(local_stress)
        return 0.5 * (matrix + matrix.T)

    def stress_tangent(self, strain: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        tangent = self.elasticity_matrix
        return tangent @ np.asarray(strain, dtype=float), tangent

    def strain_material_axes(self, global_strain: np.ndarray) -> np.ndarray:
        tensor = strain_voigt_to_tensor(global_strain)
        return strain_tensor_to_voigt(self.orientation.T @ tensor @ self.orientation)

    def stress_material_axes(self, global_stress: np.ndarray) -> np.ndarray:
        tensor = stress_voigt_to_tensor(global_stress)
        return stress_tensor_to_voigt(self.orientation.T @ tensor @ self.orientation)

    def strain_global_axes(self, material_strain: np.ndarray) -> np.ndarray:
        tensor = strain_voigt_to_tensor(material_strain)
        return strain_tensor_to_voigt(self.orientation @ tensor @ self.orientation.T)

    def stress_global_axes(self, material_stress: np.ndarray) -> np.ndarray:
        tensor = stress_voigt_to_tensor(material_stress)
        return stress_tensor_to_voigt(self.orientation @ tensor @ self.orientation.T)


def material_orientation(
    orientation: object | None = None,
    e1: object | None = None,
    e2_hint: object | None = None,
) -> np.ndarray:
    """Build a right-handed material basis whose columns are e1, e2 and e3."""
    if orientation is not None:
        if e1 is not None or e2_hint is not None:
            raise ValueError("Define either orientation or e1/e2_hint, not both.")
        return validate_material_orientation(np.asarray(orientation, dtype=float))
    if (e1 is None) != (e2_hint is None):
        raise ValueError("Material orientation requires e1 and e2_hint together.")
    if e1 is None:
        return np.eye(3)
    first = _normalized_direction(e1, "e1")
    hint = np.asarray(e2_hint, dtype=float)
    if hint.shape != (3,) or not np.all(np.isfinite(hint)):
        raise ValueError("e2_hint must contain three finite values.")
    second_raw = hint - float(hint @ first) * first
    second = _normalized_direction(second_raw, "e2_hint orthogonal component")
    third = np.cross(first, second)
    return validate_material_orientation(np.column_stack((first, second, third)))


def cylindrical_tangent_orientation(coordinates: object, definition: Mapping[str, object]) -> np.ndarray:
    """Build a material basis tangent to a cylindrical field at an element centroid.

    The material axis ``e1`` follows the circumferential direction, ``e2`` the
    cylinder axis and ``e3`` the outward radial direction.  The field is
    evaluated once per linear material element; it is therefore appropriate for
    sufficiently refined curved solids, not for arbitrary fibre steering inside
    a single element.
    """
    if str(definition.get("type", "")).lower() != "cylindrical_tangent":
        raise ValueError("Unsupported orientation_field type; expected 'cylindrical_tangent'.")
    points = np.asarray(coordinates, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or points.shape[0] < 4 or not np.all(np.isfinite(points)):
        raise ValueError("orientation_field requires finite element coordinates with shape (n, 3).")
    origin = _finite_vector(definition.get("origin"), "orientation_field.origin")
    axis = _normalized_direction(definition.get("axis"), "orientation_field.axis")
    center = np.mean(points, axis=0)
    radial = center - origin
    radial -= float(radial @ axis) * axis
    radial = _normalized_direction(radial, "orientation_field radial direction")
    circumferential = _normalized_direction(np.cross(axis, radial), "orientation_field circumferential direction")
    return validate_material_orientation(np.column_stack((circumferential, axis, radial)))


def validate_material_orientation(values: np.ndarray) -> np.ndarray:
    matrix = np.asarray(values, dtype=float)
    if matrix.shape != (3, 3) or not np.all(np.isfinite(matrix)):
        raise ValueError("Material orientation must be a finite 3x3 matrix.")
    if not np.allclose(matrix.T @ matrix, np.eye(3), rtol=0.0, atol=1.0e-10):
        raise ValueError("Material orientation must be orthonormal.")
    determinant = float(np.linalg.det(matrix))
    if determinant <= 0.0 or not np.isclose(determinant, 1.0, rtol=0.0, atol=1.0e-10):
        raise ValueError("Material orientation must be right-handed with determinant +1.")
    output = matrix.copy()
    output.setflags(write=False)
    return output


def strain_voigt_to_tensor(values: np.ndarray) -> np.ndarray:
    e1, e2, e3, g12, g23, g13 = np.asarray(values, dtype=float)
    return np.array(
        [[e1, 0.5 * g12, 0.5 * g13], [0.5 * g12, e2, 0.5 * g23], [0.5 * g13, 0.5 * g23, e3]],
        dtype=float,
    )


def strain_tensor_to_voigt(values: np.ndarray) -> np.ndarray:
    return np.array(
        [values[0, 0], values[1, 1], values[2, 2], 2.0 * values[0, 1], 2.0 * values[1, 2], 2.0 * values[0, 2]],
        dtype=float,
    )


def stress_voigt_to_tensor(values: np.ndarray) -> np.ndarray:
    s1, s2, s3, t12, t23, t13 = np.asarray(values, dtype=float)
    return np.array([[s1, t12, t13], [t12, s2, t23], [t13, t23, s3]], dtype=float)


def stress_tensor_to_voigt(values: np.ndarray) -> np.ndarray:
    return np.array(
        [values[0, 0], values[1, 1], values[2, 2], values[0, 1], values[1, 2], values[0, 2]],
        dtype=float,
    )


def _normalized_direction(values: object, name: str) -> np.ndarray:
    vector = np.asarray(values, dtype=float)
    if vector.shape != (3,) or not np.all(np.isfinite(vector)):
        raise ValueError(f"{name} must contain three finite values.")
    norm = float(np.linalg.norm(vector))
    if norm <= 1.0e-14:
        raise ValueError(f"{name} must be non-zero.")
    return vector / norm


def _finite_vector(values: object, name: str) -> np.ndarray:
    vector = np.asarray(values, dtype=float)
    if vector.shape != (3,) or not np.all(np.isfinite(vector)):
        raise ValueError(f"{name} must contain three finite values.")
    return vector
