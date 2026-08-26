# ruff: noqa: F401, F403, F405

"""Implementation group for the nonlinear robustness campaign: robustness_geometric."""

from __future__ import annotations

from solveur.verification.robustness_support import *  # noqa: F401,F403
from solveur.verification.robustness_foundations import (
    _global_model,
    _newton_rate_metrics,
    element_coordinates,
    j2_material,
)
from solveur.verification.robustness_mesh import (
    _multi_element_model,
    _refinement_model,
    mesh_refinement_mesh,
)



def run_finite_kinematic_j2_benchmark(
    element_types: tuple[str, ...] = ELEMENT_TYPES,
) -> dict[str, Any]:
    """Run the bounded Green-Lagrange/J2 candidate through common Newton.

    This is an internal research campaign. It records objectivity and solver
    diagnostics but deliberately does not promote the finite-kinematic model
    to a validated or production capability.
    """
    rows: list[dict[str, Any]] = []
    for family in element_types:
        if family not in ELEMENT_TYPES:
            raise ValueError("Finite-kinematic J2 benchmark supports TET4, TET10, HEX8 and HEX20.")
        model = _refinement_model(family, 1) if family in {"TET4", "TET10", "HEX8"} else _single_high_order_model(family)
        model.analysis = replace(
            model.analysis,
            parameters={
                **model.analysis.parameters,
                "kinematics": "total_lagrangian_j2",
                "load_steps": 3,
            },
        )
        result = solve_model(model, enforce_policy=False)
        data = result.to_dict()
        steps = data["solver"]["steps"]
        point_rows = [
            point
            for element in result.element_results
            for point in element.get("integration_points", [])
        ]
        rotation_residual = _finite_kinematic_rotation_residual(family)
        tangent_fd_error = _finite_kinematic_tangent_error(family)
        rows.append(
            {
                "element": family,
                "status": "PASS" if result.status == "PASS" and rotation_residual < 1.0e-9 and tangent_fd_error < 1.0e-6 else "FAIL",
                "kinematics": "green_lagrange_second_piola",
                "element_count": int(result.element_count),
                "dof_count": int(result.displacements.size),
                "newton_iterations": int(sum(step["iterations"] for step in steps)),
                "maximum_relative_residual": float(max(step["relative_residual"] for step in steps)),
                "final_peeq": float(steps[-1]["equivalent_plastic_strain_max"]),
                "plastic_dissipation": float(steps[-1]["plastic_dissipation_max"]),
                "minimum_det_f": float(min(float(point["det_f"]) for point in point_rows)),
                "rigid_rotation_internal_force_norm": rotation_residual,
                "tangent_fd_relative_error": tangent_fd_error,
            }
        )
    return {
        "status": "PASS_INTERNAL_RESEARCH" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "rows": rows,
        "limitations": [
            "Green-Lagrange J2 is a bounded research model, not general finite-strain plasticity.",
            "HEX20 uses a single-element high-order smoke model; no multi-element HEX20 finite-kinematic claim is made.",
            "The TET10 result uses the existing refined multi-element smoke mesh, but is not an external or mesh-convergence qualification.",
            "No external correlation or physical validation claim is made.",
        ],
    }


def run_finite_kinematic_limit_recovery_benchmark(
    element_types: tuple[str, ...] = ELEMENT_TYPES,
) -> dict[str, Any]:
    """Check recovery of the small-strain path as the load tends to zero."""

    rows: list[dict[str, Any]] = []
    load_factor = 1.0e-4
    for family in element_types:
        if family not in ELEMENT_TYPES:
            raise ValueError("Finite-kinematic limit recovery supports TET4, TET10, HEX8 and HEX20.")
        builder = _refinement_model if family in {"TET4", "TET10", "HEX8"} else _single_high_order_model
        small_model = builder(family, 1) if builder is _refinement_model else builder(family)
        small_model.analysis = replace(
            small_model.analysis,
            parameters={
                **small_model.analysis.parameters,
                "load_path": [load_factor],
                "max_iterations": 40,
                "tolerance": 1.0e-9,
            },
        )
        small_result = solve_model(small_model, enforce_policy=False)
        finite_model = deepcopy(small_model)
        finite_model.analysis = replace(
            finite_model.analysis,
            parameters={
                **finite_model.analysis.parameters,
                "kinematics": "total_lagrangian_j2",
            },
        )
        finite_result = solve_model(finite_model, enforce_policy=False)
        displacement_error = float(
            np.linalg.norm(finite_result.displacements - small_result.displacements)
            / max(np.linalg.norm(small_result.displacements), 1.0e-15)
        )
        small_steps = small_result.to_dict()["solver"]["steps"]
        finite_steps = finite_result.to_dict()["solver"]["steps"]
        rows.append(
            {
                "element": family,
                "status": (
                    "PASS"
                    if small_result.status == "PASS"
                    and finite_result.status == "PASS"
                    and displacement_error < 1.0e-8
                    and float(finite_steps[-1]["equivalent_plastic_strain_max"]) == 0.0
                    else "FAIL"
                ),
                "load_factor": load_factor,
                "small_strain_status": small_result.status,
                "finite_kinematic_status": finite_result.status,
                "small_strain_displacement_norm": float(np.linalg.norm(small_result.displacements)),
                "finite_kinematic_displacement_norm": float(np.linalg.norm(finite_result.displacements)),
                "relative_displacement_error": displacement_error,
                "small_strain_relative_residual": float(small_steps[-1]["relative_residual"]),
                "finite_kinematic_relative_residual": float(finite_steps[-1]["relative_residual"]),
                "finite_kinematic_peeq": float(finite_steps[-1]["equivalent_plastic_strain_max"]),
            }
        )
    return {
        "status": "PASS_INTERNAL_RESEARCH"
        if rows and all(row["status"] == "PASS" for row in rows)
        else "FAIL",
        "rows": rows,
        "load_factor": load_factor,
        "comparison": "small_strain_vs_total_lagrangian_j2",
        "owner_acceptance_band_required": True,
        "limitations": [
            "Single small-load recovery point per family; no finite-strain material validation claim.",
            "This is a regime-consistency check and does not close the geometric nonlinearity gate.",
        ],
    }


def _single_high_order_model(element_type: str) -> FiniteElementModel:
    """Build one constrained high-order solid for finite-kinematic smoke V&V."""

    nodes = element_coordinates(element_type)
    fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    loaded_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 1.0))
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": element_type, "nodes": list(range(len(nodes))), "material": "j2"}],
        materials={
            "j2": {
                "type": "von_mises_elastoplastic_3d",
                "E": 1000.0,
                "nu": 0.3,
                "yield_stress": 0.02,
                "hardening_modulus": 10.0,
            }
        },
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes],
        loads=[{"node": int(node), "dof": "UX", "value": 1.0 / len(loaded_nodes)} for node in loaded_nodes],
        analysis={
            "type": "nonlinear_static",
            "method": "newton_raphson",
            "load_steps": 3,
            "max_iterations": 40,
            "tolerance": 1.0e-7,
        },
    )


def run_high_order_geometric_benchmark(
    element_types: tuple[str, ...] = ("TET10", "HEX20"),
) -> dict[str, Any]:
    """Exercise the common geometric assembly on connected high-order meshes."""

    rows: list[dict[str, Any]] = []
    for family in element_types:
        if family not in {"TET10", "HEX20"}:
            raise ValueError("High-order geometric benchmark supports TET10 and HEX20.")
        nodes, elements = mesh_refinement_mesh(family, 1)
        fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
        loaded_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 1.0))
        model = FiniteElementModel.from_raw(
            nodes=nodes.tolist(),
            elements=[{"type": family, "nodes": item, "material": "solid"} for item in elements],
            materials={"solid": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.3}},
            fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes],
            loads=[{"node": int(node), "dof": "UX", "value": 1.0e-4 / len(loaded_nodes)} for node in loaded_nodes],
            analysis={
                "type": "geometric_nonlinear_static",
                "method": "newton_raphson",
                "parameters": {"load_increments": 6, "max_iterations": 30, "tolerance": 1.0e-8},
            },
        )
        result = solve_model(model, enforce_policy=False)
        solver = result.to_dict()["solver"]
        rows.append(
            {
                "element": family,
                "status": "PASS" if result.status == "success" and solver["minimum_det_f"] > 0.0 else "FAIL",
                "element_count": int(result.element_count),
                "dof_count": int(result.displacements.size),
                "newton_iterations": int(sum(step["iterations"] for step in solver["increments"])),
                "maximum_relative_residual": float(max(step["relative_residual"] for step in solver["increments"])),
                "minimum_det_f": float(solver["minimum_det_f"]),
                "strain_energy": float(solver["strain_energy"]),
                "scope": solver["scope"],
            }
        )
    return {
        "status": "PASS_INTERNAL_RESEARCH" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "rows": rows,
        "owner_acceptance_band_required": True,
        "limitations": [
            "Connected one-block high-order smoke only; no large-rotation or mesh-convergence qualification.",
            "The path is elastic Saint-Venant-Kirchhoff geometry, not finite-strain J2 plasticity.",
            "No external correlation or physical validation claim is made.",
        ],
    }


def _large_rotation_model(element_type: str, cells: int, *, load_increments: int = 60, load_scale: float = 1.5) -> tuple[FiniteElementModel, np.ndarray, list[list[int]]]:
    """Build one reproducible large-deflection elastic solid model."""

    nodes, elements = mesh_refinement_mesh(element_type, cells)
    fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    loaded_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 1.0))
    model = FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": element_type, "nodes": item, "material": "solid"} for item in elements],
        materials={"solid": {"type": "isotropic_3d", "E": 10.0, "nu": 0.3}},
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes],
        loads=[
            {"node": int(node), "dof": "UZ", "value": load_scale / len(loaded_nodes)}
            for node in loaded_nodes
        ],
        analysis={
            "type": "geometric_nonlinear_static",
            "method": "newton_raphson",
            "parameters": {"load_increments": load_increments, "max_iterations": 100, "tolerance": 1.0e-8},
        },
    )
    return model, nodes, elements


def run_large_rotation_geometric_benchmark(
    element_types: tuple[str, ...] = ("TET4", "HEX8"),
) -> dict[str, Any]:
    """Exercise a bounded large-deflection geometric path for low-order solids.

    A transverse dead load is applied to the right face of a unit block. The
    measured end-line angle is deliberately large enough to exercise the
    geometric tangent while the positive Jacobian and residual checks remain
    explicit. This is an internal elastic research observation, not a
    post-buckling or physical-validation result.
    """

    rows: list[dict[str, Any]] = []
    for family in element_types:
        if family not in {"TET4", "HEX8"}:
            raise ValueError("Large-rotation benchmark supports TET4 and HEX8.")
        model, nodes, elements = _large_rotation_model(family, 1)
        fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
        loaded_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 1.0))
        result = solve_model(model, enforce_policy=False)
        solver = result.to_dict()["solver"]
        displacement = np.asarray(result.displacements, dtype=float).reshape(-1, 3)
        deformed_nodes = nodes + displacement
        base = np.mean(nodes[fixed_nodes], axis=0)
        tip = np.mean(deformed_nodes[loaded_nodes], axis=0)
        end_vector = tip - base
        end_angle = float(np.arctan2(np.linalg.norm(end_vector[1:]), end_vector[0]))
        increments = solver["increments"]
        rows.append(
            {
                "element": family,
                "status": "PASS"
                if result.status == "success"
                and solver["minimum_det_f"] > 0.0
                and end_angle > 0.5
                and all(np.isfinite(step["relative_residual"]) for step in increments)
                else "FAIL",
                "element_count": int(result.element_count),
                "dof_count": int(result.displacements.size),
                "load_increments": int(solver["load_increments"]),
                "maximum_relative_residual": float(
                    max(step["relative_residual"] for step in increments)
                ),
                "minimum_det_f": float(solver["minimum_det_f"]),
                "maximum_displacement_norm": float(
                    np.linalg.norm(displacement, axis=1).max()
                ),
                "end_line_angle_rad": end_angle,
                "end_line_angle_deg": float(np.degrees(end_angle)),
                "strain_energy": float(solver["strain_energy"]),
            }
        )
    return {
        "status": "PASS_INTERNAL_RESEARCH" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "rows": rows,
        "owner_acceptance_band_required": True,
        "limitations": [
            "One unit-block low-order TET4/HEX8 elastic Saint-Venant-Kirchhoff path.",
            "This is a large-deflection smoke benchmark, not a large-rotation plasticity, post-buckling or external-correlation qualification.",
        ],
    }


def run_large_rotation_mesh_sensitivity_benchmark(
    element_types: tuple[str, ...] = ("TET4", "HEX8"),
    levels: tuple[int, ...] = (1, 2),
    *,
    load_increments: int = 60,
    load_scale: float = 1.0,
) -> dict[str, Any]:
    """Record bounded mesh sensitivity for the common geometric driver."""

    rows: list[dict[str, Any]] = []
    for family in element_types:
        if family not in ELEMENT_TYPES:
            raise ValueError("Large-rotation mesh sensitivity supports TET4, TET10, HEX8 and HEX20.")
        level_rows: list[dict[str, Any]] = []
        for cells in levels:
            model, nodes, _ = _large_rotation_model(
                family,
                cells,
                load_increments=load_increments,
                load_scale=load_scale,
            )
            result = solve_model(model, enforce_policy=False)
            solver = result.to_dict()["solver"]
            displacement = np.asarray(result.displacements, dtype=float).reshape(-1, 3)
            fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
            loaded_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 1.0))
            base = np.mean(nodes[fixed_nodes], axis=0)
            tip = np.mean((nodes + displacement)[loaded_nodes], axis=0)
            end_vector = tip - base
            end_angle = float(np.arctan2(np.linalg.norm(end_vector[1:]), end_vector[0]))
            increments = solver["increments"]
            level_rows.append(
                {
                    "cells": int(cells),
                    "element": family,
                    "status": "PASS" if result.status == "success" else "FAIL",
                    "element_count": int(result.element_count),
                    "dof_count": int(result.displacements.size),
                    "end_line_angle_rad": end_angle,
                    "end_line_angle_deg": float(np.degrees(end_angle)),
                    "maximum_displacement_norm": float(np.linalg.norm(displacement, axis=1).max()),
                    "minimum_det_f": float(solver["minimum_det_f"]),
                    "strain_energy": float(solver["strain_energy"]),
                    "maximum_relative_residual": float(max(step["relative_residual"] for step in increments)),
                    "newton_iterations": int(sum(step["iterations"] for step in increments)),
                }
            )
        coarse = level_rows[0]
        refined = level_rows[-1]
        rows.append(
            {
                "element": family,
                "status": "PASS_INTERNAL_RESEARCH" if all(row["status"] == "PASS" for row in level_rows) else "FAIL",
                "levels": level_rows,
                "coarse_to_refined": {
                    key: abs(coarse[key] - refined[key]) / max(abs(refined[key]), 1.0e-15)
                    for key in ("end_line_angle_rad", "maximum_displacement_norm", "strain_energy")
                },
                "owner_acceptance_band_required": True,
            }
        )
    return {
        "status": "PASS_INTERNAL_RESEARCH" if rows and all(row["status"] == "PASS_INTERNAL_RESEARCH" for row in rows) else "FAIL",
        "rows": rows,
        "levels": list(levels),
        "load_scale": float(load_scale),
        "load_increments": int(load_increments),
        "limitations": [
            "Internal elastic mesh sensitivity only; no plasticity or external correlation.",
            "The recorded coarse-to-refined changes are observations and do not define an acceptance band.",
            "The low-order load scale 1.5 smoke is not stable on refined HEX8.",
            "The TET10/HEX20 extension is deliberately limited to the recorded low-load study and remains research evidence.",
        ],
    }


def _finite_kinematic_rotation_residual(element_type: str) -> float:
    """Return the internal-force norm for a rigid rotation of one element."""
    material = j2_material()
    coords = element_coordinates(element_type)
    element_class = {
        "TET4": TotalLagrangianJ2Tet4Element,
        "TET10": TotalLagrangianJ2Tet10Element,
        "HEX8": TotalLagrangianJ2Hex8Element,
        "HEX20": TotalLagrangianJ2Hex20Element,
    }[element_type]
    element = element_class(material)
    angle = 0.7
    rotation = np.asarray(
        [[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]]
    )
    displacement = ((rotation @ coords.T).T - coords).ravel()
    states = [material.initial_state() for _ in range(element.integration_point_count)]
    internal, _, _ = element.internal_force_tangent_state(coords, displacement, states)
    return float(np.linalg.norm(internal))


def _finite_kinematic_tangent_error(element_type: str) -> float:
    """Compare the finite-kinematic element tangent with force differences."""

    material = j2_material()
    coords = element_coordinates(element_type)
    element_class = {
        "TET4": TotalLagrangianJ2Tet4Element,
        "TET10": TotalLagrangianJ2Tet10Element,
        "HEX8": TotalLagrangianJ2Hex8Element,
        "HEX20": TotalLagrangianJ2Hex20Element,
    }[element_type]
    element = element_class(material)
    deformation = np.asarray(
        [[1.04, 0.02, 0.0], [0.01, 0.98, 0.01], [0.0, 0.01, 1.03]],
        dtype=float,
    )
    displacement = ((deformation @ coords.T).T - coords).ravel()
    states = [material.initial_state() for _ in range(element.integration_point_count)]
    _, tangent, _ = element.internal_force_tangent_state(coords, displacement, states)
    numerical = np.zeros_like(tangent)
    step = 1.0e-7
    for column in range(displacement.size):
        perturbation = np.zeros_like(displacement)
        perturbation[column] = step
        plus = element.internal_force_tangent_state(coords, displacement + perturbation, states)[0]
        minus = element.internal_force_tangent_state(coords, displacement - perturbation, states)[0]
        numerical[:, column] = (plus - minus) / (2.0 * step)
    return float(np.linalg.norm(tangent - numerical) / max(np.linalg.norm(numerical), 1.0e-15))


def run_multi_element_load_step_sensitivity(
    element_types: tuple[str, ...] = ELEMENT_TYPES,
) -> dict[str, Any]:
    """Compare coarse, reference and refined load histories on connected meshes."""
    paths = {
        "coarse": [0.5, 1.0],
        "reference": [0.25, 0.5, 0.75, 1.0],
        "refined": [0.125 * index for index in range(1, 9)],
    }
    rows: list[dict[str, Any]] = []
    for family in element_types:
        histories: dict[str, dict[str, float]] = {}
        for name, path in paths.items():
            model = _multi_element_model(family)
            model.analysis = replace(
                model.analysis,
                parameters={**model.analysis.parameters, "load_path": path},
            )
            result = solve_model(model, enforce_policy=False)
            data = result.to_dict()
            steps = data["solver"]["steps"]
            final = steps[-1]
            histories[name] = {
                "displacement_norm": float(np.linalg.norm(result.displacements)),
                "peeq": float(final["equivalent_plastic_strain_max"]),
                "plastic_dissipation": float(final["plastic_dissipation_max"]),
                "maximum_relative_residual": float(max(step["relative_residual"] for step in steps)),
                "iterations": float(sum(step["iterations"] for step in steps)),
            }
        reference = histories["reference"]
        refined = histories["refined"]
        rows.append(
            {
                "element": family,
                "status": "PASS" if all(np.isfinite(list(item.values())).all() for item in histories.values()) else "FAIL",
                "histories": histories,
                "reference_to_refined": {
                    key: abs(reference[key] - refined[key]) / max(abs(refined[key]), 1.0e-15)
                    for key in ("displacement_norm", "peeq", "plastic_dissipation")
                },
                "owner_acceptance_band_required": True,
            }
        )
    return {
        "status": "PASS_INTERNAL_SENSITIVITY" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "paths": paths,
        "rows": rows,
        "limitations": [
            "The function records sensitivity; it does not invent a release tolerance.",
            "Meshes remain the connected two-element internal benchmark.",
        ],
    }


__all__ = [name for name in globals() if not name.startswith("__")]
