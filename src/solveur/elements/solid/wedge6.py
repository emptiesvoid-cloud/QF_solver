"""Six-node triangular-prism solid element for the WP07 technical route."""

from __future__ import annotations

from math import sqrt
import numpy as np

from solveur.core.nonlinear.contracts import evaluate_constitutive
from solveur.elements.solid.common import (
    strain_displacement_from_gradients,
    symmetrize,
    validate_coords_shape,
    von_mises_3d,
)
from solveur.materials.solid import SolidConstitutiveMaterial
from solveur.mesh.quality_contract import wedge6_jacobian_certificate


_GAUSS2 = 1.0 / sqrt(3.0)
_TRI3_POINTS = (
    (1.0 / 6.0, 1.0 / 6.0),
    (2.0 / 3.0, 1.0 / 6.0),
    (1.0 / 6.0, 2.0 / 3.0),
)
_PRODUCTION_POINTS = tuple(
    (r, s, t)
    for r, s in _TRI3_POINTS
    for t in (-_GAUSS2, _GAUSS2)
)
_PRODUCTION_WEIGHTS = tuple(1.0 / 6.0 for _ in _PRODUCTION_POINTS)


def _duffy_reference_rule() -> tuple[tuple[tuple[float, float, float], float], ...]:
    square_points, square_weights = np.polynomial.legendre.leggauss(5)
    line_points, line_weights = np.polynomial.legendre.leggauss(4)
    points: list[tuple[tuple[float, float, float], float]] = []
    for square_r, weight_r in zip(square_points, square_weights, strict=True):
        r = 0.5 * (float(square_r) + 1.0)
        for square_s, weight_s in zip(square_points, square_weights, strict=True):
            s = (1.0 - r) * 0.5 * (float(square_s) + 1.0)
            triangle_weight = float(weight_r * weight_s * (1.0 - r) / 4.0)
            for t, weight_t in zip(line_points, line_weights, strict=True):
                points.append(((r, s, float(t)), triangle_weight * float(weight_t)))
    return tuple(points)


_REFERENCE_RULE = _duffy_reference_rule()


class Wedge6Element:
    """Linear six-node triangular-prism element with full integration.

    This is the WP07 technical kernel.  User-facing mesh import, face loads,
    reactions and qualification remain outside this route until later gates.
    """

    integration_point_count = 6
    reference_integration_point_count = 100
    node_count = 6
    dof_count = 18
    reference_nodes = np.asarray(
        (
            (0.0, 0.0, -1.0),
            (1.0, 0.0, -1.0),
            (0.0, 1.0, -1.0),
            (0.0, 0.0, 1.0),
            (1.0, 0.0, 1.0),
            (0.0, 1.0, 1.0),
        ),
        dtype=float,
    )
    integration_points = _PRODUCTION_POINTS
    integration_weights = _PRODUCTION_WEIGHTS
    reference_integration_points = tuple(point for point, _ in _REFERENCE_RULE)
    reference_integration_weights = tuple(weight for _, weight in _REFERENCE_RULE)

    def __init__(self, material: SolidConstitutiveMaterial):
        self.material = material

    @staticmethod
    def shape_functions(point: tuple[float, float, float] | np.ndarray) -> np.ndarray:
        """Return the six shape functions on the triangular-prism domain."""

        r, s, t = (float(value) for value in np.asarray(point, dtype=float))
        if r < -1.0e-12 or s < -1.0e-12 or r + s > 1.0 + 1.0e-12 or abs(t) > 1.0 + 1.0e-12:
            raise ValueError("WEDGE6 reference coordinates are outside the triangular-prism domain.")
        return np.asarray(
            (
                0.5 * (1.0 - t) * (1.0 - r - s),
                0.5 * (1.0 - t) * r,
                0.5 * (1.0 - t) * s,
                0.5 * (1.0 + t) * (1.0 - r - s),
                0.5 * (1.0 + t) * r,
                0.5 * (1.0 + t) * s,
            ),
            dtype=float,
        )

    @staticmethod
    def shape_derivatives_reference(point: tuple[float, float, float] | np.ndarray) -> np.ndarray:
        """Return dN/dr, dN/ds and dN/dt for all six nodes."""

        r, s, t = (float(value) for value in np.asarray(point, dtype=float))
        return np.asarray(
            (
                (-0.5 * (1.0 - t), -0.5 * (1.0 - t), -0.5 * (1.0 - r - s)),
                (0.5 * (1.0 - t), 0.0, -0.5 * r),
                (0.0, 0.5 * (1.0 - t), -0.5 * s),
                (-0.5 * (1.0 + t), -0.5 * (1.0 + t), 0.5 * (1.0 - r - s)),
                (0.5 * (1.0 + t), 0.0, 0.5 * r),
                (0.0, 0.5 * (1.0 + t), 0.5 * s),
            ),
            dtype=float,
        )

    @staticmethod
    def _validated_coords(coords: np.ndarray) -> np.ndarray:
        values = validate_coords_shape(coords, (6, 3), "WEDGE6")
        if not np.isfinite(values).all():
            raise ValueError("WEDGE6 coordinates must be finite.")
        return values

    @classmethod
    def jacobian(cls, coords: np.ndarray, point: tuple[float, float, float] | np.ndarray) -> np.ndarray:
        values = cls._validated_coords(coords)
        return cls.shape_derivatives_reference(point).T @ values

    @classmethod
    def jacobian_determinant(cls, coords: np.ndarray, point: tuple[float, float, float] | np.ndarray) -> float:
        return float(np.linalg.det(cls.jacobian(coords, point)))

    @staticmethod
    def _signed_volume_validated(coords: np.ndarray) -> float:
        determinants = np.asarray(
            [Wedge6Element.jacobian_determinant(coords, point) for point in Wedge6Element.integration_points],
            dtype=float,
        )
        return float(np.dot(np.asarray(Wedge6Element.integration_weights), determinants))

    @classmethod
    def validate_geometry(cls, coords: np.ndarray) -> None:
        """Reject geometry that fails the exact triangular-vertex certificate."""

        values = cls._validated_coords(coords)
        if np.unique(values, axis=0).shape[0] != cls.node_count:
            raise ValueError("WEDGE6_JACOBIAN_ORIENTATION_INVALID: coincident element nodes.")
        certificate = wedge6_jacobian_certificate(values)
        if not certificate["valid"]:
            raise ValueError(
                "WEDGE6_JACOBIAN_ORIENTATION_INVALID: certified minimum detJ "
                f"{certificate['minimum_detJ']:.6e} <= tolerance {certificate['geometry_tolerance']:.6e}."
            )
        volume = cls._signed_volume_validated(values)
        if not np.isfinite(volume) or volume <= 0.0:
            raise ValueError(f"WEDGE6 signed volume is not positive: {volume:.6e}.")

    @classmethod
    def b_matrix(cls, coords: np.ndarray, point: tuple[float, float, float] | np.ndarray) -> tuple[np.ndarray, float]:
        cls.validate_geometry(coords)
        jacobian = cls.jacobian(coords, point)
        determinant = float(np.linalg.det(jacobian))
        if determinant <= 0.0 or not np.isfinite(determinant):
            raise ValueError(f"WEDGE6_JACOBIAN_ORIENTATION_INVALID: detJ={determinant:.6e}.")
        gradients = cls.shape_derivatives_reference(point) @ np.linalg.inv(jacobian).T
        return strain_displacement_from_gradients(gradients), determinant

    @classmethod
    def strain_displacement_matrix(
        cls, coords: np.ndarray, point: tuple[float, float, float] | np.ndarray
    ) -> np.ndarray:
        return cls.b_matrix(coords, point)[0]

    @classmethod
    def integration_data(
        cls,
        coords: np.ndarray,
        quadrature: str = "production",
    ) -> tuple[tuple[tuple[float, float, float], float, np.ndarray, float], ...]:
        """Return point, rule weight, B matrix and detJ for a declared rule."""

        cls.validate_geometry(coords)
        name = str(quadrature).strip().upper()
        if name in {"PRODUCTION", "TRI3_X_GAUSS2"}:
            points = cls.integration_points
            weights = cls.integration_weights
        elif name in {"REFERENCE", "DUFFY_GAUSS5_X_GAUSS4"}:
            points = cls.reference_integration_points
            weights = cls.reference_integration_weights
        else:
            raise ValueError(f"Unsupported WEDGE6 quadrature {quadrature!r}.")
        return tuple(
            (point, float(weight), *cls.b_matrix(coords, point))
            for point, weight in zip(points, weights, strict=True)
        )

    @classmethod
    def signed_volume(cls, coords: np.ndarray, quadrature: str = "production") -> float:
        values = cls._validated_coords(coords)
        cls.validate_geometry(values)
        data = cls.integration_data(values, quadrature)
        return float(sum(weight * determinant for _, weight, _, determinant in data))

    @classmethod
    def volume(cls, coords: np.ndarray, quadrature: str = "production") -> float:
        return abs(cls.signed_volume(coords, quadrature))

    def stiffness(self, coords: np.ndarray, quadrature: str = "production") -> np.ndarray:
        stiffness = np.zeros((self.dof_count, self.dof_count), dtype=float)
        for _, weight, b_matrix, determinant in self.integration_data(coords, quadrature):
            stiffness += weight * determinant * (b_matrix.T @ self.material.elasticity_matrix @ b_matrix)
        return symmetrize(stiffness)

    def reference_stiffness(self, coords: np.ndarray) -> np.ndarray:
        return self.stiffness(coords, "reference")

    def internal_force_tangent_state(
        self,
        coords: np.ndarray,
        local_displacement: np.ndarray,
        states: list[dict[str, object]] | None = None,
    ) -> tuple[np.ndarray, np.ndarray, list[dict[str, object]]]:
        displacement = np.asarray(local_displacement, dtype=float)
        if displacement.shape != (self.dof_count,):
            raise ValueError("WEDGE6 local displacement must have shape (18,).")
        internal = np.zeros(self.dof_count, dtype=float)
        tangent = np.zeros((self.dof_count, self.dof_count), dtype=float)
        updated_states: list[dict[str, object]] = []
        for point_index, (_, weight, b_matrix, determinant) in enumerate(self.integration_data(coords)):
            strain = b_matrix @ displacement
            previous = states[point_index] if states and point_index < len(states) else None
            response = evaluate_constitutive(self.material, strain, previous)
            internal += weight * determinant * (b_matrix.T @ response.stress)
            tangent += weight * determinant * (b_matrix.T @ response.tangent @ b_matrix)
            if response.diagnostics.get("stateful", False):
                updated_states.append(response.trial_state)
        return internal, symmetrize(tangent), updated_states

    def internal_force_and_tangent(
        self,
        coords: np.ndarray,
        local_displacement: np.ndarray,
        states: list[dict[str, object]] | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        internal, tangent, _ = self.internal_force_tangent_state(coords, local_displacement, states)
        return internal, tangent

    def strain_at(self, coords: np.ndarray, local_displacement: np.ndarray, point) -> np.ndarray:
        b_matrix, _ = self.b_matrix(coords, point)
        displacement = np.asarray(local_displacement, dtype=float)
        if displacement.shape != (self.dof_count,):
            raise ValueError("WEDGE6 local displacement must have shape (18,).")
        return b_matrix @ displacement

    def stress_at(self, coords: np.ndarray, local_displacement: np.ndarray, point) -> np.ndarray:
        strain = self.strain_at(coords, local_displacement, point)
        return self.material.stress_tangent(strain)[0]

    def strain(self, coords: np.ndarray, local_displacement: np.ndarray) -> np.ndarray:
        return self.strain_at(coords, local_displacement, (1.0 / 3.0, 1.0 / 3.0, 0.0))

    def stress(self, coords: np.ndarray, local_displacement: np.ndarray) -> np.ndarray:
        return self.material.stress_tangent(self.strain(coords, local_displacement))[0]

    @classmethod
    def integration_point_results(
        cls,
        coords: np.ndarray,
        local_displacement: np.ndarray,
        material: SolidConstitutiveMaterial,
        quadrature: str = "production",
    ) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for index, (point, weight, b_matrix, determinant) in enumerate(cls.integration_data(coords, quadrature)):
            shape = cls.shape_functions(point)
            strain = b_matrix @ np.asarray(local_displacement, dtype=float)
            stress = material.stress_tangent(strain)[0]
            rows.append(
                {
                    "index": index,
                    "location": "gauss",
                    "natural_coordinates": list(point),
                    "coordinates": (shape @ np.asarray(coords, dtype=float)).tolist(),
                    "weight": float(weight * determinant),
                    "strain": strain.tolist(),
                    "stress": stress.tolist(),
                    "von_mises": von_mises_3d(stress),
                }
            )
        return rows

    @classmethod
    def integration_points_results(
        cls,
        coords: np.ndarray,
        local_displacement: np.ndarray,
        material: SolidConstitutiveMaterial,
        quadrature: str = "production",
    ) -> list[dict[str, object]]:
        return cls.integration_point_results(coords, local_displacement, material, quadrature)

    @staticmethod
    def von_mises(stress: np.ndarray) -> float:
        return von_mises_3d(stress)


__all__ = ["Wedge6Element"]
