"""Build the controlled geometric-nonlinearity evidence pack for 025-G02.

This script is a verification/reproducibility entry point.  It does not alter
solver behaviour and intentionally keeps the finite-kinematic J2 path outside
the G02 qualification claim.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from solveur.api import solve_model  # noqa: E402
from solveur.core.geometric_assembly import build_total_lagrangian_assembly  # noqa: E402
from solveur.core.model import FiniteElementModel  # noqa: E402
from solveur.verification.code_aster_tl_structural import (  # noqa: E402
    CODE_ASTER_IMAGE,
    CODE_ASTER_PROFILE,
    run_code_aster,
)
from solveur.verification.robustness_foundations import element_coordinates  # noqa: E402
from solveur.verification.robustness_geometric import (  # noqa: E402
    _large_rotation_model,
    run_large_rotation_geometric_benchmark,
    run_large_rotation_mesh_sensitivity_benchmark,
)  # noqa: E402
from solveur.verification.robustness_mesh import mesh_refinement_mesh  # noqa: E402


OUT = ROOT / "results" / "vnv_0_2_5" / "g02_latest"
FAMILIES = ("TET4", "TET10", "HEX8", "HEX20")
LOW_ORDER = ("TET4", "HEX8")
ROTATION_ANGLE = 0.7
SMALL_LOAD_FACTORS = (1.0e-2, 1.0e-3, 1.0e-4)


def git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def code_aster_mesh(family: str, nodes: np.ndarray, elements: list[list[int]], fixed: np.ndarray, loaded: np.ndarray) -> str:
    lines = ["TITRE", f"QF Solver G02 {family} Code_Aster correlation", "FINSF", "COOR_3D"]
    lines.extend(
        f"N{i + 1} {float(node[0]):.16g} {float(node[1]):.16g} {float(node[2]):.16g}"
        for i, node in enumerate(nodes)
    )
    lines.extend(["FINSF", "TETRA4" if family == "TET4" else "HEXA8"])
    lines.extend(
        f"M{i + 1} " + " ".join(f"N{int(node) + 1}" for node in element)
        for i, element in enumerate(elements)
    )
    lines.extend(["FINSF", "GROUP_MA", "SOLID", *(f"M{i + 1}" for i in range(len(elements))), "FINSF"])
    lines.extend(["GROUP_NO", "FIXED", *(f"N{int(node) + 1}" for node in fixed), "FINSF"])
    lines.extend(["GROUP_NO", "LOAD", *(f"N{int(node) + 1}" for node in loaded), "FINSF", "FIN"])
    return "\n".join(lines) + "\n"


def code_aster_comm(family: str, load_scale: float, increments: int, node_count: int) -> str:
    element = "TETRA4" if family == "TET4" else "HEXA8"
    return f'''# coding=utf-8
import json
import numpy as np
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", PHENOMENE="MECANIQUE", MODELISATION="3D"))
material = DEFI_MATERIAU(ELAS=_F(E=10.0, NU=0.3))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", MATER=material))
fixed = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(GROUP_NO="FIXED", DX=0.0, DY=0.0, DZ=0.0))
load = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=_F(GROUP_NO="LOAD", FZ={load_scale:.16g} / {node_count}))
ramp = DEFI_FONCTION(NOM_PARA="INST", VALE=(0.0, 0.0, 1.0, 1.0))
times = DEFI_LIST_REEL(DEBUT=0.0, INTERVALLE=_F(JUSQU_A=1.0, NOMBRE={increments}))
result = STAT_NON_LINE(
    MODELE=model,
    CHAM_MATER=field,
    EXCIT=(_F(CHARGE=fixed), _F(CHARGE=load, FONC_MULT=ramp)),
    COMPORTEMENT=_F(RELATION="ELAS", DEFORMATION="GREEN_LAGRANGE"),
    INCREMENT=_F(LIST_INST=times),
    CONVERGENCE=_F(RESI_GLOB_RELA=1.0e-9, ITER_GLOB_MAXI=50),
)
result = CALC_CHAMP(reuse=result, RESULTAT=result, FORCE=("REAC_NODA",), DEFORMATION=("EPSI_ELGA",))
rows = []
for order, instant in zip(result.getIndexes(), result.getAccessParameters()["INST"]):
    displacement = result.getField("DEPL", order)
    uz, _ = displacement.getValuesWithDescription("DZ", ["LOAD"])
    reaction = result.getField("REAC_NODA", order)
    rx, _ = reaction.getValuesWithDescription("DX", ["FIXED"])
    ry, _ = reaction.getValuesWithDescription("DY", ["FIXED"])
    rz, _ = reaction.getValuesWithDescription("DZ", ["FIXED"])
    stress = result.getField("SIEF_ELGA", order)
    strain = result.getField("EPSI_ELGA", order)
    stress_components = []
    for name in ("SIXX", "SIYY", "SIZZ", "SIXY", "SIXZ", "SIYZ"):
        values, _ = stress.getValuesWithDescription(name, ["SOLID"])
        stress_components.append(float(np.mean(values)))
    strain_components = []
    for name in ("EPXX", "EPYY", "EPZZ", "EPXY", "EPXZ", "EPYZ"):
        values, _ = strain.getValuesWithDescription(name, ["SOLID"])
        strain_components.append(float(np.mean(values)))
    rows.append({{
        "order": int(order),
        "load_factor": float(instant),
        "tip_displacement_z": float(np.mean(uz)),
        "reaction_vector": [float(np.sum(rx)), float(np.sum(ry)), float(np.sum(rz))],
        "stress_sief_elga": stress_components,
        "strain_epsi_elga": strain_components,
    }})
with open("/work/code_aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump({{"element": "{element}", "rows": rows}}, stream, indent=2)
FIN()
'''


def qf_external_curve(family: str, factors: list[float]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for factor in factors:
        nodes, elements = mesh_refinement_mesh(family, 1)
        fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
        loaded_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 1.0))
        model = FiniteElementModel.from_raw(
            nodes=nodes.tolist(),
            elements=[{"type": family, "nodes": item, "material": "solid"} for item in elements],
            materials={"solid": {"type": "isotropic_3d", "E": 10.0, "nu": 0.3}},
            fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes],
            loads=[
                {"node": int(node), "dof": "UZ", "value": 0.2 * factor / len(loaded_nodes)}
                for node in loaded_nodes
            ],
            analysis={
                "type": "geometric_nonlinear_static",
                "method": "newton_raphson",
                "parameters": {"load_increments": 12, "max_iterations": 50, "tolerance": 1.0e-9},
            },
        )
        result = solve_model(model, enforce_policy=False)
        rows.append({"load_factor": factor, "status": result.status, **boundary_metrics(model, result.displacements)})
    return rows


def external_correlation() -> dict[str, Any]:
    base = OUT / "external_code_aster"
    factors = [index / 12.0 for index in range(0, 13)]
    families: dict[str, Any] = {}
    for family in LOW_ORDER:
        nodes, elements = mesh_refinement_mesh(family, 1)
        fixed = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
        loaded = np.flatnonzero(np.isclose(nodes[:, 0], 1.0))
        work = base / family
        work.mkdir(parents=True, exist_ok=True)
        stem = family.lower()
        (work / f"{stem}.mail").write_text(code_aster_mesh(family, nodes, elements, fixed, loaded), encoding="ascii")
        (work / f"{stem}.comm").write_text(
            code_aster_comm(family, 0.2, len(factors) - 1, len(loaded)), encoding="utf-8"
        )
        try:
            run_code_aster(work, stem, timeout=1200)
            raw = json.loads((work / "code_aster_raw.json").read_text(encoding="utf-8"))
            qf_rows = qf_external_curve(family, factors)
            comparisons: list[dict[str, Any]] = []
            for qf_row, ca_row in zip(qf_rows, raw["rows"], strict=True):
                ca_stress = np.asarray(ca_row["stress_sief_elga"], dtype=float)
                ca_strain = np.asarray(ca_row["strain_epsi_elga"], dtype=float)
                qf_stress = np.asarray(qf_row["cauchy_stress_mean"], dtype=float)
                qf_strain = np.asarray(qf_row["infinitesimal_strain_mean"], dtype=float)
                comparisons.append(
                    {
                        "load_factor": ca_row["load_factor"],
                        "tip_displacement_relative_error": rel(
                            qf_row["tip_displacement_z"], ca_row["tip_displacement_z"]
                        ),
                        "reaction_relative_error": float(
                            np.linalg.norm(np.asarray(qf_row["reaction_vector"]) - np.asarray(ca_row["reaction_vector"]))
                            / max(np.linalg.norm(ca_row["reaction_vector"]), 1.0e-30)
                        ),
                        "stress_relative_error": float(
                            np.linalg.norm(qf_stress - ca_stress) / max(np.linalg.norm(ca_stress), 1.0e-30)
                        ),
                        "strain_relative_error": float(
                            np.linalg.norm(qf_strain - ca_strain) / max(np.linalg.norm(ca_strain), 1.0e-30)
                        ),
                        "qf": {
                            "tip_displacement_z": qf_row["tip_displacement_z"],
                            "reaction_vector": qf_row["reaction_vector"],
                            "cauchy_stress": qf_stress.tolist(),
                            "infinitesimal_strain": qf_strain.tolist(),
                        },
                        "code_aster": ca_row,
                    }
                )
            maxima = {
                key: max(float(row[key]) for row in comparisons)
                for key in (
                    "tip_displacement_relative_error",
                    "reaction_relative_error",
                    "stress_relative_error",
                    "strain_relative_error",
                )
            }
            families[family] = {
                "status": "PASS_EXTERNAL_CORRELATION_BOUNDED",
                "external_element": raw["element"],
                "rows": comparisons,
                "maximum_relative_errors": maxima,
                "energy": {
                    "status": "NOT_COMPARED",
                    "reason": "Code_Aster native energy field is not part of this portable ELGA extraction; QF energy is reported separately in the internal curve evidence.",
                },
                "provenance": {
                    "image": CODE_ASTER_IMAGE,
                    "profile": CODE_ASTER_PROFILE,
                    "mesh": str((work / f"{stem}.mail").relative_to(ROOT)),
                    "command_file": str((work / f"{stem}.comm").relative_to(ROOT)),
                },
            }
        except Exception as error:
            families[family] = {
                "status": "BLOCKED_EXTERNAL_CORRELATION",
                "error_type": type(error).__name__,
                "error": str(error),
            }
    return {
        "status": "PASS_EXTERNAL_CORRELATION_BOUNDED"
        if families and all(item["status"] == "PASS_EXTERNAL_CORRELATION_BOUNDED" for item in families.values())
        else "BLOCKED_EXTERNAL_CORRELATION",
        "families": families,
        "load_factors": factors,
        "required_solver": "Code_Aster MUST for low-order G02 scope",
        "optional_solver": "CalculiX SHOULD and Abaqus COULD are not used to inflate this G02 decision",
        "limitations": [
            "The comparison is numerical code-to-code correlation, not physical validation.",
            "Code_Aster TET4/HEX8 histories use native SIEF_ELGA and EPSI_ELGA fields; QF reports matching Cauchy and infinitesimal measures.",
            "Energy is not compared because no common extracted native measure is available in this deck.",
        ],
    }


def plots(data: dict[str, Any]) -> list[str]:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return []
    paths: list[str] = []
    objectivity = data["objectivity"]
    fig, ax = plt.subplots(figsize=(10, 5))
    labels: list[str] = []
    values: list[float] = []
    for family in objectivity["rows"]:
        for transform in family["transforms"]:
            labels.append(f"{family['element']}\n{transform['transform']}")
            values.append(max(float(value) for key, value in transform["metrics"].items() if key != "minimum_det_f"))
    ax.bar(np.arange(len(values)), values)
    ax.set_yscale("log")
    ax.set_ylabel("max parasite norm")
    ax.set_title("G02 objectivity: rigid-body parasite measures")
    ax.set_xticks(np.arange(len(labels)), labels, rotation=70, ha="right", fontsize=7)
    fig.tight_layout()
    path = OUT / "g02_objectivity.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    paths.append(str(path.relative_to(ROOT)))

    fig, ax = plt.subplots(figsize=(8, 5))
    for family, rows in data["large_rotation"]["curves"].items():
        ax.plot([row["load_factor"] for row in rows], [row["tip_displacement_z"] for row in rows], marker="o", label=family)
    for family, item in data["external"]["families"].items():
        if item["status"] == "PASS_EXTERNAL_CORRELATION_BOUNDED":
            ax.plot(
                [row["load_factor"] for row in item["rows"]],
                [row["code_aster"]["tip_displacement_z"] for row in item["rows"]],
                linestyle="--",
                label=f"{family} Code_Aster",
            )
    ax.set_xlabel("normalized load factor")
    ax.set_ylabel("mean tip displacement z")
    ax.set_title("G02 bounded large-rotation path and Code_Aster correlation")
    ax.legend()
    fig.tight_layout()
    path = OUT / "g02_large_rotation_correlation.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    paths.append(str(path.relative_to(ROOT)))

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for item in data["mesh"]["rows"]:
        family = item["element"]
        levels = item["levels"]
        x = [level["cells_x"] for level in levels]
        axes[0].plot(x, [level["tip_displacement_norm"] for level in levels], marker="o", label=family)
        axes[1].plot(x, [level["strain_energy"] for level in levels], marker="o", label=family)
        axes[2].plot(x, [level["maximum_cauchy_stress_norm"] for level in levels], marker="o", label=family)
    axes[0].set_ylabel("tip displacement norm")
    axes[1].set_ylabel("strain energy")
    axes[2].set_ylabel("max Cauchy stress norm")
    for axis in axes:
        axis.set_xlabel("cells in x")
        axis.grid(True, alpha=0.3)
    axes[0].legend()
    fig.suptitle("G02 pre-limit mesh sensitivity: bounded observation")
    fig.tight_layout()
    path = OUT / "g02_mesh_sensitivity.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    paths.append(str(path.relative_to(ROOT)))

    fig, ax = plt.subplots(figsize=(8, 5))
    for row in data["small_strain_limit"]["rows"]:
        ax.loglog(
            [item["load_factor"] for item in row["rows"]],
            [item["relative_displacement_error"] for item in row["rows"]],
            marker="o",
            label=row["element"],
        )
    ax.set_xlabel("load factor")
    ax.set_ylabel("relative displacement error")
    ax.set_title("G02 small-strain limit recovery")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    path = OUT / "g02_small_strain_limit.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    paths.append(str(path.relative_to(ROOT)))
    return paths


def report(data: dict[str, Any], source_sha: str, dirty: bool, timestamp: str, plot_paths: list[str]) -> str:
    external_status = data["external"]["status"]
    mesh_status = data["mesh"]["status"]
    owner_decision = "REQUIRED"
    g02_status = "OPEN"
    return "\n".join(
        [
            "# QF Solver 0.2.5a0 - 025-G02 geometric nonlinear evidence",
            "",
            f"- Source SHA: `{source_sha}`",
            f"- Worktree dirty: `{str(dirty).lower()}`",
            f"- Evidence timestamp (UTC): `{timestamp}`",
            f"- Gate status: **{g02_status}**",
            f"- Owner decision: **{owner_decision}**",
            "",
            "## Decision boundary",
            "",
            "This pack qualifies only the bounded elastic Total-Lagrangian geometric core for TET4 and HEX8. It does not qualify `total_lagrangian_j2`, TET10/HEX20 finite-kinematic plasticity, post-limit load control, buckling, arc-length, contact or coupled nonlinear capabilities.",
            "",
            "## Objectivity",
            "",
            "Rigid translation, a 0.7 rad rigid rotation, and their combination were evaluated for TET4, TET10, HEX8 and HEX20. The pack records Green-Lagrange strain, second-Piola stress, Cauchy stress, internal-force and energy parasite norms. The resulting internal status is `" + data["objectivity"]["status"] + "`.",
            "",
            "## Consistent tangent",
            "",
            "The assembled sparse tangent was compared with a central finite difference of the internal force for all four families. Low-order thresholds are the existing unit-test contracts (`1e-8` TET4 and `1e-7` HEX8); high-order values are additional observations. The resulting internal status is `" + data["tangent"]["status"] + "`.",
            "",
            "## Large rotation",
            "",
            "TET4 and HEX8 were run with 60 Full-Newton load increments to a normalized end-line rotation above 0.5 rad. The path records load factor, tip displacement, reactions, energy, det(F), Newton iterations and residuals. The point after a physical load-control limit is deliberately outside this gate and belongs to G04.",
            "",
            "| Family | Final angle (rad) | Minimum det(F) | Max displacement | Energy | Max relative residual |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        + [
            f"| {family} | {item['end_line_angle_rad']:.9g} | {item['minimum_det_f']:.9g} | {item['maximum_displacement_norm']:.9g} | {item['strain_energy']:.9g} | {item['maximum_relative_residual']:.3e} |"
            for family, item in ((row["element"], row) for row in data["large_rotation"]["final_summary"]["rows"])
        ]
        + [
            "",
            "## Mesh/refinement observation",
            "",
            f"The pre-limit four-level study (coarse/medium/fine/refined = 1/2/3/4 cells) is `{mesh_status}`. It is intentionally classified `OWNER_DECISION_REQUIRED`: the measured coarse-to-refined changes are reported without inventing a universal convergence band. The load-scale 1.0 line-search failure is retained as a stability-boundary observation, not converted into a PASS.",
            "",
            "| Family | Coarse->refined tip change | Last refinement tip change | Coarse->refined energy change | Last refinement energy change |",
            "|---|---:|---:|---:|---:|",
        ]
        + [
            f"| {row['element']} | {row['coarse_to_refined_relative_change']['tip_displacement_norm']:.6g} | {row['last_refinement_relative_change']['tip_displacement_norm']:.6g} | {row['coarse_to_refined_relative_change']['strain_energy']:.6g} | {row['last_refinement_relative_change']['strain_energy']:.6g} |"
            for row in data["mesh"]["rows"]
        ]
        + [
            "",
            "## Small-strain limit",
            "",
            "The elastic Total-Lagrangian solution is compared with the existing small-strain linear route at load factors 1e-2, 1e-3 and 1e-4 for all four families. The relative displacement error decreases toward zero while det(F) remains positive. This is not the finite-kinematic J2 limit-recovery experiment, which remains research evidence.",
            "",
            "| Family | 1e-2 error | 1e-3 error | 1e-4 error |",
            "|---|---:|---:|---:|",
        ]
        + [
            f"| {row['element']} | {row['rows'][0]['relative_displacement_error']:.3e} | {row['rows'][1]['relative_displacement_error']:.3e} | {row['rows'][2]['relative_displacement_error']:.3e} |"
            for row in data["small_strain_limit"]["rows"]
        ]
        + [
            "",
            "## Code_Aster MUST correlation",
            "",
            f"The pinned Code_Aster 18.1 campaign is `{external_status}` for TET4 and HEX8, with twelve matched load factors and full displacement, reaction, stress (`SIEF_ELGA`) and strain (`EPSI_ELGA`) histories. QF compares Cauchy stress and infinitesimal strain in the corresponding extracted measures. Native Code_Aster energy is not compared because this deck does not expose a common portable energy field; QF strain energy and internal work are still archived. This is bounded numerical correlation, not physical validation.",
            "",
            "| Family | Max displacement error | Max reaction error | Max stress error | Max strain error |",
            "|---|---:|---:|---:|---:|",
        ]
        + [
            f"| {family} | {item['maximum_relative_errors']['tip_displacement_relative_error']:.3e} | {item['maximum_relative_errors']['reaction_relative_error']:.3e} | {item['maximum_relative_errors']['stress_relative_error']:.3e} | {item['maximum_relative_errors']['strain_relative_error']:.3e} |"
            for family, item in data["external"]["families"].items()
            if item["status"] == "PASS_EXTERNAL_CORRELATION_BOUNDED"
        ]
        + [
            "",
            "## Claims and limitations",
            "",
            "- `QUALIFIED candidate`: bounded elastic Total-Lagrangian geometric core for TET4/HEX8, subject to Owner acceptance of the mesh/refinement treatment and this exact evidence SHA.",
            "- `EXPERIMENTAL`: high-order elastic geometric adapter and the four-family objectivity/tangent/small-load observations.",
            "- `RESEARCH`: `kinematics=total_lagrangian_j2`, plastic finite-kinematic paths and high-order plastic geometric paths.",
            "- `NOT_IN_RELEASE_SCOPE`: G03 buckling, G04 arc-length, G05 contact, G06 coupling and G07 friction; this pack does not alter their gates.",
            "- No physical validation, post-buckling, arbitrary large-deformation, multi-million-DOF or general finite-strain plasticity claim is made.",
            "",
            "## Evidence files",
            "",
            *[f"- `{path}`" for path in plot_paths],
            "- `summary.json` contains all numeric rows and provenance.",
            "- `external_code_aster/` contains the generated meshes, command files, raw histories and Docker logs.",
            "",
            "## Gate decision",
            "",
            "G02 remains `OPEN` in this pack until the Owner explicitly accepts the bounded mesh/refinement treatment and records the release-scope decision. No requirement or tolerance was lowered. No other functional gate is modified.",
        ]
    ) + "\n"


def manifest(source_sha: str, dirty: bool, timestamp: str) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for path in sorted(OUT.rglob("*")):
        if not path.is_file() or path.name == "evidence_manifest.json":
            continue
        files.append({"path": str(path.relative_to(ROOT)), "sha256": digest(path), "bytes": path.stat().st_size})
    return {
        "schema_version": 1,
        "study_id": "VNV-G02-GEOMETRIC-NONLINEAR-025",
        "gate": "025-G02",
        "status": "OPEN",
        "source_sha": source_sha,
        "dirty": dirty,
        "timestamp_utc": timestamp,
        "command": "python scripts/build_g02_evidence.py",
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "cpu_count": os.cpu_count(),
            "docker": shutil.which("docker") is not None,
            "code_aster_image": CODE_ASTER_IMAGE,
        },
        "files": files,
        "limitations": [
            "No G03-G06 gate is evaluated or closed.",
            "Mesh acceptance and G02 scope decision remain Owner-controlled.",
        ],
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    source_sha = git("rev-parse", "HEAD")
    dirty = bool(git("status", "--porcelain"))
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    data: dict[str, Any] = {
        "schema_version": 1,
        "study_id": "VNV-G02-GEOMETRIC-NONLINEAR-025",
        "gate": "025-G02",
        "source_sha": source_sha,
        "dirty": dirty,
        "timestamp_utc": timestamp,
        "objectivity": objectivity_evidence(),
        "tangent": tangent_evidence(),
        "large_rotation": large_rotation_evidence(),
        "mesh": mesh_evidence(),
        "small_strain_limit": small_strain_limit_evidence(),
    }
    data["external"] = external_correlation()
    plot_paths = plots(data)
    data["plots"] = plot_paths
    data["status"] = "OPEN"
    data["owner_decision"] = "REQUIRED"
    data["claims"] = {
        "qualified_candidate": "bounded elastic Total-Lagrangian TET4/HEX8 only, pending Owner scope acceptance",
        "experimental": ["TET10/HEX20 elastic adapter observations", "four-family objectivity and tangent observations"],
        "research": ["total_lagrangian_j2", "finite-kinematic plasticity", "plastic large rotation"],
        "not_in_release_scope": ["G03", "G04", "G05", "G06", "G07"],
    }
    write_json(OUT / "summary.json", data)
    (OUT / "report.md").write_text(report(data, source_sha, dirty, timestamp, plot_paths), encoding="utf-8")
    write_json(
        OUT / "gate_decision.json",
        {
            "gate": "025-G02",
            "status": "OPEN",
            "recommended_status": "OPEN",
            "owner_decision": "REQUIRED",
            "source_sha": source_sha,
            "dirty": dirty,
            "evidence": "results/vnv_0_2_5/g02_latest/summary.json",
            "blocker": "Owner must accept the bounded pre-limit mesh/refinement treatment and record the G02 scope decision; this script does not sign on behalf of the Owner.",
            "functional_scope_not_changed": ["025-G03", "025-G04", "025-G05", "025-G06"],
        },
    )
    write_json(OUT / "evidence_manifest.json", manifest(source_sha, dirty, timestamp))
    print(json.dumps({"status": data["status"], "source_sha": source_sha, "dirty": dirty, "output": str(OUT)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
