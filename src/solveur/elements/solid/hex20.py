"""Quadratic twenty-node isoparametric hexahedral solid element."""

from __future__ import annotations

import numpy as np

from solveur.core.nonlinear_contracts import evaluate_constitutive
from solveur.elements.solid.common import (
    strain_displacement_from_gradients,
    symmetrize,
    validate_coords_shape,
    von_mises_3d,
)
from solveur.materials.solid import SolidConstitutiveMaterial


_GAUSS_ABSCISSA = np.sqrt(3.0 / 5.0)
_GAUSS_1D = ((_GAUSS_ABSCISSA, 5.0 / 9.0), (0.0, 8.0 / 9.0), (_GAUSS_ABSCISSA * -1.0, 5.0 / 9.0))


class Hex20Element:
    """Serendipity HEX20 element with complete 3x3x3 Gauss integration.

    The local ordering follows Gmsh's second-order incomplete hexahedron:
    eight corner nodes followed by twelve mid-edge nodes.  The edge nodes
    are ordered as returned by ``gmsh.model.mesh.getElementProperties(17)``.
    """

    integration_points: tuple[tuple[float, float, float], ...]
    integration_weights: tuple[float, ...]
    integration_point_count = 27
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
    # For each edge node: free coordinate axis, fixed axes, fixed signs.
    edge_data = (
        (0, (1, 2), (-1.0, -1.0)),
        (1, (0, 2), (-1.0, -1.0)),
        (2, (0, 1), (-1.0, -1.0)),
        (1, (0, 2), (1.0, -1.0)),
        (2, (0, 1), (1.0, -1.0)),
        (0, (1, 2), (1.0, -1.0)),
        (2, (0, 1), (1.0, 1.0)),
        (2, (0, 1), (-1.0, 1.0)),
        (0, (1, 2), (-1.0, 1.0)),
        (1, (0, 2), (-1.0, 1.0)),
        (1, (0, 2), (1.0, 1.0)),
        (0, (1, 2), (1.0, 1.0)),
    )

    def __init__(self, material: SolidConstitutiveMaterial):
        self.material = material

    @staticmethod
    def _validated_point(point: tuple[float, float, float] | np.ndarray) -> np.ndarray:
        values = np.asarray(point, dtype=float)
        if values.shape != (3,) or np.any(np.abs(values) > 1.0 + 1.0e-12):
            raise ValueError("HEX20 reference coordinates must lie in [-1, 1].")
        return values

    @classmethod
    def _build_integration_rule(cls) -> tuple[tuple[tuple[float, float, float], ...], tuple[float, ...]]:
        points: list[tuple[float, float, float]] = []
        weights: list[float] = []
        for xi, weight_xi in _GAUSS_1D:
            for eta, weight_eta in _GAUSS_1D:
                for zeta, weight_zeta in _GAUSS_1D:
                    points.append((float(xi), float(eta), float(zeta)))
                    weights.append(float(weight_xi * weight_eta * weight_zeta))
        return tuple(points), tuple(weights)

    @classmethod
    def shape_functions(cls, point: tuple[float, float, float] | np.ndarray) -> np.ndarray:
        """Return the quadratic serendipity shape functions."""
        values_point = cls._validated_point(point)
        values = np.zeros(20, dtype=float)
        for index, signs in enumerate(cls.node_signs):
            factors = 1.0 + signs * values_point
            values[index] = 0.125 * float(np.prod(factors)) * (float(signs @ values_point) - 2.0)
        for index, (free_axis, fixed_axes, fixed_signs) in enumerate(cls.edge_data, start=8):
            fixed_product = float(np.prod([1.0 + sign * values_point[axis] for axis, sign in zip(fixed_axes, fixed_signs)]))
            values[index] = 0.25 * fixed_product * (1.0 - values_point[free_axis] ** 2)
        return values

    @classmethod
    def shape_derivatives_reference(cls, point: tuple[float, float, float] | np.ndarray) -> np.ndarray:
        """Return derivatives with respect to the three reference coordinates."""
        values_point = cls._validated_point(point)
        derivatives = np.zeros((20, 3), dtype=float)
        for index, signs in enumerate(cls.node_signs):
            factors = 1.0 + signs * values_point
            product = float(np.prod(factors))
            linear = float(signs @ values_point) - 2.0
            for axis in range(3):
                other_product = float(np.prod(np.delete(factors, axis)))
                derivatives[index, axis] = 0.125 * signs[axis] * (other_product * linear + product)
        for index, (free_axis, fixed_axes, fixed_signs) in enumerate(cls.edge_data, start=8):
            free_value = values_point[free_axis]
            fixed_factors = {
                axis: 1.0 + sign * values_point[axis]
                for axis, sign in zip(fixed_axes, fixed_signs)
            }
            fixed_product = float(np.prod(tuple(fixed_factors.values())))
            derivatives[index, free_axis] = -0.5 * fixed_product * free_value
            for axis, sign in zip(fixed_axes, fixed_signs):
                other = float(np.prod([fixed_factors[item] for item in fixed_axes if item != axis]))
                derivatives[index, axis] = 0.25 * sign * other * (1.0 - free_value**2)
        return derivatives

    @staticmethod
    def _validated_coords(coords: np.ndarray) -> np.ndarray:
        return validate_coords_shape(coords, (20, 3), "HEX20")

    @classmethod
    def jacobian(cls, coords: np.ndarray, point: tuple[float, float, float] | np.ndarray) -> np.ndarray:
        coords = cls._validated_coords(coords)
        return cls.shape_derivatives_reference(point).T @ coords

    @classmethod
    def jacobian_determinant(cls, coords: np.ndarray, point: tuple[float, float, float] | np.ndarray) -> float:
        return float(np.linalg.det(cls.jacobian(coords, point)))

    @classmethod
    def validate_geometry(cls, coords: np.ndarray) -> None:
        """Reject inverted, degenerate or locally folded HEX20 geometry."""
        coords = cls._validated_coords(coords)
        span = max(float(np.max(np.ptp(coords, axis=0))), 1.0)
        tolerance = 1.0e-14 * span**3
        determinants = np.asarray(
            [cls.jacobian_determinant(coords, point) for point in cls.integration_points],
            dtype=float,
        )
        if not np.all(np.isfinite(determinants)) or np.any(determinants <= tolerance):
            minimum = float(np.min(determinants))
            raise ValueError(f"Invalid HEX20 Jacobian determinant {minimum:.6e}.")

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
        return tuple(
            (point, weight, *cls.b_matrix(coords, point))
            for point, weight in zip(cls.integration_points, cls.integration_weights)
        )

    def stiffness(self, coords: np.ndarray) -> np.ndarray:
        stiffness = np.zeros((60, 60), dtype=float)
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
        if displacement.shape != (60,):
            raise ValueError("HEX20 local displacement must have shape (60,).")
        internal = np.zeros(60, dtype=float)
        tangent = np.zeros((60, 60), dtype=float)
        updated_states: list[dict[str, object]] = []
        for point_index, (_, weight, b_matrix, determinant) in enumerate(self.integration_data(coords)):
            strain = b_matrix @ displacement
            previous = states[point_index] if states and point_index < len(states) else None
            response = evaluate_constitutive(self.material, strain, previous)
            stress, material_tangent = response.stress, response.tangent
            if response.diagnostics.get("stateful", False):
                updated_states.append(response.trial_state)
            internal += weight * determinant * (b_matrix.T @ stress)
            tangent += weight * determinant * (b_matrix.T @ material_tangent @ b_matrix)
        return internal, symmetrize(tangent), updated_states

    def internal_force_and_tangent(
        self,
        coords: np.ndarray,
        local_displacement: np.ndarray,
        states: list[dict[str, object]] | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        internal, tangent, _ = self.internal_force_tangent_state(coords, local_displacement, states)
        return internal, tangent

    def mass(self, coords: np.ndarray) -> np.ndarray:
        if self.material.density <= 0.0:
            raise ValueError("HEX20 modal analysis requires a positive material density.")
        mass = np.zeros((60, 60), dtype=float)
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
            rows.append(
                {
                    "index": index,
                    "location": "gauss",
                    "natural_coordinates": list(point),
                    "coordinates": (shape @ np.asarray(coords, dtype=float)).tolist(),
                    "weight": cls.integration_weights[index] * cls.jacobian_determinant(coords, point),
                    "strain": strain.tolist(),
                    "stress": stress.tolist(),
                    "von_mises": cls.von_mises(stress),
                }
            )
        return rows

    @staticmethod
    def von_mises(stress: np.ndarray) -> float:
        return von_mises_3d(stress)


Hex20Element.integration_points, Hex20Element.integration_weights = Hex20Element._build_integration_rule()
