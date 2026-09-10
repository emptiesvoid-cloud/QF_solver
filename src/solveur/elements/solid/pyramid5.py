"""Five-node collapsed-coordinate pyramid for the bounded WP09 feasibility route."""

from __future__ import annotations

import numpy as np

from solveur.elements.solid.common import (
    strain_displacement_from_gradients,
    symmetrize,
    validate_coords_shape,
    von_mises_3d,
)
from solveur.materials.solid import SolidConstitutiveMaterial


def _collapsed_rule(base_order: int, height_order: int) -> tuple[tuple[tuple[float, float, float], float], ...]:
    """Return a Gauss rule on the collapsed `(r, s, t)` coordinate domain.

    The physical collapsed-map determinant remains in the element Jacobian;
    the `t` weights are therefore ordinary Gauss--Legendre weights mapped to
    `[0, 1]`, not an independently weighted apex rule.
    """

    base_points, base_weights = np.polynomial.legendre.leggauss(base_order)
    raw_height_points, raw_height_weights = np.polynomial.legendre.leggauss(height_order)
    height_points = 0.5 * (raw_height_points + 1.0)
    height_weights = 0.5 * raw_height_weights
    return tuple(
        ((float(r), float(s), float(t)), float(weight_r * weight_s * weight_t))
        for r, weight_r in zip(base_points, base_weights, strict=True)
        for s, weight_s in zip(base_points, base_weights, strict=True)
        for t, weight_t in zip(height_points, height_weights, strict=True)
    )


_PRODUCTION_RULE = _collapsed_rule(3, 4)
_REFERENCE_RULE = _collapsed_rule(5, 6)


class Pyramid5Element:
    """Linear five-node pyramid with full collapsed-coordinate integration.

    This is intentionally restricted to small-strain isotropic linear
    elasticity. The collapsed map is singular at its apex, so the apex is a
    nodal interpolation point only: derivatives and quadrature are never
    evaluated there. WP09 treats this as a bounded feasibility kernel, not a
    general pyramid formulation or a modal/dynamic capability.
    """

    node_count = 5
    dof_count = 15
    integration_point_count = len(_PRODUCTION_RULE)
    reference_integration_point_count = len(_REFERENCE_RULE)
    reference_nodes = np.asarray(
        (
            (-1.0, -1.0, 0.0),
            (1.0, -1.0, 0.0),
            (1.0, 1.0, 0.0),
            (-1.0, 1.0, 0.0),
            (0.0, 0.0, 1.0),
        ),
        dtype=float,
    )
    integration_points = tuple(point for point, _ in _PRODUCTION_RULE)
    integration_weights = tuple(weight for _, weight in _PRODUCTION_RULE)
    reference_integration_points = tuple(point for point, _ in _REFERENCE_RULE)
    reference_integration_weights = tuple(weight for _, weight in _REFERENCE_RULE)

    def __init__(self, material: SolidConstitutiveMaterial):
        self.material = material

    @staticmethod
    def _reference_point(point: tuple[float, float, float] | np.ndarray) -> tuple[float, float, float]:
        r, s, t = (float(value) for value in np.asarray(point, dtype=float))
        if not np.isfinite((r, s, t)).all() or abs(r) > 1.0 + 1.0e-12 or abs(s) > 1.0 + 1.0e-12 or not -1.0e-12 <= t <= 1.0 + 1.0e-12:
            raise ValueError("PYRAMID5 collapsed reference coordinates are outside [-1,1]x[-1,1]x[0,1].")
        return r, s, t

    @classmethod
    def shape_functions(cls, point: tuple[float, float, float] | np.ndarray) -> np.ndarray:
        """Return nodal values in collapsed coordinates; apex values are well-defined."""

        r, s, t = cls._reference_point(point)
        return np.asarray(
            (
                0.25 * (1.0 - t) * (1.0 - r) * (1.0 - s),
                0.25 * (1.0 - t) * (1.0 + r) * (1.0 - s),
                0.25 * (1.0 - t) * (1.0 + r) * (1.0 + s),
                0.25 * (1.0 - t) * (1.0 - r) * (1.0 + s),
                t,
            ),
            dtype=float,
        )

    @classmethod
    def shape_derivatives_reference(cls, point: tuple[float, float, float] | np.ndarray) -> np.ndarray:
        """Return collapsed-coordinate derivatives away from the singular apex."""

        r, s, t = cls._reference_point(point)
        if t >= 1.0 - 1.0e-12:
            raise ValueError("PYRAMID5 derivatives are undefined at the collapsed apex.")
        return np.asarray(
            (
                (-0.25 * (1.0 - t) * (1.0 - s), -0.25 * (1.0 - t) * (1.0 - r), -0.25 * (1.0 - r) * (1.0 - s)),
                (0.25 * (1.0 - t) * (1.0 - s), -0.25 * (1.0 - t) * (1.0 + r), -0.25 * (1.0 + r) * (1.0 - s)),
                (0.25 * (1.0 - t) * (1.0 + s), 0.25 * (1.0 - t) * (1.0 + r), -0.25 * (1.0 + r) * (1.0 + s)),
                (-0.25 * (1.0 - t) * (1.0 + s), 0.25 * (1.0 - t) * (1.0 - r), -0.25 * (1.0 - r) * (1.0 + s)),
                (0.0, 0.0, 1.0),
            ),
            dtype=float,
        )

    @staticmethod
    def _validated_coords(coords: np.ndarray) -> np.ndarray:
        values = validate_coords_shape(coords, (5, 3), "PYRAMID5")
        if not np.isfinite(values).all():
            raise ValueError("PYRAMID5 coordinates must be finite.")
        if np.unique(values, axis=0).shape[0] != 5:
            raise ValueError("PYRAMID5_JACOBIAN_INVALID: coincident element nodes.")
        return values

    @classmethod
    def jacobian(cls, coords: np.ndarray, point: tuple[float, float, float] | np.ndarray) -> np.ndarray:
        values = cls._validated_coords(coords)
        return cls.shape_derivatives_reference(point).T @ values

    @classmethod
    def jacobian_determinant(cls, coords: np.ndarray, point: tuple[float, float, float] | np.ndarray) -> float:
        return float(np.linalg.det(cls.jacobian(coords, point)))

    @classmethod
    def validate_geometry(cls, coords: np.ndarray) -> None:
        """Reject non-positive sampled Jacobians in the declared bounded domain."""

        values = cls._validated_coords(coords)
        span = max(float(np.max(np.ptp(values, axis=0))), 1.0)
        tolerance = 1.0e-12 * span**3
        determinants = np.asarray(
            [cls.jacobian_determinant(values, point) for point in cls.reference_integration_points], dtype=float
        )
        minimum = float(np.min(determinants, initial=float("inf")))
        if not np.all(np.isfinite(determinants)) or minimum <= tolerance:
            raise ValueError(
                "PYRAMID5_JACOBIAN_INVALID: sampled minimum detJ "
                f"{minimum:.6e} <= tolerance {tolerance:.6e}."
            )

    @classmethod
    def _b_matrix_unchecked(
        cls, coords: np.ndarray, point: tuple[float, float, float] | np.ndarray
    ) -> tuple[np.ndarray, float]:
        jacobian = cls.shape_derivatives_reference(point).T @ coords
        determinant = float(np.linalg.det(jacobian))
        gradients = cls.shape_derivatives_reference(point) @ np.linalg.inv(jacobian).T
        return strain_displacement_from_gradients(gradients), determinant

    @classmethod
    def b_matrix(cls, coords: np.ndarray, point: tuple[float, float, float] | np.ndarray) -> tuple[np.ndarray, float]:
        values = cls._validated_coords(coords)
        cls.validate_geometry(values)
        b_matrix, determinant = cls._b_matrix_unchecked(values, point)
        if not np.isfinite(determinant) or determinant <= 0.0:
            raise ValueError(f"PYRAMID5_JACOBIAN_INVALID: detJ={determinant:.6e}.")
        return b_matrix, determinant

    @classmethod
    def strain_displacement_matrix(
        cls, coords: np.ndarray, point: tuple[float, float, float] | np.ndarray
    ) -> np.ndarray:
        return cls.b_matrix(coords, point)[0]

    @classmethod
    def integration_data(
        cls, coords: np.ndarray, quadrature: str = "production"
    ) -> tuple[tuple[tuple[float, float, float], float, np.ndarray, float], ...]:
        """Return point, rule weight, `B` and determinant for a named frozen rule."""

        values = cls._validated_coords(coords)
        cls.validate_geometry(values)
        name = str(quadrature).strip().upper()
        if name in {"PRODUCTION", "GAUSS3_X_GAUSS3_X_GAUSS4"}:
            rule = _PRODUCTION_RULE
        elif name in {"REFERENCE", "GAUSS5_X_GAUSS5_X_GAUSS6"}:
            rule = _REFERENCE_RULE
        else:
            raise ValueError(f"Unsupported PYRAMID5 quadrature {quadrature!r}.")
        rows = []
        for point, weight in rule:
            b_matrix, determinant = cls._b_matrix_unchecked(values, point)
            if not np.isfinite(determinant) or determinant <= 0.0:
                raise ValueError(f"PYRAMID5_JACOBIAN_INVALID: detJ={determinant:.6e}.")
            rows.append((point, weight, b_matrix, determinant))
        return tuple(rows)

    @classmethod
    def signed_volume(cls, coords: np.ndarray, quadrature: str = "production") -> float:
        return float(sum(weight * determinant for _, weight, _, determinant in cls.integration_data(coords, quadrature)))

    @classmethod
    def volume(cls, coords: np.ndarray, quadrature: str = "production") -> float:
        return abs(cls.signed_volume(coords, quadrature))

    def stiffness(self, coords: np.ndarray, quadrature: str = "production") -> np.ndarray:
        stiffness = np.zeros((self.dof_count, self.dof_count), dtype=float)
        for _, weight, b_matrix, determinant in self.integration_data(coords, quadrature):
            stiffness += weight * determinant * (b_matrix.T @ self.material.elasticity_matrix @ b_matrix)
        return symmetrize(stiffness)

    def _mass_with_quadrature(self, coords: np.ndarray, quadrature: str) -> np.ndarray:
        if self.material.density <= 0.0:
            raise ValueError("PYRAMID5 consistent mass requires a positive material density.")
        mass = np.zeros((self.dof_count, self.dof_count), dtype=float)
        for point, weight, _, determinant in self.integration_data(coords, quadrature):
            shape = self.shape_functions(point)
            mass += self.material.density * weight * determinant * np.kron(np.outer(shape, shape), np.eye(3))
        return symmetrize(mass)

    def mass(self, coords: np.ndarray) -> np.ndarray:
        """Return the consistent translational mass retained for elemental checks only."""

        return self._mass_with_quadrature(coords, "production")

    def reference_mass(self, coords: np.ndarray) -> np.ndarray:
        return self._mass_with_quadrature(coords, "reference")

    def reference_stiffness(self, coords: np.ndarray) -> np.ndarray:
        return self.stiffness(coords, "reference")

    def strain_at(self, coords: np.ndarray, local_displacement: np.ndarray, point: tuple[float, float, float]) -> np.ndarray:
        displacement = np.asarray(local_displacement, dtype=float)
        if displacement.shape != (self.dof_count,):
            raise ValueError("PYRAMID5 local displacement must have shape (15,).")
        return self.b_matrix(coords, point)[0] @ displacement

    def stress_at(self, coords: np.ndarray, local_displacement: np.ndarray, point: tuple[float, float, float]) -> np.ndarray:
        return self.material.stress_tangent(self.strain_at(coords, local_displacement, point))[0]

    @classmethod
    def integration_point_results(
        cls,
        coords: np.ndarray,
        local_displacement: np.ndarray,
        material: SolidConstitutiveMaterial,
        quadrature: str = "production",
    ) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        displacement = np.asarray(local_displacement, dtype=float)
        for index, (point, weight, b_matrix, determinant) in enumerate(cls.integration_data(coords, quadrature)):
            shape = cls.shape_functions(point)
            strain = b_matrix @ displacement
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

    integration_points_results = integration_point_results

    @staticmethod
    def von_mises(stress: np.ndarray) -> float:
        return von_mises_3d(stress)


__all__ = ["Pyramid5Element"]
