"""Explicitly experimental mean-divergence HEX8 EAS element.

This first adapter is limited to homogeneous small-strain, isotropic,
linear-static meshes. It is not a qualified element formulation.
"""

from __future__ import annotations

import numpy as np

from solveur.core.errors import InputValidationError
from solveur.elements.solid.common import strain_displacement_from_gradients
from solveur.elements.solid.hex8 import Hex8Element
from solveur.loads.entities import BodyLoad, GravityLoad, SurfaceLoad
from solveur.materials.solid import SolidMaterial

HEX8_EAS_EXPERIMENTAL = "HEX8_EAS_EXPERIMENTAL"
HEX8_EAS_FORMULATION_ID = "hex8-eas-restricted-mean-v1"
_VOLUMETRIC_VECTOR = np.asarray((1.0, 1.0, 1.0, 0.0, 0.0, 0.0), dtype=float)
_CONDITION_LIMIT = 1.0e12


def hex8_eas_scope_errors(model: object) -> list[str]:
    """Return reasons a model is outside the bounded experimental route."""
    definitions = tuple(getattr(model, "elements", ()))
    selected = [item for item in definitions if str(getattr(item, "type", "")).upper() == HEX8_EAS_EXPERIMENTAL]
    if not selected:
        return []
    errors: list[str] = []
    analysis = getattr(model, "analysis", None)
    if getattr(analysis, "type", None) != "linear_static":
        errors.append(f"{HEX8_EAS_EXPERIMENTAL} supports linear_static only.")
    if getattr(analysis, "method", None) != "direct":
        errors.append(f"{HEX8_EAS_EXPERIMENTAL} requires analysis method 'direct'.")
    if any(str(getattr(item, "type", "")).upper() != HEX8_EAS_EXPERIMENTAL for item in definitions):
        errors.append(f"{HEX8_EAS_EXPERIMENTAL} currently requires a homogeneous EAS-only solid mesh.")
    if len({getattr(item, "material", None) for item in selected}) != 1:
        errors.append(f"{HEX8_EAS_EXPERIMENTAL} currently requires one shared material.")
    parameters = getattr(analysis, "parameters", {}) or {}
    kinematics = str(parameters.get("kinematics", "small_strain")).strip().lower()
    if kinematics != "small_strain":
        errors.append(f"{HEX8_EAS_EXPERIMENTAL} supports small_strain kinematics only.")
    if getattr(model, "contacts", ()):
        errors.append(f"{HEX8_EAS_EXPERIMENTAL} does not support contact.")
    for attribute, label in (
        ("springs", "discrete springs"),
        ("concentrated_masses", "concentrated masses"),
        ("multipoint_constraints", "multi-point constraints"),
        ("rbe2", "RBE2 constraints"),
        ("rbe3", "RBE3 constraints"),
    ):
        if getattr(model, attribute, ()):
            errors.append(f"{HEX8_EAS_EXPERIMENTAL} does not support {label} in this experimental route.")
    for item in selected:
        material = getattr(model, "materials", {}).get(getattr(item, "material", ""), {})
        if str(material.get("type", "")).strip().lower() != "isotropic_3d":
            errors.append(f"{HEX8_EAS_EXPERIMENTAL} requires material type 'isotropic_3d'.")
            break
    for index, load in enumerate(getattr(model, "distributed_loads", ())):
        if not isinstance(load, (BodyLoad, GravityLoad, SurfaceLoad)):
            errors.append(
                f"{HEX8_EAS_EXPERIMENTAL} does not support distributed load {index} "
                f"({type(load).__name__})."
            )
        elif isinstance(load, SurfaceLoad) and load.follower:
            errors.append(f"{HEX8_EAS_EXPERIMENTAL} does not support follower surface loads.")
    return errors


def require_hex8_eas_scope(model: object) -> None:
    errors = hex8_eas_scope_errors(model)
    if errors:
        raise InputValidationError(" ".join(errors))


class Hex8EASExperimentalElement:
    """Six-mode transverse EAS with mean-free strains and mean divergence.

    The enhanced variables are statically condensed at each element. The
    implementation uses the production HEX8 shape functions and SI material
    matrix, but remains an experimental, linear-static-only route.
    """

    node_count = 8
    integration_point_count = 8
    integration_points = Hex8Element.integration_points
    formulation_id = HEX8_EAS_FORMULATION_ID
    maturity = "EXPERIMENTAL"
    qualification_status = "NOT_ASSESSED"

    def __init__(self, material: SolidMaterial):
        if type(material) is not SolidMaterial:
            raise TypeError("HEX8_EAS_EXPERIMENTAL supports SolidMaterial only.")
        if not np.isfinite((material.E, material.nu, material.density)).all():
            raise ValueError("HEX8_EAS_EXPERIMENTAL material parameters must be finite.")
        if material.E <= 0.0 or not (-1.0 < material.nu < 0.5):
            raise ValueError("HEX8_EAS_EXPERIMENTAL requires E > 0 and -1 < nu < 0.5.")
        self.material = material
        self.bulk_modulus = float(material.E / (3.0 * (1.0 - 2.0 * material.nu)))
        self.shear_modulus = float(material.E / (2.0 * (1.0 + material.nu)))
        if not np.isfinite((self.bulk_modulus, self.shear_modulus)).all():
            raise ValueError("HEX8_EAS_EXPERIMENTAL moduli are not finite.")
        self.deviatoric_root = np.zeros((5, 6), dtype=float)
        self.deviatoric_root[0, :3] = np.array([1.0, -1.0, 0.0]) * np.sqrt(self.shear_modulus)
        self.deviatoric_root[1, :3] = np.array([1.0, 1.0, -2.0]) * np.sqrt(self.shear_modulus / 3.0)
        self.deviatoric_root[2:, 3:] = np.eye(3) * np.sqrt(self.shear_modulus)
        self.deviatoric = self.deviatoric_root.T @ self.deviatoric_root
        self._standard = Hex8Element(material)

    @classmethod
    def validate_geometry(cls, coords: np.ndarray) -> None:
        """Validate the standard HEX8 map plus the center map used by EAS."""
        xyz = np.asarray(coords, dtype=float)
        Hex8Element.validate_geometry(xyz)
        determinant_tolerance = Hex8Element._jacobian_determinant_tolerance(xyz)
        determinant = Hex8Element.jacobian_determinant(xyz, (0.0, 0.0, 0.0))
        if not np.isfinite(determinant) or determinant <= determinant_tolerance:
            raise InputValidationError(
                "HEX8_EAS_EXPERIMENTAL has an invalid center Jacobian determinant."
            )

    @staticmethod
    def _enrichment_strain_matrix(gradients: np.ndarray) -> np.ndarray:
        """Map nine parent-axis bubble amplitudes to engineering strain."""
        values = np.asarray(gradients, dtype=float)
        if values.shape != (3, 3):
            raise ValueError("EAS bubble gradients must have shape (3, 3).")
        matrix = np.zeros((6, 9), dtype=float)
        for axis in range(3):
            gx, gy, gz = values[axis]
            column = 3 * axis
            matrix[0, column] = gx
            matrix[1, column + 1] = gy
            matrix[2, column + 2] = gz
            matrix[3, column:column + 2] = (gy, gx)
            matrix[4, column + 1:column + 3] = (gz, gy)
            matrix[5, (column, column + 2)] = (gz, gx)
        return matrix

    @classmethod
    def _transverse_basis(cls, coords: np.ndarray) -> np.ndarray:
        """Map six amplitudes into planes normal to the center tangents."""
        jacobian = Hex8Element.jacobian(coords, (0.0, 0.0, 0.0))
        basis = np.zeros((9, 6), dtype=float)
        for axis in range(3):
            tangent = np.asarray(jacobian[axis], dtype=float)
            norm = float(np.linalg.norm(tangent))
            if not np.isfinite(norm) or norm <= 0.0:
                raise InputValidationError("HEX8_EAS_EXPERIMENTAL has a degenerate center tangent.")
            direction = tangent / norm
            reference = np.eye(3)[int(np.argmin(np.abs(direction)))]
            first = np.cross(direction, reference)
            first_norm = float(np.linalg.norm(first))
            if not np.isfinite(first_norm) or first_norm <= 0.0:
                raise InputValidationError("HEX8_EAS_EXPERIMENTAL could not construct a transverse basis.")
            first /= first_norm
            second = np.cross(direction, first)
            basis[3 * axis:3 * axis + 3, 2 * axis] = first
            basis[3 * axis:3 * axis + 3, 2 * axis + 1] = second
        return basis

    def _operators(self, coords: np.ndarray) -> dict[str, object]:
        xyz = np.asarray(coords, dtype=float)
        if xyz.shape != (8, 3) or not np.all(np.isfinite(xyz)):
            raise InputValidationError("HEX8_EAS_EXPERIMENTAL coordinates must be a finite (8, 3) array.")
        xyz = xyz - xyz[0]
        self.validate_geometry(xyz)
        determinant_tolerance = Hex8Element._jacobian_determinant_tolerance(xyz)
        point_set = (*self.integration_points, (0.0, 0.0, 0.0))
        determinants = np.asarray(
            [Hex8Element.jacobian_determinant(xyz, point) for point in point_set], dtype=float
        )
        if not np.all(np.isfinite(determinants)) or np.any(determinants <= determinant_tolerance):
            raise InputValidationError("HEX8_EAS_EXPERIMENTAL has an invalid center or Gauss Jacobian.")

        b_matrices: list[np.ndarray] = []
        weights: list[float] = []
        raw_modes: list[np.ndarray] = []
        try:
            for point, determinant in zip(self.integration_points, determinants[:-1], strict=True):
                jacobian = Hex8Element.jacobian(xyz, point)
                inverse_transpose = np.linalg.inv(jacobian).T
                gradients = Hex8Element.shape_derivatives_reference(point) @ inverse_transpose
                b_matrices.append(strain_displacement_from_gradients(gradients))
                weights.append(float(determinant))
                bubble_gradients = np.diag(-2.0 * np.asarray(point, dtype=float)) @ inverse_transpose
                raw_modes.append(self._enrichment_strain_matrix(bubble_gradients))
        except np.linalg.LinAlgError as exc:
            raise InputValidationError("HEX8_EAS_EXPERIMENTAL Jacobian inversion failed.") from exc

        weight_array = np.asarray(weights, dtype=float)
        volume = float(np.sum(weight_array))
        if not np.isfinite(volume) or volume <= 0.0:
            raise InputValidationError("HEX8_EAS_EXPERIMENTAL volume is not finite and positive.")
        raw = np.asarray(raw_modes, dtype=float)
        mean = np.einsum("i,ijk->jk", weight_array, raw) / volume
        transverse = self._transverse_basis(xyz)
        modes = (raw - mean) @ transverse
        b_array = np.asarray(b_matrices, dtype=float)
        divergence = np.einsum("i,ij->j", weight_array, b_array[:, :3, :].sum(axis=1)) / volume

        base_deviatoric = np.zeros((24, 24), dtype=float)
        coupling = np.zeros((24, 6), dtype=float)
        internal = np.zeros((6, 6), dtype=float)
        for weight, b_matrix, mode in zip(weight_array, b_array, modes, strict=True):
            base_deviatoric += weight * (b_matrix.T @ self.deviatoric @ b_matrix)
            coupling += weight * (b_matrix.T @ self.deviatoric @ mode)
            internal += weight * (mode.T @ self.deviatoric @ mode)
        internal = 0.5 * (internal + internal.T)
        if not np.all(np.isfinite(internal)):
            raise InputValidationError("HEX8_EAS_EXPERIMENTAL condensed block contains non-finite values.")
        try:
            eigenvalues = np.linalg.eigvalsh(internal)
        except np.linalg.LinAlgError as exc:
            raise InputValidationError("HEX8_EAS_EXPERIMENTAL condensed block eigensolve failed.") from exc
        if not np.all(np.isfinite(eigenvalues)) or eigenvalues[0] <= 0.0:
            raise InputValidationError("HEX8_EAS_EXPERIMENTAL condensed block is not positive definite.")
        condition = float(eigenvalues[-1] / eigenvalues[0])
        if not np.isfinite(condition) or condition > _CONDITION_LIMIT:
            raise InputValidationError(
                f"HEX8_EAS_EXPERIMENTAL condensed block condition {condition:.6e} exceeds {_CONDITION_LIMIT:.1e}."
            )
        root_weight = np.sqrt(weight_array)[:, None, None]
        raw_factors = (root_weight * (self.deviatoric_root @ b_array)).reshape(-1, 24)
        weighted_modes = (root_weight * (self.deviatoric_root @ modes)).reshape(-1, 6)
        try:
            q, r = np.linalg.qr(weighted_modes, mode="reduced")
            solved_coupling = np.linalg.solve(r, q.T @ raw_factors)
        except np.linalg.LinAlgError as exc:
            raise InputValidationError("HEX8_EAS_EXPERIMENTAL QR condensation failed.") from exc
        if not np.all(np.isfinite(solved_coupling)):
            raise InputValidationError("HEX8_EAS_EXPERIMENTAL QR condensation contains non-finite values.")

        deviatoric_factors = raw_factors - weighted_modes @ solved_coupling
        volumetric_factor = np.sqrt(self.bulk_modulus * volume) * divergence
        factors = np.vstack((deviatoric_factors, volumetric_factor))
        stiffness = factors.T @ factors
        if not np.all(np.isfinite(stiffness)):
            raise InputValidationError("HEX8_EAS_EXPERIMENTAL stiffness contains non-finite values.")
        return {
            "coordinates": xyz,
            "b_matrices": b_array,
            "weights": weight_array,
            "volume": volume,
            "mean_divergence": divergence,
            "transverse_basis": transverse,
            "enhanced_modes": modes,
            "base_deviatoric": base_deviatoric,
            "coupling": coupling,
            "condensed_block": internal,
            "condition": condition,
            "solved_coupling": solved_coupling,
            "strain_factors": factors,
            "stiffness": stiffness,
        }

    def stiffness(self, coords: np.ndarray) -> np.ndarray:
        """Return the condensed 24 by 24 tangent for the mean-divergence route."""
        return np.asarray(self._operators(coords)["stiffness"], dtype=float)

    def recover(self, coords: np.ndarray, local_displacement: np.ndarray) -> dict[str, object]:
        """Recover enhanced amplitudes, forces, stresses and energy consistently."""
        displacement = np.asarray(local_displacement, dtype=float)
        if displacement.shape != (24,) or not np.all(np.isfinite(displacement)):
            raise InputValidationError("HEX8_EAS_EXPERIMENTAL displacement must be a finite vector of size 24.")
        operators = self._operators(coords)
        coupling_solution = np.asarray(operators["solved_coupling"], dtype=float)
        alpha = -(coupling_solution @ displacement)
        b_matrices = np.asarray(operators["b_matrices"], dtype=float)
        weights = np.asarray(operators["weights"], dtype=float)
        modes = np.asarray(operators["enhanced_modes"], dtype=float)
        divergence = np.asarray(operators["mean_divergence"], dtype=float)
        pressure = float(self.bulk_modulus * (divergence @ displacement))
        strains = np.einsum("qij,j->qi", b_matrices, displacement) + np.einsum("qij,j->qi", modes, alpha)
        stresses = strains @ self.deviatoric.T + pressure * _VOLUMETRIC_VECTOR
        factors = np.asarray(operators["strain_factors"], dtype=float)
        weighted_strain = factors @ displacement
        force = factors.T @ weighted_strain
        deviatoric_energy = 0.0
        deviatoric_energy_density = np.zeros(len(weights), dtype=float)
        for point_index, weight in enumerate(weights):
            density = float(np.sum(weighted_strain[:-1].reshape(8, 5)[point_index] ** 2) / (2 * weight))
            deviatoric_energy_density[point_index] = density
            deviatoric_energy += weight * density
        volumetric_energy_density = 0.5 * self.bulk_modulus * float((divergence @ displacement) ** 2)
        volumetric_energy = 0.5 * self.bulk_modulus * float(operators["volume"]) * float(
            (divergence @ displacement) ** 2
        )
        stiffness = np.asarray(operators["stiffness"], dtype=float)
        matrix_force = stiffness @ displacement
        relative_force_gap = float(np.linalg.norm(force - matrix_force) / max(np.linalg.norm(force), 1.0e-30))
        return {
            **operators,
            "enhanced_variables": alpha,
            "mean_volumetric_stress": pressure,
            "strains": strains,
            "stresses": stresses,
            "internal_force": force,
            "matrix_force": matrix_force,
            "force_tangent_relative_gap": relative_force_gap,
            "deviatoric_energy": deviatoric_energy,
            "deviatoric_energy_density": deviatoric_energy_density,
            "volumetric_energy_density": volumetric_energy_density,
            "volumetric_energy": volumetric_energy,
            "energy": deviatoric_energy + volumetric_energy,
            "maturity": self.maturity,
            "qualification_status": self.qualification_status,
            "formulation_id": self.formulation_id,
        }
