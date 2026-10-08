"""Bounded corotational small-strain J2 solid elements.

This module lives beside, rather than inside, the existing Green--Lagrange /
second-Piola research path. The default ``legacy_corotational_j2/v1`` route
retains its original transported-state, ``P=R T_local`` and finite-difference
tangent behavior. An explicitly selected
``corrected_corotational_biot_j2/v1`` kernel implements the R1 material-frame
state and exact polar-adjoint internal force, but intentionally has no global
Newton tangent, public stress aggregation, or checkpoint migration yet.

Both routes are bounded small-local-strain models, not general finite-strain
plasticity. The corrected force-only kernel cannot be used as a validated
nonlinear analysis route until WP08-R3 supplies its compatible tangent and
result contracts.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import TYPE_CHECKING, Any, Mapping

import numpy as np

from solveur.core.nonlinear.contracts import evaluate_constitutive
from solveur.elements.solid.common import symmetrize, validate_coords_shape
from solveur.elements.solid.total_lagrangian_j2 import (
    TotalLagrangianJ2Hex8Element,
    TotalLagrangianJ2Hex20Element,
    TotalLagrangianJ2Tet4Element,
    TotalLagrangianJ2Tet10Element,
)
from solveur.materials.solid import VonMisesElastoplasticMaterial


LEGACY_COROTATIONAL_J2 = "legacy_corotational_j2/v1"
CORRECTED_COROTATIONAL_J2 = "corrected_corotational_biot_j2/v1"
CORRECTED_COROTATIONAL_STATE = "corotational_j2_state/v2"
CORRECTED_STRESS_SEMANTICS = "corotational_stress/v2"


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


def _corrected_polar_kinematics(
    deformation: np.ndarray, *, max_local_strain: float
) -> tuple[np.ndarray, np.ndarray, float]:
    """Compute and verify the bounded right polar split required by R1."""

    if not np.isfinite(max_local_strain) or not (0.0 < max_local_strain <= 0.05):
        raise ValueError("Corrected local-strain limit must be finite, positive and no greater than 0.05.")
    value = np.asarray(deformation, dtype=float)
    if value.shape != (3, 3) or not np.all(np.isfinite(value)):
        raise ValueError("Corrected corotational deformation gradient must be finite with shape (3, 3).")
    determinant = float(np.linalg.det(value))
    if not np.isfinite(determinant) or determinant <= 1.0e-10:
        raise ValueError(f"Invalid corrected corotational determinant {determinant:.6e}.")
    left, singular_values, right_transpose = np.linalg.svd(value)
    rotation = left @ right_transpose
    stretch = right_transpose.T @ np.diag(singular_values) @ right_transpose
    # Remove only SVD roundoff from the symmetric polar factor, never from a stress.
    stretch = 0.5 * (stretch + stretch.T)
    scale = max(float(np.linalg.norm(value)), 1.0)
    reconstruction = float(np.linalg.norm(value - rotation @ stretch)) / scale
    orthogonality = float(np.linalg.norm(rotation.T @ rotation - np.eye(3)))
    symmetry = float(np.linalg.norm(stretch - stretch.T)) / max(float(np.linalg.norm(stretch)), 1.0)
    stretches = np.linalg.eigvalsh(stretch)
    strain_norm = float(np.linalg.norm(stretch - np.eye(3)))
    if (
        not np.all(np.isfinite(rotation))
        or not np.all(np.isfinite(stretch))
        or reconstruction > 1.0e-12
        or orthogonality > 1.0e-12
        or symmetry > 1.0e-12
        or float(np.linalg.det(rotation)) <= 0.0
        or float(np.min(stretches)) <= 0.0
    ):
        raise ValueError(
            "Corrected corotational polar decomposition failed its reconstruction, "
            "orthogonality, symmetry or positive-stretch checks."
        )
    if strain_norm > max_local_strain:
        raise ValueError(
            f"Corrected corotational small-strain bound exceeded: ||U-I||_F={strain_norm:.6e} > {max_local_strain:.6e}."
        )
    return rotation, stretch, determinant


def _polar_stretch_directional_derivative(
    rotation: np.ndarray, stretch: np.ndarray, delta_deformation: np.ndarray
) -> np.ndarray:
    """Apply the exact right-polar differential using its skew Sylvester solve."""

    rotation = np.asarray(rotation, dtype=float)
    stretch = np.asarray(stretch, dtype=float)
    delta_deformation = np.asarray(delta_deformation, dtype=float)
    if (
        rotation.shape != (3, 3)
        or stretch.shape != (3, 3)
        or delta_deformation.shape != (3, 3)
        or not np.all(np.isfinite(rotation))
        or not np.all(np.isfinite(stretch))
        or not np.all(np.isfinite(delta_deformation))
    ):
        raise ValueError("Polar differential inputs must be finite 3x3 tensors.")
    stretch_symmetry = float(np.linalg.norm(stretch - stretch.T)) / max(float(np.linalg.norm(stretch)), 1.0)
    if stretch_symmetry > 1.0e-12:
        raise ValueError("Polar differential requires a symmetric right stretch.")
    eigenvalues, basis = np.linalg.eigh(stretch)
    if float(np.min(eigenvalues)) <= 0.0:
        raise ValueError("Polar differential requires a positive-definite right stretch.")
    local_increment = basis.T @ rotation.T @ delta_deformation @ basis
    omega_local: np.ndarray = np.zeros((3, 3), dtype=float)
    for row in range(3):
        for column in range(row + 1, 3):
            value = (local_increment[row, column] - local_increment[column, row]) / (
                eigenvalues[row] + eigenvalues[column]
            )
            omega_local[row, column] = value
            omega_local[column, row] = -value
    omega = basis @ omega_local @ basis.T
    local_frame_increment = rotation.T @ delta_deformation
    delta_stretch = local_frame_increment - omega @ stretch
    return 0.5 * (delta_stretch + delta_stretch.T)


def _corrected_first_piola_from_biot_stress(
    rotation: np.ndarray, stretch: np.ndarray, biot_stress: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Return the exact polar-adjoint nominal stress and its material-frame map."""

    rotation = np.asarray(rotation, dtype=float)
    stretch = np.asarray(stretch, dtype=float)
    stress = np.asarray(biot_stress, dtype=float)
    if (
        rotation.shape != (3, 3)
        or stretch.shape != (3, 3)
        or stress.shape != (3, 3)
        or not np.all(np.isfinite(rotation))
        or not np.all(np.isfinite(stretch))
        or not np.all(np.isfinite(stress))
    ):
        raise ValueError("Corrected polar-adjoint inputs must be finite 3x3 tensors.")
    stretch_symmetry = float(np.linalg.norm(stretch - stretch.T)) / max(float(np.linalg.norm(stretch)), 1.0)
    if stretch_symmetry > 1.0e-12:
        raise ValueError("Corrected polar-adjoint requires a symmetric right stretch.")
    stress_scale = max(float(np.linalg.norm(stress)), 1.0)
    if float(np.linalg.norm(stress - stress.T)) / stress_scale > 1.0e-12:
        raise ValueError("Biot-conjugate material stress must be symmetric.")
    if float(np.linalg.norm(rotation.T @ rotation - np.eye(3))) > 1.0e-12 or float(np.linalg.det(rotation)) <= 0.0:
        raise ValueError("Corrected polar-adjoint requires a proper orthogonal rotation.")
    stretches, basis = np.linalg.eigh(stretch)
    if float(np.min(stretches)) <= 0.0:
        raise ValueError("Corrected polar-adjoint map requires positive principal stretches.")
    stress_local = basis.T @ stress @ basis
    nominal_local: np.ndarray = np.empty((3, 3), dtype=float)
    for row in range(3):
        for column in range(3):
            if row == column:
                nominal_local[row, column] = stress_local[row, column]
            else:
                denominator = stretches[row] + stretches[column]
                nominal_local[row, column] = 2.0 * stretches[row] * stress_local[row, column] / denominator
    nominal_material = basis @ nominal_local @ basis.T
    first_piola = rotation @ nominal_material
    angular_tensor = nominal_material @ stretch
    angular_scale = max(float(np.linalg.norm(angular_tensor)), 1.0)
    angular_error = float(np.linalg.norm(angular_tensor - angular_tensor.T)) / angular_scale
    if not np.all(np.isfinite(first_piola)) or angular_error > 1.0e-12:
        raise ArithmeticError("Corrected polar-adjoint failed the unsymmetrized angular-momentum identity.")
    return first_piola, nominal_material


def _corrected_stress_measures(
    deformation: np.ndarray,
    first_piola: np.ndarray,
    determinant: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Reconstruct raw PK2 and Cauchy tensors and reject loss of symmetry."""

    deformation = np.asarray(deformation, dtype=float)
    first_piola = np.asarray(first_piola, dtype=float)
    if (
        deformation.shape != (3, 3)
        or first_piola.shape != (3, 3)
        or not np.all(np.isfinite(deformation))
        or not np.all(np.isfinite(first_piola))
        or not np.isfinite(determinant)
        or determinant <= 1.0e-10
    ):
        raise ValueError("Corrected stress transformations require finite admissible F, P and J.")
    determinant_from_f = float(np.linalg.det(deformation))
    determinant_scale = max(abs(determinant_from_f), abs(determinant), 1.0)
    if abs(determinant_from_f - determinant) / determinant_scale > 1.0e-12:
        raise ValueError("Corrected stress transformations require J=det(F).")
    second_piola = np.linalg.solve(deformation, first_piola)
    cauchy = first_piola @ deformation.T / determinant
    for name, tensor in (("PK2", second_piola), ("Cauchy", cauchy)):
        scale = max(float(np.linalg.norm(tensor)), 1.0)
        skew = float(np.linalg.norm(tensor - tensor.T)) / scale
        if not np.all(np.isfinite(tensor)) or skew > 1.0e-10:
            raise ArithmeticError(
                f"Corrected {name} stress failed its unsymmetrized symmetry check (relative skew={skew:.6e})."
            )
    return second_piola, cauchy


def _corrected_material_identity(material: VonMisesElastoplasticMaterial) -> str:
    """Hash the exact material parameters consumed by the corrected local return."""

    parameters = {
        "material_type": f"{type(material).__module__}.{type(material).__qualname__}",
        "young_modulus": float(material.E),
        "poisson_ratio": float(material.nu),
        "yield_stress": float(material.yield_stress),
        "hardening_modulus": float(material.hardening_modulus),
        "density": float(material.density),
    }
    payload = json.dumps(parameters, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(b"qf-corrected-corotational-j2-material/v1\0" + payload.encode()).hexdigest()


def _corrected_initial_state(material: VonMisesElastoplasticMaterial) -> dict[str, Any]:
    """Create an explicitly versioned fresh state for a corrected analysis."""

    identity = _corrected_material_identity(material)
    return {
        "formulation_id": CORRECTED_COROTATIONAL_J2,
        "state_schema": CORRECTED_COROTATIONAL_STATE,
        "material_identity": identity,
        "model": "von_mises_isotropic_hardening",
        "elastic": True,
        "plastic_strain": [0.0] * 6,
        "equivalent_plastic_strain": 0.0,
        "plastic_dissipation": 0.0,
        "hardening_energy": 0.0,
        "strain": [0.0] * 6,
        "stress": [0.0] * 6,
        "yield_function": -float(material.yield_stress),
        "plastic_multiplier": 0.0,
    }


def _validate_corrected_state(state: Mapping[str, Any], material: VonMisesElastoplasticMaterial) -> dict[str, Any]:
    """Validate a corrected state without migrating legacy or unknown state."""

    if state.get("formulation_id") != CORRECTED_COROTATIONAL_J2:
        raise ValueError("Corrected J2 refuses legacy or unidentified material states.")
    if state.get("state_schema") != CORRECTED_COROTATIONAL_STATE:
        raise ValueError("Corrected J2 refuses an unsupported constitutive-state schema.")
    if state.get("material_identity") != _corrected_material_identity(material):
        raise ValueError("Corrected J2 state material identity does not match this material.")
    required = (
        "plastic_strain",
        "equivalent_plastic_strain",
        "plastic_dissipation",
        "hardening_energy",
        "strain",
        "stress",
    )
    if any(name not in state for name in required):
        raise ValueError("Corrected J2 state is missing required schema-v2 fields.")
    copied = deepcopy(dict(state))
    plastic = np.asarray(copied["plastic_strain"], dtype=float)
    strain = np.asarray(copied["strain"], dtype=float)
    stress = np.asarray(copied["stress"], dtype=float)
    if (
        plastic.shape != (6,)
        or strain.shape != (6,)
        or stress.shape != (6,)
        or not np.all(np.isfinite(plastic))
        or not np.all(np.isfinite(strain))
        or not np.all(np.isfinite(stress))
    ):
        raise ValueError("Corrected J2 state tensors must be finite six-component Voigt values.")
    plastic_tensor = _strain_tensor(plastic)
    state_roundoff = 128.0 * np.finfo(float).eps * max(float(np.linalg.norm(plastic_tensor)), 1.0)
    if abs(float(np.trace(plastic_tensor))) > state_roundoff:
        raise ValueError("Corrected J2 plastic strain must be deviatoric in the material frame.")
    alpha = float(copied["equivalent_plastic_strain"])
    dissipation = float(copied["plastic_dissipation"])
    hardening_energy = float(copied["hardening_energy"])
    if (
        not np.isfinite(alpha)
        or not np.isfinite(dissipation)
        or not np.isfinite(hardening_energy)
        or alpha < 0.0
        or dissipation < 0.0
        or hardening_energy < 0.0
    ):
        raise ValueError("Corrected J2 scalar state fields must be finite and non-negative.")
    expected_hardening = 0.5 * float(material.hardening_modulus) * alpha**2
    if abs(hardening_energy - expected_hardening) > 128.0 * np.finfo(float).eps * max(abs(expected_hardening), 1.0):
        raise ValueError("Corrected J2 hardening-energy state is inconsistent with alpha.")
    expected_dissipation = float(material.yield_stress) * alpha
    if abs(dissipation - expected_dissipation) > 128.0 * np.finfo(float).eps * max(abs(expected_dissipation), 1.0):
        raise ValueError("Corrected J2 dissipation state is inconsistent with accepted plastic history.")
    return copied


def _evaluate_corrected_material_state(
    material: VonMisesElastoplasticMaterial,
    biot_strain: np.ndarray,
    accepted_state: Mapping[str, Any],
) -> tuple[np.ndarray, dict[str, Any], dict[str, Any]]:
    """Reuse the existing J2 radial return with a strict corrected state seam."""

    accepted = _validate_corrected_state(accepted_state, material)
    strain_voigt = _strain_voigt(biot_strain)
    response = evaluate_constitutive(material, strain_voigt, accepted)
    stress_voigt = np.asarray(response.stress, dtype=float)
    if stress_voigt.shape != (6,) or not np.all(np.isfinite(stress_voigt)):
        raise ValueError("Corrected J2 radial return produced invalid stress values.")
    if not response.diagnostics.get("stateful", False):
        raise ValueError("Corrected corotational J2 requires a stateful isotropic J2 material.")
    material_trial = response.trial_state
    alpha_old = float(accepted["equivalent_plastic_strain"])
    alpha_new = float(material_trial.get("equivalent_plastic_strain", float("nan")))
    delta_alpha = alpha_new - alpha_old
    if not np.isfinite(alpha_new) or delta_alpha < -1.0e-12:
        raise ValueError("Corrected J2 radial return produced a non-monotone plastic history.")
    delta_alpha = max(delta_alpha, 0.0)
    plastic = np.asarray(material_trial.get("plastic_strain", []), dtype=float)
    if plastic.shape != (6,) or not np.all(np.isfinite(plastic)):
        raise ValueError("Corrected J2 radial return produced invalid plastic strain.")
    plastic_tensor = _strain_tensor(plastic)
    state_roundoff = 128.0 * np.finfo(float).eps * max(float(np.linalg.norm(plastic_tensor)), 1.0)
    if abs(float(np.trace(plastic_tensor))) > state_roundoff:
        raise ValueError("Corrected J2 radial return violated deviatoric plastic flow.")
    stress_tensor = _stress_tensor(stress_voigt)
    if not np.all(np.isfinite(stress_tensor)):
        raise ValueError("Corrected J2 radial return produced non-finite stress.")
    yield_function = float(material_trial.get("yield_function", float("nan")))
    if not np.isfinite(yield_function):
        raise ValueError("Corrected J2 radial return produced a non-finite yield diagnostic.")
    new_state = {
        "formulation_id": CORRECTED_COROTATIONAL_J2,
        "state_schema": CORRECTED_COROTATIONAL_STATE,
        "material_identity": accepted["material_identity"],
        "model": "von_mises_isotropic_hardening",
        "elastic": bool(material_trial.get("elastic", False)),
        "plastic_strain": plastic.tolist(),
        "equivalent_plastic_strain": alpha_new,
        "plastic_dissipation": float(material.yield_stress) * alpha_new,
        "hardening_energy": 0.5 * float(material.hardening_modulus) * alpha_new**2,
        "strain": strain_voigt.tolist(),
        "stress": stress_voigt.tolist(),
        "yield_function": yield_function,
        "plastic_multiplier": delta_alpha,
    }
    if not np.all(np.isfinite(list(new_state["strain"]) + list(new_state["stress"]))):
        raise ValueError("Corrected J2 trial state contains non-finite components.")
    diagnostics = {
        "elastic": new_state["elastic"],
        "yield_function": new_state["yield_function"],
        "plastic_multiplier": delta_alpha,
    }
    return stress_tensor, new_state, diagnostics


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
    """Legacy corotational route plus an isolated corrected force-only kernel."""

    tangent_step: float = 1.0e-7
    if TYPE_CHECKING:
        node_count: int
        material: object

        def _cached_reference_data(
            self, coords: np.ndarray
        ) -> tuple[tuple[float, np.ndarray], ...]: ...

    def __init__(
        self,
        material: object,
        *,
        max_corotational_strain: float = 0.05,
        formulation_id: str = LEGACY_COROTATIONAL_J2,
        **kwargs: Any,
    ) -> None:
        if not np.isfinite(max_corotational_strain) or max_corotational_strain <= 0.0:
            raise ValueError("max_corotational_strain must be a positive finite value.")
        if formulation_id not in {LEGACY_COROTATIONAL_J2, CORRECTED_COROTATIONAL_J2}:
            raise ValueError(f"Unknown corotational J2 formulation ID: {formulation_id!r}.")
        if formulation_id == CORRECTED_COROTATIONAL_J2 and max_corotational_strain > 0.05:
            raise ValueError("Corrected corotational J2 cannot exceed the frozen R1 strain cap of 0.05.")
        if formulation_id == CORRECTED_COROTATIONAL_J2 and type(material) is not VonMisesElastoplasticMaterial:
            raise ValueError(
                "Corrected corotational J2 requires the existing isotropic "
                "VonMisesElastoplasticMaterial implementation."
            )
        self.max_corotational_strain = float(max_corotational_strain)
        self.formulation_id = formulation_id
        super().__init__(material, **kwargs)  # type: ignore[call-arg]

    def corrected_initial_state(self) -> dict[str, Any]:
        """Return a fresh, versioned material state for the corrected kernel."""

        if self.formulation_id != CORRECTED_COROTATIONAL_J2:
            raise ValueError("Select corrected_corotational_biot_j2/v1 explicitly to create its state.")
        if type(self.material) is not VonMisesElastoplasticMaterial:
            raise ValueError("Corrected corotational J2 material type is not supported.")
        return _corrected_initial_state(self.material)

    def corrected_internal_force_state(
        self,
        coords: np.ndarray,
        local_displacement: np.ndarray,
        states: list[dict[str, Any]] | None = None,
    ) -> tuple[np.ndarray, list[dict[str, Any]], list[dict[str, Any]]]:
        """Publicly explicit R2 entry to corrected force/state evaluation."""

        return self._corrected_force_and_states(coords, local_displacement, states)

    def _corrected_force_and_states(
        self,
        coords: np.ndarray,
        local_displacement: np.ndarray,
        states: list[dict[str, Any]] | None = None,
    ) -> tuple[np.ndarray, list[dict[str, Any]], list[dict[str, Any]]]:
        """Evaluate R2 corrected forces and diagnostics without a Newton tangent.

        This explicitly selected diagnostic/kernel API is not wired to nonlinear
        global Newton assembly.  R3 must supply and validate its compatible
        tangent and result migration before that route can be enabled.
        """

        if self.formulation_id != CORRECTED_COROTATIONAL_J2:
            raise ValueError("Corrected force evaluation requires explicit corrected formulation selection.")
        if type(self.material) is not VonMisesElastoplasticMaterial:
            raise ValueError("Corrected corotational J2 material type is not supported.")
        coords = validate_coords_shape(coords, (self.node_count, 3), self.__class__.__name__)
        displacement = np.asarray(local_displacement, dtype=float)
        expected = 3 * self.node_count
        if displacement.shape != (expected,) or not np.all(np.isfinite(displacement)):
            raise ValueError(f"{self.__class__.__name__} displacement must have shape ({expected},).")
        local = displacement.reshape(self.node_count, 3)
        reference_data = self._cached_reference_data(coords)
        if states is None:
            accepted_states = [self.corrected_initial_state() for _ in reference_data]
        else:
            if len(states) != len(reference_data):
                raise ValueError("Corrected J2 accepted-state count must match the integration rule.")
            accepted_states = states

        internal: np.ndarray = np.zeros(expected, dtype=float)
        updated_states: list[dict[str, Any]] = []
        points: list[dict[str, Any]] = []
        identity = np.eye(3)
        for point_index, (measure, gradients) in enumerate(reference_data):
            measure = float(measure)
            gradients = np.asarray(gradients, dtype=float)
            if (
                not np.isfinite(measure)
                or measure <= 0.0
                or gradients.shape != (self.node_count, 3)
                or not np.all(np.isfinite(gradients))
            ):
                raise ValueError(f"Invalid corrected reference integration data at point {point_index}.")
            deformation = identity + local.T @ gradients
            rotation, stretch, determinant = _corrected_polar_kinematics(
                deformation, max_local_strain=self.max_corotational_strain
            )
            biot_strain = stretch - identity
            accepted = accepted_states[point_index]
            biot_stress, trial_state, diagnostics = _evaluate_corrected_material_state(
                self.material, biot_strain, accepted
            )
            first_piola, nominal_material = _corrected_first_piola_from_biot_stress(rotation, stretch, biot_stress)
            second_piola, cauchy = _corrected_stress_measures(deformation, first_piola, determinant)
            internal += measure * np.einsum("iJ,aJ->ai", first_piola, gradients, optimize=True).reshape(expected)
            updated_states.append(trial_state)
            points.append(
                {
                    "index": point_index,
                    "weight": measure,
                    "formulation_id": CORRECTED_COROTATIONAL_J2,
                    "state_schema": CORRECTED_COROTATIONAL_STATE,
                    "semantic_version": CORRECTED_STRESS_SEMANTICS,
                    "deformation_gradient": deformation.tolist(),
                    "rotation": rotation.tolist(),
                    "right_stretch": stretch.tolist(),
                    "biot_strain": _strain_voigt(biot_strain).tolist(),
                    "biot_stress": biot_stress.tolist(),
                    "first_piola_stress": first_piola.tolist(),
                    "second_piola_stress": second_piola.tolist(),
                    "cauchy_stress": cauchy.tolist(),
                    "stress_semantics": {
                        "biot_stress": {
                            "stress_measure": "BIOT_STRESS_CONJUGATE_TO_RIGHT_STRETCH_STRAIN",
                            "stress_frame": "REFERENCE_CONFIGURATION",
                        },
                        "first_piola_stress": {
                            "stress_measure": "FIRST_PIOLA_KIRCHHOFF",
                            "stress_frame": "EXPLICIT_USER_FRAME",
                        },
                        "second_piola_stress": {
                            "stress_measure": "SECOND_PIOLA_KIRCHHOFF",
                            "stress_frame": "REFERENCE_CONFIGURATION",
                        },
                        "cauchy_stress": {
                            "stress_measure": "CAUCHY",
                            "stress_frame": "CURRENT_CONFIGURATION",
                        },
                    },
                    "det_f": determinant,
                    "material_diagnostics": diagnostics,
                    "material_state": deepcopy(trial_state),
                    "public_result_availability": {
                        "status": "UNAVAILABLE",
                        "reason": "WP08-R3 result aggregation and serialization are not implemented.",
                    },
                }
            )
        if not np.all(np.isfinite(internal)):
            raise ValueError("Corrected corotational internal force contains non-finite values.")
        return internal, updated_states, points

    def _force_and_states(
        self,
        coords: np.ndarray,
        local_displacement: np.ndarray,
        states: list[dict[str, Any]] | None,
    ) -> tuple[np.ndarray, list[dict[str, Any]], list[dict[str, Any]]]:
        if self.formulation_id != LEGACY_COROTATIONAL_J2:
            raise RuntimeError(
                "The corrected formulation has a separate force-only API; legacy force/stress semantics are disabled."
            )
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

        if self.formulation_id == CORRECTED_COROTATIONAL_J2:
            raise RuntimeError(
                "Corrected corotational J2 has no production-compatible tangent yet; "
                "global Newton is not ready until WP08-R3."
            )

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

        if self.formulation_id == CORRECTED_COROTATIONAL_J2:
            raise RuntimeError(
                "Corrected stress results are not exposed through legacy post-processing; WP08-R3 is required."
            )

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
    "CORRECTED_COROTATIONAL_J2",
    "CORRECTED_COROTATIONAL_STATE",
    "CORRECTED_STRESS_SEMANTICS",
    "LEGACY_COROTATIONAL_J2",
    "CorotationalJ2Hex8Element",
    "CorotationalJ2Hex20Element",
    "CorotationalJ2Tet4Element",
    "CorotationalJ2Tet10Element",
]
