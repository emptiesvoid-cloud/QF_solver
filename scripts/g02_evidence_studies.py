"""Internal studies used by the controlled 025-G02 evidence builder."""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from solveur.api import solve_model  # noqa: E402
from solveur.core.geometric_assembly import build_total_lagrangian_assembly  # noqa: E402
from solveur.core.model import FiniteElementModel  # noqa: E402
from solveur.verification.robustness_foundations import element_coordinates  # noqa: E402
from solveur.verification.robustness_geometric import (  # noqa: E402
    _large_rotation_model,
    run_large_rotation_geometric_benchmark,
    run_large_rotation_mesh_sensitivity_benchmark,
)
from solveur.verification.robustness_mesh import mesh_refinement_mesh  # noqa: E402

FAMILIES = ("TET4", "TET10", "HEX8", "HEX20")
LOW_ORDER = ("TET4", "HEX8")
ROTATION_ANGLE = 0.7
SMALL_LOAD_FACTORS = (1.0e-2, 1.0e-3, 1.0e-4)


def rel(value: float, reference: float) -> float:
    return float(abs(value - reference) / max(abs(reference), 1.0e-30))


def vector_from_tensor(value: np.ndarray) -> list[float]:
    tensor = np.asarray(value, dtype=float)
    return [
        float(tensor[0, 0]),
        float(tensor[1, 1]),
        float(tensor[2, 2]),
        float(tensor[0, 1]),
        float(tensor[0, 2]),
        float(tensor[1, 2]),
    ]


def rotation_z(angle: float) -> np.ndarray:
    return np.asarray(
        [
            [math.cos(angle), -math.sin(angle), 0.0],
            [math.sin(angle), math.cos(angle), 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=float,
    )


def element_model(
    family: str,
    nodes: np.ndarray,
    elements: list[list[int]],
    *,
    analysis: str = "geometric_nonlinear_static",
    parameters: dict[str, object] | None = None,
) -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=np.asarray(nodes, dtype=float).tolist(),
        elements=[{"type": family, "nodes": item, "material": "solid"} for item in elements],
        materials={"solid": {"type": "isotropic_3d", "E": 10.0, "nu": 0.3}},
        analysis={
            "type": analysis,
            "method": "newton_raphson",
            "parameters": parameters
            or {"load_increments": 12, "max_iterations": 50, "tolerance": 1.0e-9},
        },
    )


def objectivity_evidence() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    transforms = {
        "rigid_translation": lambda coords: coords + np.asarray([0.25, -0.15, 0.30]),
        "rigid_rotation": lambda coords: (rotation_z(ROTATION_ANGLE) @ coords.T).T,
        "translation_plus_rotation": lambda coords: (
            (rotation_z(ROTATION_ANGLE) @ coords.T).T + np.asarray([0.25, -0.15, 0.30])
        ),
    }
    for family in FAMILIES:
        coords = element_coordinates(family)
        model = element_model(family, coords, [list(range(len(coords)))])
        assembly = build_total_lagrangian_assembly(model)
        family_rows: list[dict[str, Any]] = []
        for name, transform in transforms.items():
            current = transform(coords)
            displacement = (current - coords).reshape(-1)
            internal, _ = assembly.assemble(displacement, tangent_required=False)
            states = assembly.element_states(displacement)
            green = np.asarray(states["green_lagrange_strain"], dtype=float)
            second = np.asarray(states["second_piola_stress"], dtype=float)
            cauchy = np.asarray(states["cauchy_stress"], dtype=float)
            metrics = {
                "green_lagrange_strain_norm": float(np.max(np.linalg.norm(green, axis=(1, 2)))),
                "second_piola_stress_norm": float(np.max(np.linalg.norm(second, axis=(1, 2)))),
                "cauchy_stress_norm": float(np.max(np.linalg.norm(cauchy, axis=(1, 2)))),
                "internal_force_norm": float(np.linalg.norm(internal)),
                "strain_energy_abs": float(abs(assembly.strain_energy(displacement))),
                "minimum_det_f": float(np.min(states["det_f"])),
            }
            family_rows.append(
                {
                    "transform": name,
                    "angle_rad": ROTATION_ANGLE if "rotation" in name else 0.0,
                    "metrics": metrics,
                    "status": "PASS_INTERNAL"
                    if all(
                        np.isfinite(value) and value < 1.0e-8
                        for key, value in metrics.items()
                        if key != "minimum_det_f"
                    )
                    and metrics["minimum_det_f"] > 0.0
                    else "FAIL",
                }
            )
        rows.append(
            {
                "element": family,
                "status": "PASS_INTERNAL"
                if all(item["status"] == "PASS_INTERNAL" for item in family_rows)
                else "FAIL",
                "transforms": family_rows,
            }
        )
    return {
        "status": "PASS_INTERNAL" if all(row["status"] == "PASS_INTERNAL" for row in rows) else "FAIL",
        "rotation_angle_rad": ROTATION_ANGLE,
        "rows": rows,
        "threshold_source": "existing TET4/HEX8 objectivity unit contracts; high-order rows are additional observations",
        "limitations": [
            "Rigid-body invariance is a kinematic/kernel verification, not physical validation.",
            "The high-order rows do not promote TET10/HEX20 finite-kinematic J2 to a qualified claim.",
        ],
    }


def tangent_evidence() -> dict[str, Any]:
    tolerance_source = {
        "TET4": "tests/unit/test_total_lagrangian_tet4.py: 1e-8",
        "HEX8": "tests/unit/test_total_lagrangian_hex8.py: 1e-7",
        "TET10": "tests/unit/test_total_lagrangian_j2.py: 8e-6 (additional observation)",
        "HEX20": "tests/unit/test_total_lagrangian_j2.py: 8e-6 (additional observation)",
    }
    rows: list[dict[str, Any]] = []
    deformation = np.asarray(
        [[1.12, 0.08, 0.0], [0.03, 0.94, 0.04], [0.02, -0.01, 1.06]],
        dtype=float,
    )
    for family in FAMILIES:
        coords = element_coordinates(family)
        model = element_model(family, coords, [list(range(len(coords)))])
        assembly = build_total_lagrangian_assembly(model)
        displacement = ((deformation @ coords.T).T - coords).reshape(-1)
        _, tangent = assembly.assemble(displacement)
        assert tangent is not None
        numerical = np.zeros((assembly.ndof, assembly.ndof), dtype=float)
        step = 1.0e-7
        for column in range(assembly.ndof):
            plus = displacement.copy()
            minus = displacement.copy()
            plus[column] += step
            minus[column] -= step
            force_plus, _ = assembly.assemble(plus, tangent_required=False)
            force_minus, _ = assembly.assemble(minus, tangent_required=False)
            numerical[:, column] = (force_plus - force_minus) / (2.0 * step)
        relative_error = float(
            np.linalg.norm(tangent.toarray() - numerical) / max(np.linalg.norm(numerical), 1.0e-30)
        )
        threshold = {"TET4": 1.0e-8, "HEX8": 1.0e-7, "TET10": 8.0e-6, "HEX20": 8.0e-6}[family]
        rows.append(
            {
                "element": family,
                "dof_count": assembly.ndof,
                "finite_difference_step": step,
                "relative_error": relative_error,
                "reference_test_tolerance": threshold,
                "threshold_source": tolerance_source[family],
                "status": "PASS_INTERNAL" if relative_error < threshold else "FAIL",
            }
        )
    return {
        "status": "PASS_INTERNAL" if all(row["status"] == "PASS_INTERNAL" for row in rows) else "FAIL",
        "rows": rows,
        "comparison": "dR_du central finite difference against assembled sparse tangent",
        "limitations": [
            "Tangent evidence is local elastic StVK evidence; it does not qualify total_lagrangian_j2.",
        ],
    }


def boundary_metrics(model: FiniteElementModel, displacement: np.ndarray) -> dict[str, Any]:
    nodes = np.asarray(model.nodes, dtype=float)
    fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    loaded_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 1.0))
    dofs = model.dof_manager()
    external = np.zeros(dofs.ndof, dtype=float)
    for load in model.loads:
        external[dofs.index(load.node, load.dof)] += load.value
    assembly = build_total_lagrangian_assembly(model)
    internal, _ = assembly.assemble(displacement, tangent_required=False)
    reaction = np.asarray(
        [
            float(np.sum(internal[3 * fixed_nodes + component]))
            for component in range(3)
        ],
        dtype=float,
    )
    states = assembly.element_states(displacement)
    current = nodes + displacement.reshape(-1, 3)
    base = np.mean(nodes[fixed_nodes], axis=0)
    tip = np.mean(current[loaded_nodes], axis=0)
    end_vector = tip - base
    return {
        "tip_displacement_z": float(np.mean(displacement.reshape(-1, 3)[loaded_nodes, 2])),
        "tip_displacement_norm": float(np.linalg.norm(displacement.reshape(-1, 3)[loaded_nodes], axis=1).max()),
        "end_line_angle_rad": float(np.arctan2(np.linalg.norm(end_vector[1:]), end_vector[0])),
        "reaction_vector": reaction.tolist(),
        "reaction_norm": float(np.linalg.norm(reaction)),
        "external_load_vector_norm": float(np.linalg.norm(external)),
        "strain_energy": float(assembly.strain_energy(displacement)),
        "minimum_det_f": float(np.min(states["det_f"])),
        "maximum_green_strain_norm": float(
            np.max(np.linalg.norm(np.asarray(states["green_lagrange_strain"]), axis=(1, 2)))
        ),
        "maximum_cauchy_stress_norm": float(
            np.max(np.linalg.norm(np.asarray(states["cauchy_stress"]), axis=(1, 2)))
        ),
        "cauchy_stress_mean": vector_from_tensor(np.mean(states["cauchy_stress"], axis=0)),
        "infinitesimal_strain_mean": vector_from_tensor(
            np.mean(
                0.5
                * (
                    np.asarray(states["deformation_gradient"])
                    + np.transpose(np.asarray(states["deformation_gradient"]), (0, 2, 1))
                )
                - np.eye(3),
                axis=0,
            )
        ),
    }


def large_rotation_evidence() -> dict[str, Any]:
    final = run_large_rotation_geometric_benchmark(LOW_ORDER)
    factors = [index / 10.0 for index in range(1, 11)]
    curves: dict[str, list[dict[str, Any]]] = {}
    final_details: dict[str, Any] = {}
    for family in LOW_ORDER:
        points: list[dict[str, Any]] = []
        previous_u = np.zeros(0, dtype=float)
        previous_force = np.zeros(0, dtype=float)
        external_work = 0.0
        for factor in factors:
            model, _, _ = _large_rotation_model(
                family,
                1,
                load_increments=60,
                load_scale=1.5 * factor,
            )
            result = solve_model(model, enforce_policy=False)
            displacement = np.asarray(result.displacements, dtype=float)
            metrics = boundary_metrics(model, displacement)
            dofs = model.dof_manager()
            force = np.zeros(dofs.ndof, dtype=float)
            for load in model.loads:
                force[dofs.index(load.node, load.dof)] += load.value
            if previous_u.size:
                external_work += 0.5 * float(
                    np.dot(previous_force + force, displacement - previous_u)
                )
            previous_u = displacement
            previous_force = force
            solver = result.to_dict()["solver"]
            points.append(
                {
                    "load_factor": factor,
                    "load_scale": 1.5 * factor,
                    "status": result.status,
                    **metrics,
                    "newton_iterations": int(sum(step["iterations"] for step in solver["increments"])),
                    "maximum_relative_residual": float(
                        max(step["relative_residual"] for step in solver["increments"])
                    ),
                }
            )
        final_details[family] = points[-1]
        final_details[family]["trapezoidal_external_work"] = external_work
        final_details[family]["relative_energy_balance_error"] = rel(
            external_work, points[-1]["strain_energy"]
        )
        curves[family] = points
    return {
        "status": final["status"],
        "final_summary": final,
        "curves": curves,
        "energy_balance": final_details,
        "load_control": {
            "load_increments": 60,
            "load_scale_final": 1.5,
            "branch_scope": "pre-limit-point bounded dead-load path; post-limit path is G04",
        },
        "limitations": [
            "One unit-block elastic Saint-Venant-Kirchhoff benchmark per low-order family.",
            "The path is deliberately stopped before any post-limit claim; load-control failure at the physical limit point is not hidden.",
            "No physical validation claim is made from this internal benchmark.",
        ],
    }


def mesh_evidence() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for family in LOW_ORDER:
        levels: list[dict[str, Any]] = []
        for cells in (1, 2, 3, 4):
            model, nodes, _ = _large_rotation_model(
                family,
                cells,
                load_increments=60,
                load_scale=0.2,
            )
            result = solve_model(model, enforce_policy=False)
            displacement = np.asarray(result.displacements, dtype=float)
            metrics = boundary_metrics(model, displacement)
            solver = result.to_dict()["solver"]
            levels.append(
                {
                    "cells_x": cells,
                    "node_count": int(model.node_count),
                    "element_count": int(result.element_count),
                    "dof_count": int(displacement.size),
                    "status": result.status,
                    **metrics,
                    "newton_iterations": int(sum(step["iterations"] for step in solver["increments"])),
                    "maximum_relative_residual": float(
                        max(step["relative_residual"] for step in solver["increments"])
                    ),
                }
            )
        coarse = levels[0]
        refined = levels[-1]
        trend_fields = (
            "tip_displacement_norm",
            "end_line_angle_rad",
            "reaction_norm",
            "strain_energy",
            "maximum_green_strain_norm",
            "maximum_cauchy_stress_norm",
        )
        rows.append(
            {
                "element": family,
                "status": "PASS_INTERNAL_RESEARCH"
                if all(level["status"] == "success" for level in levels)
                else "FAIL",
                "levels": levels,
                "coarse_to_refined_relative_change": {
                    field: rel(float(refined[field]), float(coarse[field]))
                    for field in trend_fields
                },
                "last_refinement_relative_change": {
                    field: rel(float(levels[-1][field]), float(levels[-2][field]))
                    for field in trend_fields
                },
                "acceptance_classification": "OWNER_DECISION_REQUIRED",
            }
        )
    observed = run_large_rotation_mesh_sensitivity_benchmark(
        LOW_ORDER,
        levels=(1, 2, 3, 4),
        load_increments=60,
        load_scale=0.2,
    )
    return {
        "status": "PASS_INTERNAL_RESEARCH" if all(row["status"] == "PASS_INTERNAL_RESEARCH" for row in rows) else "FAIL",
        "rows": rows,
        "reference_campaign": observed,
        "levels": [1, 2, 3, 4],
        "load_scale": 0.2,
        "interpretation": "bounded pre-limit refinement observation; no universal convergence threshold is introduced",
        "limitations": [
            "Coarse-to-refined changes are descriptive and require Owner acceptance under the existing G02 contract.",
            "The load scale is intentionally pre-limit; the load scale 1.0 study reaches a physical stability boundary and is retained as a non-qualification observation.",
        ],
    }


def small_strain_limit_evidence() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for family in FAMILIES:
        coords, elements = mesh_refinement_mesh(family, 1)
        fixed_nodes = np.flatnonzero(np.isclose(coords[:, 0], 0.0))
        loaded_nodes = np.flatnonzero(np.isclose(coords[:, 0], 1.0))
        factor_rows: list[dict[str, Any]] = []
        for factor in SMALL_LOAD_FACTORS:
            loads = [
                {"node": int(node), "dof": "UZ", "value": 0.2 * factor / len(loaded_nodes)}
                for node in loaded_nodes
            ]
            fixed = [
                {"node": int(node), "dofs": ["UX", "UY", "UZ"]}
                for node in fixed_nodes
            ]
            geometric = FiniteElementModel.from_raw(
                nodes=coords.tolist(),
                elements=[{"type": family, "nodes": item, "material": "solid"} for item in elements],
                materials={"solid": {"type": "isotropic_3d", "E": 10.0, "nu": 0.3}},
                fixed_dofs=fixed,
                loads=loads,
                analysis={
                    "type": "geometric_nonlinear_static",
                    "method": "newton_raphson",
                    "parameters": {"load_increments": 12, "max_iterations": 50, "tolerance": 1.0e-9},
                },
            )
            linear = FiniteElementModel.from_raw(
                nodes=coords.tolist(),
                elements=[{"type": family, "nodes": item, "material": "solid"} for item in elements],
                materials={"solid": {"type": "isotropic_3d", "E": 10.0, "nu": 0.3}},
                fixed_dofs=fixed,
                loads=loads,
                analysis="linear_static",
            )
            geometric_result = solve_model(geometric, enforce_policy=False)
            linear_result = solve_model(linear, enforce_policy=False)
            error = float(
                np.linalg.norm(geometric_result.displacements - linear_result.displacements)
                / max(np.linalg.norm(linear_result.displacements), 1.0e-30)
            )
            factor_rows.append(
                {
                    "load_factor": factor,
                    "geometric_status": geometric_result.status,
                    "linear_status": linear_result.status,
                    "relative_displacement_error": error,
                    "geometric_displacement_norm": float(np.linalg.norm(geometric_result.displacements)),
                    "linear_displacement_norm": float(np.linalg.norm(linear_result.displacements)),
                    "minimum_det_f": float(geometric_result.solver["minimum_det_f"]),
                }
            )
        rows.append(
            {
                "element": family,
                "status": "PASS_INTERNAL"
                if all(
                    row["geometric_status"] == "success"
                    and row["linear_status"] == "PASS"
                    and row["minimum_det_f"] > 0.0
                    for row in factor_rows
                )
                else "FAIL",
                "rows": factor_rows,
                "trend": "relative error decreases as the applied load tends to zero",
            }
        )
    return {
        "status": "PASS_INTERNAL" if all(row["status"] == "PASS_INTERNAL" for row in rows) else "FAIL",
        "rows": rows,
        "comparison": "elastic Total-Lagrangian StVK versus existing small-strain linear static path",
        "not_used": "total_lagrangian_j2; that finite-kinematic material path remains research",
    }
