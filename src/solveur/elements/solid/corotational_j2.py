"""Bounded corotational small-strain J2 solid elements.

This module deliberately lives beside, rather than inside, the existing
Green--Lagrange/second-Piola research path.  The formulation is intended for
large rigid rotations and small local strains.  It is not a finite-strain
plasticity implementation: the material state remains an additive small-
strain J2 state, transported between successive corotated frames.

The element force uses the polar decomposition ``F = R U``.  The constitutive
law is evaluated on the Biot-like corotated strain ``U - I`` and the local
stress is rotated back through ``P = R sigma_local``.  The element tangent is
formed by a central difference of this force at a fixed committed material
state.  This is intentionally conservative for the first bounded research
path: the numerical tangent exposes frame-transport and geometric terms to
Newton instead of silently reusing the Green--Lagrange tangent.
"""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any

import numpy as np

from solveur.core.nonlinear.contracts import evaluate_constitutive
from solveur.elements.solid.common import symmetrize, validate_coords_shape
from solveur.elements.solid.total_lagrangian_j2 import (
    TotalLagrangianJ2Hex8Element,
    TotalLagrangianJ2Hex20Element,
    TotalLagrangianJ2Tet4Element,
    TotalLagrangianJ2Tet10Element,
)


def _strain_voigt(tensor: np.ndarray) -> np.ndarray:
    """Convert a symmetric tensor to engineering-Voigt strain order."""

    return np.asarray(
        [
            tensor[0, 0],
            tensor[1, 1],
            tensor[2, 2],
            2.0 * tensor[0, 1],
            2.0 * tensor[1, 2],
            2.0 * tensor[0, 2],
        ],
        dtype=float,
    )


def _strain_tensor(values: np.ndarray) -> np.ndarray:
    """Convert engineering-Voigt strain values to a symmetric tensor."""

    ex, ey, ez, gxy, gyz, gxz = np.asarray(values, dtype=float)
    return np.array(
        [[ex, 0.5 * gxy, 0.5 * gxz], [0.5 * gxy, ey, 0.5 * gyz], [0.5 * gxz, 0.5 * gyz, ez]],
        dtype=float,
    )


def _stress_tensor(values: np.ndarray) -> np.ndarray:
    """Convert stress Voigt values to a symmetric tensor."""

    sx, sy, sz, txy, tyz, txz = np.asarray(values, dtype=float)
    return np.array([[sx, txy, txz], [txy, sy, tyz], [txz, tyz, sz]], dtype=float)


def _stress_voigt(tensor: np.ndarray) -> np.ndarray:
    """Convert a symmetric stress tensor to stress Voigt order."""

    return np.asarray(
        [tensor[0, 0], tensor[1, 1], tensor[2, 2], tensor[0, 1], tensor[1, 2], tensor[0, 2]],
        dtype=float,
    )


def _polar_decomposition(deformation: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """Return the proper rotation, right stretch and determinant of ``F``."""

    determinant = float(np.linalg.det(deformation))
    if not np.isfinite(determinant) or determinant <= 1.0e-10:
        raise ValueError(f"Invalid corotational deformation determinant {determinant:.6e}.")
    left, singular_values, right_transpose = np.linalg.svd(deformation)
    rotation = left @ right_transpose
    if not np.all(np.isfinite(rotation)) or float(np.linalg.det(rotation)) <= 0.0:
        raise ValueError("Corotational polar decomposition produced an invalid rotation.")
    stretch = right_transpose.T @ np.diag(singular_values) @ right_transpose
    return rotation, symmetrize(stretch), determinant


def _transport_state(state: dict[str, Any] | None, rotation: np.ndarray) -> dict[str, Any] | None:
    """Transport local tensor state from the committed frame to ``rotation``."""

    if state is None:
        return None
    transported = deepcopy(state)
    if "corotation" not in state:
        nonzero = max(
            [
                float(np.linalg.norm(np.asarray(state.get("plastic_strain", [0.0] * 6), dtype=float))),
                float(np.linalg.norm(np.asarray(state.get("stress", [0.0] * 6), dtype=float))),
                float(abs(float(state.get("equivalent_plastic_strain", 0.0)))),
            ]
        )
        if nonzero > 1.0e-14:
            raise ValueError("Corotational restart state is missing its committed frame metadata.")
        old_rotation = np.eye(3)
    else:
        old_rotation = np.asarray(state["corotation"], dtype=float)
        if old_rotation.shape != (3, 3) or not np.all(np.isfinite(old_rotation)):
            raise ValueError("Corotational restart state contains an invalid committed rotation.")
    relative_rotation = rotation.T @ old_rotation
    if not np.all(np.isfinite(relative_rotation)):
        raise ValueError("Corotational state transport produced non-finite rotation data.")

    if "plastic_strain" in state:
        plastic = relative_rotation @ _strain_tensor(np.asarray(state["plastic_strain"], dtype=float)) @ relative_rotation.T
        transported["plastic_strain"] = _strain_voigt(symmetrize(plastic)).tolist()
    if "stress" in state:
        stress = relative_rotation @ _stress_tensor(np.asarray(state["stress"], dtype=float)) @ relative_rotation.T
        transported["stress"] = _stress_voigt(symmetrize(stress)).tolist()
    if "strain" in state:
        strain = relative_rotation @ _strain_tensor(np.asarray(state["strain"], dtype=float)) @ relative_rotation.T
        transported["strain"] = _strain_voigt(symmetrize(strain)).tolist()
    transported["corotation"] = rotation.tolist()
    transported["kinematics"] = "corotational_small_strain"
    return transported


class _CorotationalJ2Mixin:
    """Shared corotational force, state transport and numerical tangent."""

    tangent_step: float = 1.0e-7
    if TYPE_CHECKING:
        node_count: int
        material: object

        def _cached_reference_data(
            self, coords: np.ndarray
        ) -> tuple[tuple[float, np.ndarray], ...]: ...

    def __init__(self, material: object, *, max_corotational_strain: float = 0.05, **kwargs: Any) -> None:
        if not np.isfinite(max_corotational_strain) or max_corotational_strain <= 0.0:
            raise ValueError("max_corotational_strain must be a positive finite value.")
        self.max_corotational_strain = float(max_corotational_strain)
        super().__init__(material, **kwargs)  # type: ignore[call-arg]

    def _force_and_states(
        self,
        coords: np.ndarray,
        local_displacement: np.ndarray,
        states: list[dict[str, Any]] | None,
    ) -> tuple[np.ndarray, list[dict[str, Any]], list[dict[str, Any]]]:
        coords = validate_coords_shape(coords, (self.node_count, 3), self.__class__.__name__)
        local = np.asarray(local_displacement, dtype=float).reshape(self.node_count, 3)
        internal: np.ndarray = np.zeros(3 * self.node_count, dtype=float)
        updated_states: list[dict[str, Any]] = []
        points: list[dict[str, Any]] = []
        identity = np.eye(3)
        for point_index, (measure, gradients) in enumerate(self._cached_reference_data(coords)):
            deformation = identity + local.T @ gradients
            rotation, stretch, determinant = _polar_decomposition(deformation)
            corotated_strain = symmetrize(stretch - identity)
            local_strain_norm = float(np.linalg.norm(corotated_strain))
            if local_strain_norm > self.max_corotational_strain:
                raise ValueError(
                    "Corotational small-strain bound exceeded: "
                    f"||U-I||_F={local_strain_norm:.6e} > {self.max_corotational_strain:.6e}."
                )
            committed = states[point_index] if states and point_index < len(states) else None
            transported = _transport_state(committed, rotation)
            response = evaluate_constitutive(self.material, _strain_voigt(corotated_strain), transported)
            local_stress = _stress_tensor(response.stress)
            first_piola = rotation @ local_stress
            internal += float(measure) * np.einsum("iJ,aJ->ai", first_piola, gradients).reshape(-1)
            trial_state = deepcopy(response.trial_state)
            trial_state["corotation"] = rotation.tolist()
            trial_state["kinematics"] = "corotational_small_strain"
            if response.diagnostics.get("stateful", False):
                updated_states.append(trial_state)
            points.append(
                {
                    "index": point_index,
                    "weight": float(measure),
                    "deformation_gradient": deformation.tolist(),
                    "green_lagrange_strain": (0.5 * (deformation.T @ deformation - identity)).tolist(),
                    "corotation": rotation.tolist(),
                    "right_stretch": stretch.tolist(),
                    "corotational_strain": _strain_voigt(corotated_strain).tolist(),
                    "corotational_strain_norm": local_strain_norm,
                    "strain": _strain_voigt(corotated_strain).tolist(),
                    "stress": response.stress.tolist(),
                    "local_stress": response.stress.tolist(),
                    "first_piola_stress": first_piola.tolist(),
                    "cauchy_stress": (first_piola @ deformation.T / determinant).tolist(),
                    "second_piola_stress": local_stress.tolist(),
                    "det_f": determinant,
                    "material_state": trial_state,
                }
            )
        return internal, updated_states, points

    def internal_force_tangent_state(
        self,
        coords: np.ndarray,
        local_displacement: np.ndarray,
        states: list[dict[str, Any]] | None = None,
    ) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]]]:
        """Return corotational internal force, tangent and trial states."""

        displacement = np.asarray(local_displacement, dtype=float)
        expected = 3 * self.node_count
        if displacement.shape != (expected,) or not np.all(np.isfinite(displacement)):
            raise ValueError(f"{self.__class__.__name__} displacement must have shape ({expected},).")
        internal, updated_states, _ = self._force_and_states(coords, displacement, states)
        tangent: np.ndarray = np.zeros((expected, expected), dtype=float)
        scale = self.tangent_step * max(
            1.0,
            float(np.max(np.abs(displacement))) if displacement.size else 0.0,
            float(np.max(np.abs(coords))) if np.asarray(coords).size else 0.0,
        )
        for column in range(expected):
            plus = displacement.copy()
            minus = displacement.copy()
            plus[column] += scale
            minus[column] -= scale
            force_plus, _, _ = self._force_and_states(coords, plus, states)
            force_minus, _, _ = self._force_and_states(coords, minus, states)
            tangent[:, column] = (force_plus - force_minus) / (2.0 * scale)
        return internal, symmetrize(tangent), updated_states

    def internal_force_and_tangent(
        self,
        coords: np.ndarray,
        local_displacement: np.ndarray,
        states: list[dict[str, Any]] | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return the state-aware corotational kernel without trial states."""

        internal, tangent, _ = self.internal_force_tangent_state(coords, local_displacement, states)
        return internal, tangent

    def integration_point_results(
        self,
        coords: np.ndarray,
        local_displacement: np.ndarray,
        states: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Return local corotational and global stress measures for post-processing."""

        _, _, points = self._force_and_states(coords, local_displacement, states)
        return points


class CorotationalJ2Tet4Element(_CorotationalJ2Mixin, TotalLagrangianJ2Tet4Element):
    """Corotational small-strain J2 TET4 element."""


class CorotationalJ2Tet10Element(_CorotationalJ2Mixin, TotalLagrangianJ2Tet10Element):
    """Corotational small-strain J2 TET10 element."""


class CorotationalJ2Hex8Element(_CorotationalJ2Mixin, TotalLagrangianJ2Hex8Element):
    """Corotational small-strain J2 HEX8 element."""


class CorotationalJ2Hex20Element(_CorotationalJ2Mixin, TotalLagrangianJ2Hex20Element):
    """Corotational small-strain J2 HEX20 element."""


__all__ = [
    "CorotationalJ2Hex8Element",
    "CorotationalJ2Hex20Element",
    "CorotationalJ2Tet4Element",
    "CorotationalJ2Tet10Element",
]
