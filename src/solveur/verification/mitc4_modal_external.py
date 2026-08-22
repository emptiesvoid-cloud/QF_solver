"""Same-mesh MITC4, Navier and Code_Aster modal correlation."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from solveur.elements.shell.mitc4.mesh import MeshFactory
from solveur.api import solve_model
from solveur.core.model import FiniteElementModel
from solveur.verification.mitc4_modal_plate import (
    TEN_MODE_ORDERS,
    Mitc4SimplySupportedPlateStudy,
)


STUDY_ID = "VNV-MITC4-MODAL-CODEASTER-DKQ-004"


@dataclass(frozen=True)
class CodeAsterModalPoint:
    """One Code_Aster mode with its signed nodal transverse shape."""

    frequency_hz: float
    uz: np.ndarray


class CodeAsterModalParser:
    """Parse deterministic modal fields exported by the controlled runner."""

    def parse(
        self,
        path: str | Path,
        *,
        node_count: int,
        minimum_mode_count: int = 10,
    ) -> list[CodeAsterModalPoint]:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        points: list[CodeAsterModalPoint] = []
        for index, item in enumerate(payload.get("modes", [])):
            values = np.asarray(item["uz"], dtype=float)
            if values.shape != (node_count,) or not np.all(np.isfinite(values)):
                raise ValueError(f"Code_Aster mode {index} must contain {node_count} finite UZ values")
            frequency = float(item["frequency_hz"])
            if not np.isfinite(frequency) or frequency <= 0.0:
                raise ValueError(f"Code_Aster mode {index} has an invalid frequency")
            points.append(CodeAsterModalPoint(frequency, values))
        if len(points) < minimum_mode_count:
            raise ValueError(
                "Code_Aster modal correlation requires at least "
                f"{minimum_mode_count} modes"
            )
        return sorted(points, key=lambda point: point.frequency_hz)


class Mitc4CodeAsterModalStudy:
    """Compare ten bending modes on an identical regular square mesh."""

    frequency_difference_limit = 0.03
    navier_error_limit = 0.03
    mac_limit = 0.99

    def __init__(self, *, mesh_size: int = 16) -> None:
        self.mesh_size = int(mesh_size)
        if self.mesh_size < 4:
            raise ValueError("mesh_size must be at least 4")

    def run(self, code_aster_raw: str | Path) -> dict[str, Any]:
        model, quads = build_modal_correlation_model(self.mesh_size)
        result = solve_model(model, enforce_policy=False)
        uz_indices = np.asarray(
            [result.dofs.index(node, "UZ") for node in range(model.node_count)], dtype=int
        )
        mode_count = len(TEN_MODE_ORDERS)
        qf_shapes = np.asarray(result.modes[uz_indices, :mode_count], dtype=float)
        parser = CodeAsterModalParser()
        aster_points = parser.parse(
            code_aster_raw,
            node_count=model.node_count,
            minimum_mode_count=mode_count,
        )[:mode_count]
        aster_shapes = np.column_stack([point.uz for point in aster_points])
        navier_study = Mitc4SimplySupportedPlateStudy(meshes=(self.mesh_size,))
        base_frequency = navier_study.analytical_frequencies_hz()[0] / 2.0
        navier_frequencies = np.asarray(
            [base_frequency * (m * m + n * n) for m, n in TEN_MODE_ORDERS],
            dtype=float,
        )
        navier_shapes = np.column_stack(
            [_navier_shape(model.nodes, m, n) for m, n in TEN_MODE_ORDERS]
        )
        qf_frequencies = np.asarray(result.frequencies_hz[:mode_count], dtype=float)
        aster_frequencies = np.asarray([point.frequency_hz for point in aster_points])
        metrics = {
            "qf_navier_frequency_errors": _relative_errors(qf_frequencies, navier_frequencies),
            "code_aster_navier_frequency_errors": _relative_errors(
                aster_frequencies, navier_frequencies
            ),
            "qf_code_aster_frequency_differences": _relative_errors(
                qf_frequencies, aster_frequencies
            ),
            "qf_navier_mac": _mode_group_mac_summary(qf_shapes, navier_shapes),
            "code_aster_navier_mac": _mode_group_mac_summary(aster_shapes, navier_shapes),
            "qf_code_aster_mac": _mode_group_mac_summary(qf_shapes, aster_shapes),
            "qf_max_relative_residual": float(result.solver["max_relative_residual"]),
            "qf_mass_orthogonality_error": float(result.solver["mass_orthogonality_error"]),
            "qf_stiffness_orthogonality_error": float(
                result.solver["stiffness_diagonal_error"]
            ),
        }
        checks = {
            "qf_navier_frequencies": max(metrics["qf_navier_frequency_errors"])
            <= self.navier_error_limit,
            "code_aster_navier_frequencies": max(
                metrics["code_aster_navier_frequency_errors"]
            )
            <= self.navier_error_limit,
            "same_mesh_frequency_agreement": max(
                metrics["qf_code_aster_frequency_differences"]
            )
            <= self.frequency_difference_limit,
            "qf_navier_shapes": min(metrics["qf_navier_mac"].values()) >= self.mac_limit,
            "code_aster_navier_shapes": min(metrics["code_aster_navier_mac"].values())
            >= self.mac_limit,
            "same_mesh_shape_agreement": min(metrics["qf_code_aster_mac"].values())
            >= self.mac_limit,
            "qf_modal_residual": metrics["qf_max_relative_residual"] <= 1.0e-7,
            "qf_orthogonality": max(
                metrics["qf_mass_orthogonality_error"],
                metrics["qf_stiffness_orthogonality_error"],
            )
            <= 1.0e-7,
        }
        return {
            "study_id": STUDY_ID,
            "status": "PASS" if all(checks.values()) else "FAIL",
            "model": {
                "geometry": "simply-supported square plate 1 m x 1 m x 0.01 m",
                "mesh": [self.mesh_size, self.mesh_size],
                "node_count": model.node_count,
                "element_count": len(model.elements),
                "material": {"E_pa": 70.0e9, "nu": 0.3, "density_kg_m3": 2700.0},
                "same_mesh_and_constraints": True,
                "qf_formulation": "MITC4 Reissner-Mindlin",
                "code_aster_formulation": "DKT/DKQ Kirchhoff",
                "compared_mode_count": mode_count,
                "qf_method": result.method,
                "qf_retained_dof_count": result.solver["dynamic_reduction"][
                    "retained_dof_count"
                ],
            },
            "mode_orders": [list(order) for order in TEN_MODE_ORDERS],
            "frequencies_hz": {
                "navier": navier_frequencies.tolist(),
                "qf_solver": qf_frequencies.tolist(),
                "code_aster": aster_frequencies.tolist(),
            },
            "metrics": metrics,
            "acceptance": {
                "frequency_difference_max": self.frequency_difference_limit,
                "navier_frequency_error_max": self.navier_error_limit,
                "mac_min": self.mac_limit,
                "relative_residual_max": 1.0e-7,
                "orthogonality_error_max": 1.0e-7,
            },
            "checks": checks,
            "limitations": [
                "The analytical reference is Kirchhoff Navier theory for a thin square plate.",
                "Repeated analytical modes are compared as two-dimensional eigenspaces.",
                "Code_Aster DKQ and QF_solver MITC4 are different shell formulations.",
                "This study does not replace a free-free rigid-mode or curved-shell modal campaign.",
            ],
            "_plot_data": {
                "nodes": model.nodes,
                "quads": quads,
                "qf_shapes": qf_shapes,
                "code_aster_shapes": aster_shapes,
                "navier_shapes": navier_shapes,
            },
        }


def build_modal_correlation_model(size: int = 16) -> tuple[FiniteElementModel, np.ndarray]:
    """Build the flat plate with identical physical constraints for both solvers."""
    mesh = MeshFactory.rectangular_plate(size, size, 1.0, 1.0)
    x = mesh.nodes[:, 0]
    y = mesh.nodes[:, 1] + 0.5
    boundary = np.flatnonzero(
        np.isclose(x, 0.0) | np.isclose(x, 1.0) | np.isclose(y, 0.0) | np.isclose(y, 1.0)
    )
    fixed = [
        {"node": node, "dofs": ["UX", "UY", "RZ"]}
        for node in range(mesh.nodes.shape[0])
    ]
    fixed.extend({"node": int(node), "dofs": ["UZ"]} for node in boundary)
    sparse = size >= 24
    model = FiniteElementModel.from_raw(
        analysis={
            "type": "modal",
            "method": "eigsh" if sparse else "eigh",
            "modes": 12,
            "dense_modal_max_dofs": 10000,
            "modal_residual_failure_tolerance": 1.0e-6,
            "arpack_tolerance": 1.0e-11,
            "arpack_maxiter": 10000,
            "arpack_ncv": 36,
        },
        nodes=mesh.nodes.tolist(),
        elements=[
            {"type": "MITC4", "nodes": quad.tolist(), "material": "skin"}
            for quad in mesh.quads
        ],
        materials={
            "skin": {
                "type": "shell_isotropic",
                "E": 70.0e9,
                "nu": 0.3,
                "t": 0.01,
                "density": 2700.0,
                "drilling_scale": 1.0e-4,
            }
        },
        fixed_dofs=fixed,
    )
    return model, mesh.quads


def _navier_shape(nodes: np.ndarray, m: int, n: int) -> np.ndarray:
    return np.sin(m * math.pi * nodes[:, 0]) * np.sin(n * math.pi * (nodes[:, 1] + 0.5))


def _relative_errors(values: np.ndarray, references: np.ndarray) -> list[float]:
    return (np.abs(values - references) / np.maximum(np.abs(references), 1.0e-30)).tolist()


def _mac(first: np.ndarray, second: np.ndarray) -> float:
    numerator = abs(np.vdot(first, second)) ** 2
    denominator = max(float(np.vdot(first, first).real * np.vdot(second, second).real), 1.0e-30)
    return float(numerator / denominator)


def _subspace_mac(first: np.ndarray, second: np.ndarray) -> float:
    first_basis, _ = np.linalg.qr(first)
    second_basis, _ = np.linalg.qr(second)
    singular_values = np.linalg.svd(first_basis.T @ second_basis, compute_uv=False)
    return float(np.min(singular_values) ** 2)


def _mode_group_mac_summary(first: np.ndarray, second: np.ndarray) -> dict[str, float]:
    return {
        "mode_11": _mac(first[:, 0], second[:, 0]),
        "subspace_12_21": _subspace_mac(first[:, 1:3], second[:, 1:3]),
        "mode_22": _mac(first[:, 3], second[:, 3]),
        "subspace_13_31": _subspace_mac(first[:, 4:6], second[:, 4:6]),
        "subspace_23_32": _subspace_mac(first[:, 6:8], second[:, 6:8]),
        "subspace_14_41": _subspace_mac(first[:, 8:10], second[:, 8:10]),
    }
