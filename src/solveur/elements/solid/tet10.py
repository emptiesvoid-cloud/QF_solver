"""Quadratic ten-node tetrahedral solid element."""

from __future__ import annotations

import numpy as np

from solveur.core.nonlinear.contracts import evaluate_constitutive

from solveur.elements.solid.common import (
    strain_displacement_from_gradients,
    symmetrize,
    validate_coords_shape,
    von_mises_3d,
)
from solveur.elements.solid.quadrature import tetra_duffy_rule, tetra_lattice_points
from solveur.materials.solid import SolidConstitutiveMaterial


class Tet10Element:
    """Isoparametric TET10 element for 3D linear elasticity."""

    # Hammer four-point tetra integration in barycentric coordinates.
    a = 0.5854101966249685
    b = 0.1381966011250105
    integration_points = (
        (a, b, b, b),
        (b, a, b, b),
        (b, b, a, b),
        (b, b, b, a),
    )
    integration_weight = 1.0 / 24.0
    integration_point_count = len(integration_points)
    # Symmetric five-point rule used by the opt-in Code_Aster comparison
    # configuration for stateful nonlinear TET10 calculations.  The negative
    # centroid weight is intentional and the rule integrates cubic fields.
    code_aster_integration_points = (
        (0.25, 0.25, 0.25, 0.25),
        (0.5, 1.0 / 6.0, 1.0 / 6.0, 1.0 / 6.0),
        (1.0 / 6.0, 0.5, 1.0 / 6.0, 1.0 / 6.0),
        (1.0 / 6.0, 1.0 / 6.0, 0.5, 1.0 / 6.0),
        (1.0 / 6.0, 1.0 / 6.0, 1.0 / 6.0, 0.5),
    )
    code_aster_integration_weights = (-2.0 / 15.0, 3.0 / 40.0, 3.0 / 40.0, 3.0 / 40.0, 3.0 / 40.0)
    nonlinear_quadrature_names = frozenset({"hammer4", "code_aster_5"})
    curved_quadrature_order = 4
    straight_sided_tolerance = 1.0e-12
    edge_nodes = ((0, 1, 4), (1, 2, 5), (2, 0, 6), (0, 3, 7), (1, 3, 8), (2, 3, 9))
    nodal_barycentric = np.array(
        [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
            [0.5, 0.5, 0.0, 0.0],
            [0.0, 0.5, 0.5, 0.0],
            [0.5, 0.0, 0.5, 0.0],
            [0.5, 0.0, 0.0, 0.5],
            [0.0, 0.5, 0.0, 0.5],
            [0.0, 0.0, 0.5, 0.5],
        ],
        dtype=float,
    )

    def __init__(self, material: SolidConstitutiveMaterial, nonlinear_quadrature: str = "hammer4"):
        self.material = material
        self.nonlinear_quadrature = self.normalize_nonlinear_quadrature(nonlinear_quadrature)
        self.nonlinear_integration_point_count = len(self.nonlinear_integration_rule())

    @classmethod
    def normalize_nonlinear_quadrature(cls, value: str | None) -> str:
        """Normalize the explicit stateful TET10 quadrature selection."""
        normalized = str(value or "hammer4").strip().lower()
        if normalized not in cls.nonlinear_quadrature_names:
            allowed = ", ".join(sorted(cls.nonlinear_quadrature_names))
            raise ValueError(f"Unsupported TET10 nonlinear quadrature {value!r}; allowed: {allowed}.")
        return normalized

    @staticmethod
    def corner_signed_volume(coords: np.ndarray) -> float:
        corners = np.asarray(coords, dtype=float)[:4]
        matrix = np.column_stack((corners[1] - corners[0], corners[2] - corners[0], corners[3] - corners[0]))
        return float(np.linalg.det(matrix) / 6.0)

    @staticmethod
    def shape_functions(barycentric: tuple[float, float, float, float]) -> np.ndarray:
        l1, l2, l3, l4 = barycentric
        return np.array(
            [
                l1 * (2.0 * l1 - 1.0),
                l2 * (2.0 * l2 - 1.0),
                l3 * (2.0 * l3 - 1.0),
                l4 * (2.0 * l4 - 1.0),
                4.0 * l1 * l2,
                4.0 * l2 * l3,
                4.0 * l3 * l1,
                4.0 * l1 * l4,
                4.0 * l2 * l4,
                4.0 * l3 * l4,
            ],
            dtype=float,
        )

    @staticmethod
    def shape_derivatives_reference(barycentric: tuple[float, float, float, float]) -> np.ndarray:
        l1, l2, l3, l4 = barycentric
        gradients_l = np.array(
            [
                [-1.0, -1.0, -1.0],
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ],
            dtype=float,
        )
        values = np.array(
            [
                (4.0 * l1 - 1.0) * gradients_l[0],
                (4.0 * l2 - 1.0) * gradients_l[1],
                (4.0 * l3 - 1.0) * gradients_l[2],
                (4.0 * l4 - 1.0) * gradients_l[3],
                4.0 * (l1 * gradients_l[1] + l2 * gradients_l[0]),
                4.0 * (l2 * gradients_l[2] + l3 * gradients_l[1]),
                4.0 * (l3 * gradients_l[0] + l1 * gradients_l[2]),
                4.0 * (l1 * gradients_l[3] + l4 * gradients_l[0]),
                4.0 * (l2 * gradients_l[3] + l4 * gradients_l[1]),
                4.0 * (l3 * gradients_l[3] + l4 * gradients_l[2]),
            ],
            dtype=float,
        )
        return values

    @classmethod
    def b_matrix(cls, coords: np.ndarray, barycentric: tuple[float, float, float, float]) -> tuple[np.ndarray, float]:
        coords = validate_coords_shape(coords, (10, 3), "TET10")
        dnr = cls.shape_derivatives_reference(barycentric)
        jacobian = dnr.T @ coords
        det_j = float(np.linalg.det(jacobian))
        if det_j <= 1.0e-14:
            raise ValueError(f"Invalid TET10 jacobian {det_j:.6e}.")
        gradients = dnr @ np.linalg.inv(jacobian).T
        return strain_displacement_from_gradients(gradients), det_j

    @classmethod
    def jacobian_determinants(
        cls,
        coords: np.ndarray,
        points: tuple[tuple[float, float, float, float], ...] | None = None,
    ) -> np.ndarray:
        """Evaluate the geometric Jacobian on a deterministic closed lattice."""
        coords = validate_coords_shape(coords, (10, 3), "TET10")
        samples = points or tetra_lattice_points(4)
        values = []
        for point in samples:
            derivatives = cls.shape_derivatives_reference(point)
            values.append(float(np.linalg.det(derivatives.T @ coords)))
        return np.asarray(values, dtype=float)

    @classmethod
    def geometry_diagnostics(cls, coords: np.ndarray) -> dict[str, float]:
        """Return curvature and sampled-Jacobian indicators used by integration."""
        points = validate_coords_shape(coords, (10, 3), "TET10")
        deviations = []
        relative_deviations = []
        for first, second, middle in cls.edge_nodes:
            edge_length = float(np.linalg.norm(points[second] - points[first]))
            midpoint = 0.5 * (points[first] + points[second])
            deviation = float(np.linalg.norm(points[middle] - midpoint))
            deviations.append(deviation)
            relative_deviations.append(deviation / edge_length if edge_length > 0.0 else np.inf)
        determinants = cls.jacobian_determinants(points)
        minimum = float(np.min(determinants))
        maximum = float(np.max(determinants))
        return {
            "mid_edge_deviation_max": float(max(deviations)),
            "mid_edge_deviation_mean": float(np.mean(deviations)),
            "mid_edge_deviation_ratio_max": float(max(relative_deviations)),
            "sampled_jacobian_min": minimum,
            "sampled_jacobian_max": maximum,
            "sampled_jacobian_ratio": minimum / maximum if maximum > 0.0 else float("-inf"),
            "sampled_jacobian_nonpositive_count": float(np.count_nonzero(determinants <= 0.0)),
            "sampled_jacobian_count": float(determinants.size),
        }

    @classmethod
    def stiffness_integration_rule(
        cls,
        coords: np.ndarray,
        quadrature_order: int | None = None,
    ) -> tuple[tuple[tuple[float, float, float, float], float], ...]:
        """Select exact straight-sided or enriched curved-geometry quadrature."""
        diagnostics = cls.geometry_diagnostics(coords)
        if diagnostics["sampled_jacobian_min"] <= 1.0e-14:
            raise ValueError(
                f"Invalid TET10 sampled jacobian {diagnostics['sampled_jacobian_min']:.6e}."
            )
        if quadrature_order is None and (
            diagnostics["mid_edge_deviation_ratio_max"] <= cls.straight_sided_tolerance
        ):
            return cls.hammer_integration_rule()
        return tetra_duffy_rule(quadrature_order or cls.curved_quadrature_order)

    @classmethod
    def hammer_integration_rule(
        cls,
    ) -> tuple[tuple[tuple[float, float, float, float], float], ...]:
        """Return the four-point degree-two rule retained for straight TET10."""
        return tuple((point, cls.integration_weight) for point in cls.integration_points)

    @classmethod
    def code_aster_integration_rule(
        cls,
    ) -> tuple[tuple[tuple[float, float, float, float], float], ...]:
        """Return the symmetric five-point tetrahedral rule used for correlation."""
        return tuple(zip(cls.code_aster_integration_points, cls.code_aster_integration_weights, strict=True))

    def nonlinear_integration_rule(
        self,
    ) -> tuple[tuple[tuple[float, float, float, float], float], ...]:
        """Return the selected rule for stateful constitutive integration."""
        if self.nonlinear_quadrature == "code_aster_5":
            return self.code_aster_integration_rule()
        return self.hammer_integration_rule()

    @classmethod
    def extrapolate_integration_values(
        cls,
        values: np.ndarray,
        points: np.ndarray | None = None,
    ) -> np.ndarray:
        """Fit a linear barycentric field and extrapolate it to ten nodes."""
        point_values = np.asarray(values, dtype=float)
        interpolation = np.asarray(cls.integration_points if points is None else points, dtype=float)
        if interpolation.ndim != 2 or interpolation.shape[1] != 4:
            raise ValueError("TET10 extrapolation points must have four barycentric coordinates.")
        if point_values.shape[0] != interpolation.shape[0] or interpolation.shape[0] < 4:
            raise ValueError("TET10 extrapolation expects at least four values matching the points.")
        coefficients, _, rank, _ = np.linalg.lstsq(interpolation, point_values, rcond=None)
        if rank < 4:
            raise ValueError("TET10 extrapolation points do not span a linear barycentric field.")
        return cls.nodal_barycentric @ coefficients

    def stiffness(self, coords: np.ndarray, quadrature_order: int | None = None) -> np.ndarray:
        if self.corner_signed_volume(coords) <= 1.0e-14:
            raise ValueError("Invalid TET10 corner orientation or volume.")
        stiffness = np.zeros((30, 30), dtype=float)
        for point, weight in self.stiffness_integration_rule(coords, quadrature_order):
            b, det_j = self.b_matrix(coords, point)
            stiffness += weight * det_j * (b.T @ self.material.elasticity_matrix @ b)
        return symmetrize(stiffness)

    def internal_force_and_tangent(
        self,
        coords: np.ndarray,
        local_displacement: np.ndarray,
        states: list[dict[str, object]] | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        internal, tangent, _ = self.internal_force_tangent_state(coords, local_displacement, states)
        return internal, tangent

    def internal_force_tangent_state(
        self,
        coords: np.ndarray,
        local_displacement: np.ndarray,
        states: list[dict[str, object]] | None = None,
    ) -> tuple[np.ndarray, np.ndarray, list[dict[str, object]]]:
        if self.corner_signed_volume(coords) <= 1.0e-14:
            raise ValueError("Invalid TET10 corner orientation or volume.")
        local_displacement = np.asarray(local_displacement, dtype=float)
        internal = np.zeros(30, dtype=float)
        tangent = np.zeros((30, 30), dtype=float)
        updated_states: list[dict[str, object]] = []
        if hasattr(self.material, "stress_tangent_state"):
            rule = self.nonlinear_integration_rule()
        else:
            rule = self.stiffness_integration_rule(coords)
        for point_index, (point, weight) in enumerate(rule):
            b, det_j = self.b_matrix(coords, point)
            strain = b @ local_displacement
            previous = states[point_index] if states and point_index < len(states) else None
            response = evaluate_constitutive(self.material, strain, previous)
            stress, material_tangent = response.stress, response.tangent
            if response.diagnostics.get("stateful", False):
                updated_states.append(response.trial_state)
            internal += weight * det_j * (b.T @ stress)
            tangent += weight * det_j * (b.T @ material_tangent @ b)
        return internal, symmetrize(tangent), updated_states

    def mass(self, coords: np.ndarray) -> np.ndarray:
        if self.material.density <= 0.0:
            raise ValueError("TET10 modal analysis requires a positive material density.")
        if self.corner_signed_volume(coords) <= 1.0e-14:
            raise ValueError("Invalid TET10 corner orientation or volume.")
        mass = np.zeros((30, 30), dtype=float)
        identity = np.eye(3)
        for point, weight in tetra_duffy_rule(5):
            shape = self.shape_functions(point)
            derivatives = self.shape_derivatives_reference(point)
            det_j = float(np.linalg.det(derivatives.T @ coords))
            if det_j <= 1.0e-14:
                raise ValueError(f"Invalid TET10 jacobian {det_j:.6e} during mass integration.")
            mass += self.material.density * weight * det_j * np.kron(np.outer(shape, shape), identity)
        return symmetrize(mass)

    def strain(self, coords: np.ndarray, local_displacement: np.ndarray) -> np.ndarray:
        b, _ = self.b_matrix(coords, (0.25, 0.25, 0.25, 0.25))
        return b @ np.asarray(local_displacement, dtype=float)

    def stress(self, coords: np.ndarray, local_displacement: np.ndarray) -> np.ndarray:
        stress, _ = self.material.stress_tangent(self.strain(coords, local_displacement))
        return stress

    @staticmethod
    def von_mises(stress: np.ndarray) -> float:
        return von_mises_3d(stress)
