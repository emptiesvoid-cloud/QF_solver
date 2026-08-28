"""Bounded Total-Lagrangian J2 elements for the 0.2.5 research path.

The constitutive model is evaluated on the objective Green-Lagrange strain and
returns a second-Piola stress. This is an explicit, documented finite-kinematic
model; it is not a claim of general finite-strain plasticity.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from solveur.core.nonlinear_contracts import evaluate_constitutive
from solveur.elements.solid.hex8 import Hex8Element
from solveur.elements.solid.hex20 import Hex20Element
from solveur.elements.solid.tet4 import Tet4Element
from solveur.elements.solid.tet10 import Tet10Element
from solveur.elements.solid.common import symmetrize, validate_coords_shape


def _strain_voigt(tensor: np.ndarray) -> np.ndarray:
    """Convert a symmetric strain tensor to engineering Voigt order."""
    return np.asarray(
        [tensor[0, 0], tensor[1, 1], tensor[2, 2], 2.0 * tensor[0, 1], 2.0 * tensor[1, 2], 2.0 * tensor[0, 2]],
        dtype=float,
    )


def _stress_tensor(values: np.ndarray) -> np.ndarray:
    """Convert stress Voigt order ``XX,YY,ZZ,XY,YZ,XZ`` to a tensor."""
    sx, sy, sz, txy, tyz, txz = np.asarray(values, dtype=float)
    return np.array([[sx, txy, txz], [txy, sy, tyz], [txz, tyz, sz]], dtype=float)


def _constitutive_tensor(tangent: np.ndarray) -> np.ndarray:
    """Expand an engineering-Voigt tangent into a symmetric fourth-order tensor."""
    tangent = np.asarray(tangent, dtype=float)
    if tangent.shape != (6, 6):
        raise ValueError("Total-Lagrangian J2 tangent must have shape (6, 6).")
    output_basis = np.zeros((6, 3, 3), dtype=float)
    input_basis = np.zeros((6, 3, 3), dtype=float)
    for index in range(3):
        output_basis[index, index, index] = 1.0
        input_basis[index, index, index] = 1.0
    for index, (first, second) in enumerate(((0, 1), (1, 2), (0, 2)), start=3):
        output_basis[index, first, second] = 1.0
        output_basis[index, second, first] = 1.0
        input_basis[index, first, second] = 1.0
        input_basis[index, second, first] = 1.0
    return np.einsum("aij,ab,bkl->ijkl", output_basis, tangent, input_basis, optimize=True)


class TotalLagrangianJ2Element:
    """Common finite-kinematic J2 element kernel for the supported solids."""

    node_count: int
    integration_point_count: int

    def __init__(self, material: object):
        self.material = material
        self._reference_cache_key: tuple[tuple[int, ...], str, bytes] | None = None
        self._reference_cache: tuple[tuple[float, np.ndarray], ...] | None = None
        self._reference_cache_hits = 0
        self._reference_cache_misses = 0

    def reference_geometry_cache_info(self) -> dict[str, int]:
        """Return reference-geometry cache counters for profiling evidence."""
        return {
            "hits": self._reference_cache_hits,
            "misses": self._reference_cache_misses,
        }

    def _cached_reference_data(
        self, coords: np.ndarray
    ) -> tuple[tuple[float, np.ndarray], ...]:
        """Reuse reference quadrature data while the reference mesh is unchanged.

        Total-Lagrangian kernels use immutable reference coordinates throughout a
        solve.  The key includes shape, dtype and bytes so a reused element cannot
        silently retain geometry from a different model or a mutated array.
        """
        contiguous = np.ascontiguousarray(coords, dtype=float)
        key = (tuple(contiguous.shape), contiguous.dtype.str, contiguous.tobytes())
        if self._reference_cache_key == key and self._reference_cache is not None:
            self._reference_cache_hits += 1
            return self._reference_cache
        reference_data = self._reference_data(contiguous)
        self._reference_cache_key = key
        self._reference_cache = reference_data
        self._reference_cache_misses += 1
        return reference_data

    def _reference_data(
        self, coords: np.ndarray
    ) -> tuple[tuple[float, np.ndarray], ...]:
        raise NotImplementedError

    def internal_force_tangent_state(
        self,
        coords: np.ndarray,
        local_displacement: np.ndarray,
        states: list[dict[str, Any]] | None = None,
    ) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]]]:
        coords = validate_coords_shape(coords, (self.node_count, 3), self.__class__.__name__)
        local_displacement = np.asarray(local_displacement, dtype=float)
        expected = 3 * self.node_count
        if local_displacement.shape != (expected,) or not np.all(np.isfinite(local_displacement)):
            raise ValueError(f"{self.__class__.__name__} displacement must have shape ({expected},).")
        internal = np.zeros(expected, dtype=float)
        tangent = np.zeros((expected, expected), dtype=float)
        updated_states: list[dict[str, Any]] = []
        local = local_displacement.reshape(self.node_count, 3)
        for point_index, (measure, gradients) in enumerate(self._cached_reference_data(coords)):
            deformation = np.eye(3) + local.T @ gradients
            determinant = float(np.linalg.det(deformation))
            if determinant <= 1.0e-10 or not np.all(np.isfinite(deformation)):
                raise ValueError(f"Invalid finite deformation gradient determinant {determinant:.6e}.")
            green = 0.5 * (deformation.T @ deformation - np.eye(3))
            response = evaluate_constitutive(
                self.material,
                _strain_voigt(green),
                states[point_index] if states and point_index < len(states) else None,
            )
            second = _stress_tensor(response.stress)
            first = deformation @ second
            internal += measure * np.einsum("iJ,aJ->ai", first, gradients).reshape(expected)
            if response.diagnostics.get("stateful", False):
                updated_states.append(response.trial_state)
            tangent += measure * self._tangent(deformation, second, response.tangent, gradients)
        return internal, symmetrize(tangent), updated_states

    def internal_force_and_tangent(
        self,
        coords: np.ndarray,
        local_displacement: np.ndarray,
        states: list[dict[str, Any]] | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return the state-aware kernel without exposing trial states."""
        internal, tangent, _ = self.internal_force_tangent_state(coords, local_displacement, states)
        return internal, tangent

    def integration_point_results(
        self,
        coords: np.ndarray,
        local_displacement: np.ndarray,
        states: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Return objective finite-kinematic fields for evidence/post-processing."""
        coords = validate_coords_shape(coords, (self.node_count, 3), self.__class__.__name__)
        local = np.asarray(local_displacement, dtype=float).reshape(self.node_count, 3)
        rows: list[dict[str, Any]] = []
        for point_index, (measure, gradients) in enumerate(self._cached_reference_data(coords)):
            deformation = np.eye(3) + local.T @ gradients
            determinant = float(np.linalg.det(deformation))
            if determinant <= 1.0e-10:
                raise ValueError(f"Invalid finite deformation gradient determinant {determinant:.6e}.")
            green = 0.5 * (deformation.T @ deformation - np.eye(3))
            response = evaluate_constitutive(
                self.material,
                _strain_voigt(green),
                states[point_index] if states and point_index < len(states) else None,
            )
            second = _stress_tensor(response.stress)
            cauchy = deformation @ second @ deformation.T / determinant
            rows.append(
                {
                    "index": point_index,
                    "location": "gauss",
                    "weight": float(measure),
                    "deformation_gradient": deformation.tolist(),
                    "green_lagrange_strain": green.tolist(),
                    "second_piola_stress": second.tolist(),
                    "cauchy_stress": (0.5 * (cauchy + cauchy.T)).tolist(),
                    "det_f": determinant,
                    "stress": response.stress.tolist(),
                    "strain": _strain_voigt(green).tolist(),
                    "equivalent_plastic_strain": float(
                        response.trial_state.get("equivalent_plastic_strain", 0.0)
                    ),
                    "material_state": response.trial_state,
                }
            )
        return rows

    @staticmethod
    def _tangent(
        deformation: np.ndarray,
        second: np.ndarray,
        material_tangent: np.ndarray,
        gradients: np.ndarray,
    ) -> np.ndarray:
        """Assemble material and geometric tangent in reference coordinates."""
        constitutive = _constitutive_tensor(material_tangent)
        local_nodes = gradients.shape[0]
        green_derivatives = 0.5 * (
            np.einsum("bm,qn->bqmn", gradients, deformation, optimize=True)
            + np.einsum("qm,bn->bqmn", deformation, gradients, optimize=True)
        )
        material_blocks = np.einsum(
            "aj,ik,kjmn,bqmn->abiq",
            gradients,
            deformation,
            constitutive,
            green_derivatives,
            optimize=True,
        )
        geometric_scalars = np.einsum("aj,jk,bk->ab", gradients, second, gradients, optimize=True)
        blocks = material_blocks + geometric_scalars[:, :, None, None] * np.eye(3)
        return blocks.transpose(0, 2, 1, 3).reshape(3 * local_nodes, 3 * local_nodes)


class TotalLagrangianJ2Tet4Element(TotalLagrangianJ2Element):
    """Green-Lagrange/J2 TET4 research element."""

    node_count = 4
    integration_point_count = 1

    def _reference_data(self, coords: np.ndarray) -> tuple[tuple[float, np.ndarray], ...]:
        volume = Tet4Element.signed_volume(coords)
        if volume <= 1.0e-14:
            raise ValueError(f"Invalid TET4 reference volume {volume:.6e}.")
        return ((volume, Tet4Element.shape_gradients(coords)),)


class TotalLagrangianJ2Hex8Element(TotalLagrangianJ2Element):
    """Green-Lagrange/J2 HEX8 research element."""

    node_count = 8
    integration_point_count = 8

    def _reference_data(self, coords: np.ndarray) -> tuple[tuple[float, np.ndarray], ...]:
        Hex8Element.validate_geometry(coords)
        data: list[tuple[float, np.ndarray]] = []
        for point in Hex8Element.integration_points:
            jacobian = Hex8Element.jacobian(coords, point)
            determinant = float(np.linalg.det(jacobian))
            gradients = Hex8Element.shape_derivatives_reference(point) @ np.linalg.inv(jacobian).T
            data.append((determinant, gradients))
        return tuple(data)


class TotalLagrangianJ2Tet10Element(TotalLagrangianJ2Element):
    """Green-Lagrange/J2 TET10 element using the stateful TET10 rule."""

    node_count = 10
    integration_point_count = 4

    def __init__(self, material: object, nonlinear_quadrature: str = "hammer4"):
        super().__init__(material)
        self.nonlinear_quadrature = Tet10Element.normalize_nonlinear_quadrature(nonlinear_quadrature)
        self.integration_point_count = len(self._rule())

    def _rule(self) -> tuple[tuple[tuple[float, float, float, float], float], ...]:
        if self.nonlinear_quadrature == "code_aster_5":
            return Tet10Element.code_aster_integration_rule()
        return Tet10Element.hammer_integration_rule()

    def _reference_data(self, coords: np.ndarray) -> tuple[tuple[float, np.ndarray], ...]:
        coords = validate_coords_shape(coords, (self.node_count, 3), self.__class__.__name__)
        if Tet10Element.corner_signed_volume(coords) <= 1.0e-14:
            raise ValueError("Invalid TET10 reference orientation or volume.")
        data: list[tuple[float, np.ndarray]] = []
        for point, weight in self._rule():
            derivatives = Tet10Element.shape_derivatives_reference(point)
            jacobian = derivatives.T @ coords
            determinant = float(np.linalg.det(jacobian))
            if not np.isfinite(determinant) or determinant <= 1.0e-14:
                raise ValueError(f"Invalid TET10 reference Jacobian determinant {determinant:.6e}.")
            gradients = derivatives @ np.linalg.inv(jacobian).T
            data.append((float(weight * determinant), gradients))
        return tuple(data)


class TotalLagrangianJ2Hex20Element(TotalLagrangianJ2Element):
    """Green-Lagrange/J2 HEX20 element with complete 3x3x3 integration."""

    node_count = 20
    integration_point_count = 27

    def _reference_data(self, coords: np.ndarray) -> tuple[tuple[float, np.ndarray], ...]:
        coords = validate_coords_shape(coords, (self.node_count, 3), self.__class__.__name__)
        Hex20Element.validate_geometry(coords)
        data: list[tuple[float, np.ndarray]] = []
        for point, weight in zip(Hex20Element.integration_points, Hex20Element.integration_weights, strict=True):
            jacobian = Hex20Element.jacobian(coords, point)
            determinant = float(np.linalg.det(jacobian))
            if not np.isfinite(determinant) or determinant <= 1.0e-14:
                raise ValueError(f"Invalid HEX20 reference Jacobian determinant {determinant:.6e}.")
            derivatives = Hex20Element.shape_derivatives_reference(point)
            gradients = derivatives @ np.linalg.inv(jacobian).T
            data.append((float(weight * determinant), gradients))
        return tuple(data)
