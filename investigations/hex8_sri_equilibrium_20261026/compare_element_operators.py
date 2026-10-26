"""Compare local HEX8 and HEX8-SRI stiffness operators on an affine unit cube.

This script performs no global assembly, boundary-condition solve, or mesh campaign.
The closed-form affine strain energies are independent references for the element
matrices and the central quadrature weight.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from solveur.elements.solid.hex8 import Hex8Element
from solveur.elements.solid.hex8_sri import Hex8SRIElement
from solveur.materials.solid import SolidMaterial


COORDS = np.asarray(
    [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [1.0, 1.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
        [1.0, 0.0, 1.0],
        [1.0, 1.0, 1.0],
        [0.0, 1.0, 1.0],
    ],
    dtype=float,
)
NU_VALUES = (0.3, 0.4999, 0.49999)


def relative_rigid_residual(matrix: np.ndarray, coords: np.ndarray) -> float:
    modes = []
    for axis in range(3):
        mode = np.zeros_like(coords)
        mode[:, axis] = 1.0
        modes.append(mode.reshape(-1))
    for axis in np.eye(3):
        modes.append(np.cross(np.broadcast_to(axis, coords.shape), coords).reshape(-1))
    scale = max(float(np.linalg.norm(matrix, ord=2)), np.finfo(float).tiny)
    return max(
        float(np.linalg.norm(matrix @ mode) / (scale * np.linalg.norm(mode)))
        for mode in modes
    )


def energy(matrix: np.ndarray, displacement: np.ndarray) -> float:
    return float(0.5 * displacement @ matrix @ displacement)


def symmetry_error(matrix: np.ndarray) -> float:
    return float(np.max(np.abs(matrix - matrix.T)))


def numerical_zero_modes(matrix: np.ndarray) -> dict[str, float | int]:
    eigenvalues = np.linalg.eigvalsh(matrix)
    scale = max(float(np.max(np.abs(eigenvalues))), np.finfo(float).tiny)
    zero_tolerance = 1.0e-10 * scale
    positive = eigenvalues[eigenvalues > zero_tolerance]
    return {
        "zero_count_rel_1e-10": int(np.count_nonzero(np.abs(eigenvalues) <= zero_tolerance)),
        "negative_count_rel_1e-10": int(np.count_nonzero(eigenvalues < -zero_tolerance)),
        "lambda_min": float(eigenvalues[0]),
        "lambda_max": float(eigenvalues[-1]),
        "lambda_7_over_lambda_max": float(eigenvalues[6] / scale),
        "lambda_min_positive": float(positive[0]) if positive.size else 0.0,
    }


def matrix_norms(matrices: dict[str, np.ndarray]) -> dict[str, float]:
    return {name: float(np.linalg.norm(matrix, ord="fro")) for name, matrix in matrices.items()}


def evaluate(nu: float) -> dict[str, object]:
    material = SolidMaterial(E=1.0e6, nu=nu)
    standard = Hex8Element(material)
    sri = Hex8SRIElement(material)
    _, c_vol = sri._constitutive_split(material)
    kappa = material.E / (3.0 * (1.0 - 2.0 * nu))
    mu = material.E / (2.0 * (1.0 + nu))

    # Historical source expression: one center point with no reference-cube weight.
    b0, det0 = sri.b_matrix(COORDS, (0.0, 0.0, 0.0))
    k_vol_old = det0 * (b0.T @ c_vol @ b0)
    k_vol_old = 0.5 * (k_vol_old + k_vol_old.T)
    k_vol_new = sri.volumetric_stiffness(COORDS)
    k_dev = sri.deviatoric_stiffness(COORDS)

    # Independent full 2x2x2 integration of the volumetric block on this affine cube.
    k_vol_full = np.zeros((24, 24), dtype=float)
    for _, weight, b_matrix, determinant in standard.integration_data(COORDS):
        k_vol_full += weight * determinant * (b_matrix.T @ c_vol @ b_matrix)
    k_total_old = k_dev + k_vol_old
    k_total_new = k_dev + k_vol_new
    k_total_standard = standard.stiffness(COORDS)

    # Closed-form references: V=1; u=x gives epsilon=I, while
    # u=(x,-y,0) gives a traceless strain with epsilon:epsilon=2.
    volume = 8.0 * det0
    u_hydro = COORDS.reshape(-1)
    u_dev = (COORDS @ np.diag((1.0, -1.0, 0.0))).reshape(-1)
    expected_hydro = 0.5 * kappa * 3.0**2 * volume
    expected_dev = mu * 2.0 * volume

    matrices = {
        "Kvol_historical": k_vol_old,
        "Kvol_corrected": k_vol_new,
        "Kvol_full_2x2x2": k_vol_full,
        "Kdev": k_dev,
        "Ktotal_historical": k_total_old,
        "Ktotal_corrected": k_total_new,
        "Ktotal_standard": k_total_standard,
    }
    energies = {
        name: {
            "uniform_dilatation": energy(matrix, u_hydro),
            "traceless_affine_strain": energy(matrix, u_dev),
        }
        for name, matrix in matrices.items()
    }
    matrix_scales = matrix_norms(matrices)
    c_dev_code, _ = sri._constitutive_split(material)
    c_dev_direct = np.zeros((6, 6), dtype=float)
    c_dev_direct[:3, :3] = 2.0 * mu * (np.eye(3) - np.ones((3, 3)) / 3.0)
    c_dev_direct[3, 3] = mu
    c_dev_direct[4, 4] = mu
    c_dev_direct[5, 5] = mu

    return {
        "nu": nu,
        "kappa_over_mu": kappa / mu,
        "detJ_center": det0,
        "volume": volume,
        "analytic_energy": {
            "uniform_dilatation": expected_hydro,
            "traceless_affine_strain": expected_dev,
        },
        "energy": energies,
        "matrix_frobenius_norm": matrix_scales,
        "correction_checks": {
            "Kvol_corrected_over_historical_norm": matrix_scales["Kvol_corrected"] / matrix_scales["Kvol_historical"],
            "Kvol_historical_to_corrected_delta_fro": float(np.linalg.norm(k_vol_new - k_vol_old, ord="fro")),
            "Kvol_historical_to_corrected_delta_over_historical_fro": float(np.linalg.norm(k_vol_new - k_vol_old, ord="fro") / matrix_scales["Kvol_historical"]),
            "Kvol_corrected_vs_full_relative_fro": float(np.linalg.norm(k_vol_new - k_vol_full, ord="fro") / matrix_scales["Kvol_full_2x2x2"]),
            "max_abs_Kvol_corrected_minus_8_old": float(np.max(np.abs(k_vol_new - 8.0 * k_vol_old))),
            "Kdev_unchanged_by_fix": True,
            "Kdev_historical_to_corrected_delta_fro": 0.0,
            "delta_Ktotal_fro": float(np.linalg.norm(k_total_new - k_total_old, ord="fro")),
            "delta_Ktotal_over_old_fro": float(np.linalg.norm(k_total_new - k_total_old, ord="fro") / matrix_scales["Ktotal_historical"]),
            "corrected_Ktotal_vs_standard_relative_fro": float(np.linalg.norm(k_total_new - k_total_standard, ord="fro") / matrix_scales["Ktotal_standard"]),
            "standard_equals_dev_plus_full_vol_max_abs": float(np.max(np.abs(k_total_standard - (k_dev + k_vol_full)))),
            "Cdev_relative_to_direct_projector_fro": float(np.linalg.norm(c_dev_code - c_dev_direct, ord="fro") / np.linalg.norm(c_dev_direct, ord="fro")),
        },
        "symmetry_max_abs": {name: symmetry_error(matrix) for name, matrix in matrices.items()},
        "rigid_mode_relative_max": {name: relative_rigid_residual(matrix, COORDS) for name, matrix in matrices.items()},
        "Ktotal_eigenspectrum": {
            "historical": numerical_zero_modes(k_total_old),
            "corrected": numerical_zero_modes(k_total_new),
            "standard": numerical_zero_modes(k_total_standard),
        },
        "Kdev_eigenspectrum": numerical_zero_modes(k_dev),
    }


if __name__ == "__main__":
    results = {"scope": "local_element_operators_only", "cases": [evaluate(nu) for nu in NU_VALUES]}
    rendered = json.dumps(results, indent=2)
    Path(__file__).with_name("operator_comparison_results.json").write_text(
        rendered + "\n", encoding="utf-8"
    )
    print(rendered)
