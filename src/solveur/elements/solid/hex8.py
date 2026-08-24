"""Eight-node isoparametric hexahedral solid element."""

from __future__ import annotations

import numpy as np

from solveur.elements.solid.common import (
    strain_displacement_from_gradients,
    symmetrize,
    validate_coords_shape,
    von_mises_3d,
)
from solveur.materials.solid import SolidConstitutiveMaterial

_GAUSS_COORDINATE = 1.0 / np.sqrt(3.0)


class Hex8Element:
    """Trilinear HEX8 element with complete 2x2x2 Gauss integration."""

    integration_point_count = 8
    node_signs = np.asarray(
        (
            (-1.0, -1.0, -1.0),
            (1.0, -1.0, -1.0),
            (1.0, 1.0, -1.0),
            (-1.0, 1.0, -1.0),
            (-1.0, -1.0, 1.0),
            (1.0, -1.0, 1.0),
            (1.0, 1.0, 1.0),
            (-1.0, 1.0, 1.0),
        ),
        dtype=float,
    )
    integration_points = tuple(
        tuple(float(value) for value in point)
        for point in (
            (sx * _GAUSS_COORDINATE, sy * _GAUSS_COORDINATE, sz * _GAUSS_COORDINATE)
            for sx in (-1.0, 1.0)
            for sy in (-1.0, 1.0)
            for sz in (-1.0, 1.0)
        )
    )

    def __init__(self, material: SolidConstitutiveMaterial):
        self.material = material

    @staticmethod
    def shape_functions(point: tuple[float, float, float] | np.ndarray) -> np.ndarray:
        """Return trilinear shape functions in the [-1, 1]^3 domain."""
        xi, eta, zeta = np.asarray(point, dtype=float)
        if np.any(np.abs((xi, eta, zeta)) > 1.0 + 1.0e-12):
            raise ValueError("HEX8 reference coordinates must lie in [-1, 1].")
        signs = Hex8Element.node_signs
        return 0.125 * (1.0 + signs[:, 0] * xi) * (1.0 + signs[:, 1] * eta) * (1.0 + signs[:, 2] * zeta)

    @staticmethod
    def shape_derivatives_reference(point: tuple[float, float, float] | np.ndarray) -> np.ndarray:
        """Return dN/d(xi, eta, zeta) for all eight nodes."""
        xi, eta, zeta = np.asarray(point, dtype=float)
        signs = Hex8Element.node_signs
        values = np.empty((8, 3), dtype=float)
        values[:, 0] = 0.125 * signs[:, 0] * (1.0 + signs[:, 1] * eta) * (1.0 + signs[:, 2] * zeta)
        values[:, 1] = 0.125 * signs[:, 1] * (1.0 + signs[:, 0] * xi) * (1.0 + signs[:, 2] * zeta)
        values[:, 2] = 0.125 * signs[:, 2] * (1.0 + signs[:, 0] * xi) * (1.0 + signs[:, 1] * eta)
        return values

    @staticmethod
    def _validated_coords(coords: np.ndarray) -> np.ndarray:
        return validate_coords_shape(coords, (8, 3), "HEX8")

    @classmethod
    def jacobian(cls, coords: np.ndarray, point: tuple[float, float, float] | np.ndarray) -> np.ndarray:
        coords = cls._validated_coords(coords)
        return cls.shape_derivatives_reference(point).T @ coords

    @classmethod
    def jacobian_determinant(cls, coords: np.ndarray, point: tuple[float, float, float] | np.ndarray) -> float:
        return float(np.linalg.det(cls.jacobian(coords, point)))

    @classmethod
    def validate_geometry(cls, coords: np.ndarray) -> None:
        """Reject inverted, degenerate or locally folded HEX8 geometry."""
        coords = cls._validated_coords(coords)
        span = max(float(np.max(np.ptp(coords, axis=0))), 1.0)
        tolerance = 1.0e-14 * span**3
        determinants = np.asarray([cls.jacobian_determinant(coords, point) for point in cls.integration_points])
        if np.any(determinants <= tolerance):
            minimum = float(np.min(determinants))
            raise ValueError(f"Invalid HEX8 Jacobian determinant {minimum:.6e}.")

    @classmethod
    def b_matrix(cls, coords: np.ndarray, point: tuple[float, float, float] | np.ndarray) -> tuple[np.ndarray, float]:
        cls.validate_geometry(coords)
        jacobian = cls.jacobian(coords, point)
        determinant = float(np.linalg.det(jacobian))
        gradients = cls.shape_derivatives_reference(point) @ np.linalg.inv(jacobian).T
        return strain_displacement_from_gradients(gradients), determinant

    @classmethod
    def integration_data(cls, coords: np.ndarray) -> tuple[tuple[tuple[float, float, float], float, np.ndarray, float], ...]:
        cls.validate_geometry(coords)
        data = []
        for point in cls.integration_points:
            b_matrix, determinant = cls.b_matrix(coords, point)
            data.append((point, 1.0, b_matrix, determinant))
        return tuple(data)

    def stiffness(self, coords: np.ndarray) -> np.ndarray:
        stiffness = np.zeros((24, 24), dtype=float)
        for _, weight, b_matrix, determinant in self.integration_data(coords):
            stiffness += weight * determinant * (b_matrix.T @ self.material.elasticity_matrix @ b_matrix)
        return symmetrize(stiffness)

    def internal_force_tangent_state(
        self,
        coords: np.ndarray,
        local_displacement: np.ndarray,
        states: list[dict[str, object]] | None = None,
    ) -> tuple[np.ndarray, np.ndarray, list[dict[str, object]]]:
        displacement = np.asarray(local_displacement, dtype=float)
        if displacement.shape != (24,):
            raise ValueError("HEX8 local displacement must have shape (24,).")
        internal = np.zeros(24, dtype=float)
        tangent = np.zeros((24, 24), dtype=float)
        updated_states: list[dict[str, object]] = []
        for point_index, (_, weight, b_matrix, determinant) in enumerate(self.integration_data(coords)):
            strain = b_matrix @ displacement
            if hasattr(self.material, "stress_tangent_state"):
                previous = states[point_index] if states and point_index < len(states) else None
                stress, material_tangent, updated = self.material.stress_tangent_state(strain, previous)
                updated_states.append(updated)
            else:
                stress, material_tangent = self.material.stress_tangent(strain)
            internal += weight * determinant * (b_matrix.T @ stress)
            tangent += weight * determinant * (b_matrix.T @ material_tangent @ b_matrix)
        return internal, symmetrize(tangent), updated_states

    def internal_force_and_tangent(self, coords: np.ndarray, local_displacement: np.ndarray, states=None):
        internal, tangent, _ = self.internal_force_tangent_state(coords, local_displacement, states)
        return internal, tangent

    def mass(self, coords: np.ndarray) -> np.ndarray:
        if self.material.density <= 0.0:
            raise ValueError("HEX8 modal analysis requires a positive material density.")
        mass = np.zeros((24, 24), dtype=float)
        identity = np.eye(3)
        for point, weight, _, determinant in self.integration_data(coords):
            shape = self.shape_functions(point)
            mass += self.material.density * weight * determinant * np.kron(np.outer(shape, shape), identity)
        return symmetrize(mass)

    def mass_lumped(self, coords: np.ndarray) -> np.ndarray:
        """Return the row-sum lumped mass as a diagonal matrix."""
        consistent = self.mass(coords)
        return np.diag(np.sum(consistent, axis=1))

    def strain_at(self, coords: np.ndarray, local_displacement: np.ndarray, point) -> np.ndarray:
        b_matrix, _ = self.b_matrix(coords, point)
        return b_matrix @ np.asarray(local_displacement, dtype=float)

    def stress_at(self, coords: np.ndarray, local_displacement: np.ndarray, point) -> np.ndarray:
        strain = self.strain_at(coords, local_displacement, point)
        return self.material.stress_tangent(strain)[0]

    def strain(self, coords: np.ndarray, local_displacement: np.ndarray) -> np.ndarray:
        return self.strain_at(coords, local_displacement, (0.0, 0.0, 0.0))

    def stress(self, coords: np.ndarray, local_displacement: np.ndarray) -> np.ndarray:
        return self.material.stress_tangent(self.strain(coords, local_displacement))[0]

    @classmethod
    def integration_points_results(cls, coords: np.ndarray, local_displacement: np.ndarray, material) -> list[dict[str, object]]:
        element = cls(material)
        rows = []
        for index, point in enumerate(cls.integration_points):
            shape = cls.shape_functions(point)
            strain = element.strain_at(coords, local_displacement, point)
            stress = material.stress_tangent(strain)[0]
            rows.append({
                "index": index,
                "location": "gauss",
                "natural_coordinates": list(point),
                "coordinates": (shape @ np.asarray(coords, dtype=float)).tolist(),
                "weight": cls.jacobian_determinant(coords, point),
                "strain": strain.tolist(),
                "stress": stress.tolist(),
                "von_mises": cls.von_mises(stress),
            })
        return rows

    @staticmethod
    def von_mises(stress: np.ndarray) -> float:
        return von_mises_3d(stress)
