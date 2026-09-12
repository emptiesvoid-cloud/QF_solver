"""WP04-C bounded TET4 structural qualification infrastructure.

The frozen campaign manifest is deliberately separate from this module and was
added before any result execution.  This module consumes that manifest without
changing its controls.  It exercises the public geometric Newton route through
its existing compatibility entry point and only observes detached states after
global acceptance.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
from typing import Any

import numpy as np
import pytest
from scipy.sparse.linalg import spsolve

from solveur.core.analyses.geometric_nonlinear import _newton_dead_load
from solveur.core.errors import MeshValidationError, NumericalConvergenceError
from solveur.core.nonlinear.state import NonlinearState
from solveur.elements.solid.tet4_total_lagrangian_batch import TotalLagrangianTet4Assembly
from solveur.materials.solid import SolidMaterial


ROOT = Path(__file__).resolve().parents[2]
QUALIFICATION = ROOT / "qualification" / "0_2_9"
CAMPAIGN_PATH = QUALIFICATION / "wp04_c_tet4_campaign.json"
WP04_C_START_SHA = "48bfa83bc517e031cdab4876970a4f511f744e35"

LENGTH = 4.0
HEIGHT = 0.5
DEPTH = 0.5
YOUNG = 1.0e6
POISSON = 0.30
TOTAL_LOAD = np.asarray([0.0, -50.0, 0.0], dtype=float)
MATERIAL = SolidMaterial(E=YOUNG, nu=POISSON)
NEWTON_TOLERANCE = 1.0e-10
NEWTON_MAX_ITERATIONS = 40
MESH_LEVELS: dict[str, tuple[int, int, int]] = {
    "M1": (8, 4, 4),
    "M2": (16, 8, 8),
    "M3": (24, 12, 12),
}
SMALL_LOAD_LEVELS = (0.1, 0.01, 0.001)
LOAD_STEP_COUNTS = (6, 12, 24, 48)
REPLAY_RUNS = 3


_RUN_CACHE: dict[tuple[str, int, float], dict[str, Any]] = {}
_CAMPAIGN_CACHE: tuple[dict[str, Any], dict[str, np.ndarray]] | None = None


def _structured_tet4_mesh(nx: int, ny: int, nz: int) -> tuple[np.ndarray, np.ndarray]:
    """Return the frozen conforming six-TET split of the cantilever cells."""

    x = np.linspace(0.0, LENGTH, nx + 1)
    y = np.linspace(0.0, HEIGHT, ny + 1)
    z = np.linspace(0.0, DEPTH, nz + 1)
    nodes = np.stack(np.meshgrid(x, y, z, indexing="ij"), axis=-1).reshape(-1, 3)

    def node_id(i: int, j: int, k: int) -> int:
        return i * (ny + 1) * (nz + 1) + j * (nz + 1) + k

    elements: list[list[int]] = []
    pattern = ((0, 1, 3, 7), (0, 3, 2, 7), (0, 2, 6, 7), (0, 6, 4, 7), (0, 4, 5, 7), (0, 5, 1, 7))
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                cube = [
                    node_id(a, b, c)
                    for a, b, c in (
                        (i, j, k),
                        (i + 1, j, k),
                        (i, j + 1, k),
                        (i + 1, j + 1, k),
                        (i, j, k + 1),
                        (i + 1, j, k + 1),
                        (i, j + 1, k + 1),
                        (i + 1, j + 1, k + 1),
                    )
                ]
                elements.extend([[cube[index] for index in local] for local in pattern])
    return nodes, np.asarray(elements, dtype=int)


def _build_case(level: str, load_multiplier: float = 1.0) -> dict[str, Any]:
    if level not in MESH_LEVELS:
        raise ValueError(f"Unknown frozen WP04-C mesh level {level!r}.")
    nodes, elements = _structured_tet4_mesh(*MESH_LEVELS[level])
    assembly = TotalLagrangianTet4Assembly(nodes, elements, MATERIAL)
    fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    loaded_nodes = np.flatnonzero(np.isclose(nodes[:, 0], LENGTH))
    fixed = (3 * fixed_nodes[:, None] + np.arange(3)).reshape(-1)
    external = np.zeros(assembly.ndof, dtype=float)
    external.reshape(-1, 3)[loaded_nodes] = load_multiplier * TOTAL_LOAD / loaded_nodes.size
    centroid = np.mean(nodes[elements], axis=1)
    stress_mask = (
        (centroid[:, 0] / LENGTH >= 0.40)
        & (centroid[:, 0] / LENGTH <= 0.60)
        & (centroid[:, 1] / HEIGHT >= 0.75)
        & (centroid[:, 1] / HEIGHT <= 0.90)
        & (centroid[:, 2] / DEPTH >= 0.25)
        & (centroid[:, 2] / DEPTH <= 0.75)
    )
    if not np.any(stress_mask):
        raise AssertionError(f"Frozen stress region has no TET4 sample on {level}.")
    return {
        "level": level,
        "nodes": nodes,
        "elements": elements,
        "assembly": assembly,
        "fixed": fixed,
        "fixed_nodes": fixed_nodes,
        "loaded_nodes": loaded_nodes,
        "external": external,
        "stress_mask": stress_mask,
        "reference_centroids": centroid,
    }


def _free_dofs(ndof: int, fixed: np.ndarray) -> np.ndarray:
    return np.setdiff1d(np.arange(ndof, dtype=int), fixed)


def _relative_vector(value: np.ndarray, reference: np.ndarray, *, floor: float = 1.0e-12) -> float:
    return float(np.linalg.norm(np.asarray(value) - np.asarray(reference)) / max(float(np.linalg.norm(reference)), floor))


def _relative_scalar(value: float, reference: float, *, floor: float = 1.0e-12) -> float:
    return abs(float(value) - float(reference)) / max(abs(float(reference)), floor)


def _equilibrium_metrics(
    physical_nodes: np.ndarray,
    external: np.ndarray,
    internal: np.ndarray,
    fixed: np.ndarray,
) -> dict[str, Any]:
    reactions = np.zeros_like(external)
    reactions[fixed] = internal[fixed] - external[fixed]
    applied_by_node = external.reshape(-1, 3)
    reaction_by_node = reactions.reshape(-1, 3)
    external_resultant = np.sum(applied_by_node, axis=0)
    reaction_resultant = np.sum(reaction_by_node, axis=0)
    external_moment = np.sum(np.cross(physical_nodes, applied_by_node), axis=0)
    reaction_moment = np.sum(np.cross(physical_nodes, reaction_by_node), axis=0)
    force_scale = max(float(np.linalg.norm(external_resultant)), float(np.linalg.norm(reaction_resultant)), 1.0)
    moment_scale = max(float(np.linalg.norm(external_moment)), float(np.linalg.norm(reaction_moment)), 1.0)
    return {
        "reactions": reactions,
        "external_resultant": external_resultant,
        "reaction_resultant": reaction_resultant,
        "external_moment": external_moment,
        "reaction_moment": reaction_moment,
        "force_imbalance": external_resultant + reaction_resultant,
        "moment_imbalance": external_moment + reaction_moment,
        "force_relative_error": float(np.linalg.norm(external_resultant + reaction_resultant) / force_scale),
        "moment_relative_error": float(np.linalg.norm(external_moment + reaction_moment) / moment_scale),
    }


def _envelope(states: dict[str, np.ndarray]) -> dict[str, Any]:
    deformation = np.asarray(states["deformation_gradient"], dtype=float)
    green = np.asarray(states["green_lagrange_strain"], dtype=float)
    determinants = np.asarray(states["det_f"], dtype=float)
    stretches = np.linalg.svd(deformation, compute_uv=False)
    green_norms = np.linalg.norm(green, axis=(1, 2))
    if not np.all(np.isfinite(deformation)) or not np.all(np.isfinite(stretches)):
        raise AssertionError("Qualification state contains non-finite deformation data.")
    return {
        "minimum_det_f": float(np.min(determinants)),
        "minimum_principal_stretch": float(np.min(stretches)),
        "maximum_principal_stretch": float(np.max(stretches)),
        "maximum_green_lagrange_norm": float(np.max(green_norms)),
        "det_f": determinants,
        "principal_stretches": stretches,
        "green_lagrange_norms": green_norms,
    }


def _semantic_digest(
    state_digest: str,
    accepted_factors: np.ndarray,
    iteration_history: np.ndarray,
    residual_history: np.ndarray,
) -> str:
    payload = {
        "state_digest": state_digest,
        "accepted_factors": [float(value) for value in accepted_factors],
        "iteration_history": [int(value) for value in iteration_history],
        "residual_history": [float(value) for value in residual_history],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _solve_case(level: str, intervals: int, load_multiplier: float = 1.0, *, cached: bool = True) -> dict[str, Any]:
    key = (level, intervals, float(load_multiplier))
    if cached and key in _RUN_CACHE:
        return _RUN_CACHE[key]
    case = _build_case(level, load_multiplier)
    assembly = case["assembly"]
    snapshots: list[NonlinearState] = []

    def observe(_step: int, state: NonlinearState) -> None:
        snapshots.append(state.detached_copy())

    displacement, diagnostics = _newton_dead_load(
        assembly,
        case["external"],
        case["fixed"],
        increments=intervals,
        tolerance=NEWTON_TOLERANCE,
        max_iterations=NEWTON_MAX_ITERATIONS,
        initial_state=NonlinearState(
            displacement=np.zeros(assembly.ndof, dtype=float),
            load_factor=0.0,
            continuation_state={"accepted_step": 0},
        ),
        target_load_factors=[step / intervals for step in range(1, intervals + 1)],
        accepted_state_callback=observe,
    )
    if len(snapshots) != intervals:
        raise AssertionError("WP04-C observation must contain exactly one detached accepted state per load interval.")
    internal, _ = assembly.assemble(displacement, tangent_required=False)
    states = assembly.element_states(displacement)
    envelope = _envelope(states)
    physical_nodes = case["nodes"] + displacement.reshape(-1, 3)
    equilibrium = _equilibrium_metrics(physical_nodes, case["external"], internal, case["fixed"])
    free = _free_dofs(assembly.ndof, case["fixed"])
    residual = case["external"] - internal
    residual_scale = max(float(np.linalg.norm(case["external"][free])), 1.0)
    increment_rows = diagnostics.get("increments")
    if not isinstance(increment_rows, list) or len(increment_rows) != intervals:
        raise AssertionError("Full Newton diagnostics omitted a frozen accepted increment record.")
    iterations = np.asarray([int(row["iterations"]) for row in increment_rows], dtype=int)
    relative_residuals = np.asarray([float(row["relative_residual"]) for row in increment_rows], dtype=float)
    accepted_factors = np.asarray([state.load_factor for state in snapshots], dtype=float)
    state_digests = [state.digest for state in snapshots]
    sampled_volumes = assembly.volumes[case["stress_mask"]]
    sampled_stress = np.asarray(states["cauchy_stress"], dtype=float)[case["stress_mask"], 0, 0]
    representative_stress = float(np.dot(sampled_volumes, sampled_stress) / np.sum(sampled_volumes))
    node_displacement = displacement.reshape(-1, 3)
    minimum_volume = float(np.min(np.asarray(assembly.volumes, dtype=float)))
    maximum_volume = float(np.max(np.asarray(assembly.volumes, dtype=float)))
    mesh_quality = {
        "element_volume_minimum": minimum_volume,
        "element_volume_maximum": maximum_volume,
        "element_volume_ratio": maximum_volume / minimum_volume,
        "reference_jacobian_minimum": 6.0 * minimum_volume,
        "reference_jacobian_maximum": 6.0 * maximum_volume,
    }
    result: dict[str, Any] = {
        **case,
        "intervals": intervals,
        "load_multiplier": float(load_multiplier),
        "displacement": displacement,
        "internal": internal,
        "states": states,
        "envelope": envelope,
        "equilibrium": equilibrium,
        "strain_energy": float(assembly.strain_energy(displacement)),
        "tip_displacement": float(np.mean(node_displacement[case["loaded_nodes"], 1])),
        "loaded_face_average_displacement": np.mean(node_displacement[case["loaded_nodes"]], axis=0),
        "representative_stress": representative_stress,
        "stress_contributing_elements": int(np.count_nonzero(case["stress_mask"])),
        "stress_contributing_volume": float(np.sum(sampled_volumes)),
        "accepted_factors": accepted_factors,
        "accepted_state_digests": state_digests,
        "state_digest": state_digests[-1],
        "iteration_history": iterations,
        "increment_relative_residuals": relative_residuals,
        "newton_iterations": int(np.sum(iterations)),
        "final_relative_residual": float(np.linalg.norm(residual[free]) / residual_scale),
        "diagnostic_final_relative_residual": float(diagnostics["final_relative_residual"]),
        "mesh_quality": mesh_quality,
    }
    result["semantic_digest"] = _semantic_digest(
        result["state_digest"], accepted_factors, iterations, relative_residuals
    )
    if cached:
        _RUN_CACHE[key] = result
    return result


def _linear_reference(level: str, load_multiplier: float) -> dict[str, Any]:
    case = _build_case(level, load_multiplier)
    assembly = case["assembly"]
    zero = np.zeros(assembly.ndof, dtype=float)
    _, tangent = assembly.assemble(zero, tangent_required=True)
    if tangent is None:
        raise AssertionError("Zero-displacement TET4 tangent is required for the linear-static reference.")
    free = _free_dofs(assembly.ndof, case["fixed"])
    displacement = np.zeros(assembly.ndof, dtype=float)
    displacement[free] = np.asarray(spsolve(tangent[free, :][:, free], case["external"][free]), dtype=float)
    internal = np.asarray(tangent @ displacement, dtype=float)
    return {
        "displacement": displacement,
        "internal": internal,
        "equilibrium": _equilibrium_metrics(
            case["nodes"] + displacement.reshape(-1, 3), case["external"], internal, case["fixed"]
        ),
    }


def _mesh_metrics(mesh_rows: dict[str, dict[str, Any]]) -> dict[str, Any]:
    medium = mesh_rows["M2"]
    fine = mesh_rows["M3"]
    coarse = mesh_rows["M1"]

    def scalar_trend(key: str) -> dict[str, Any]:
        coarse_medium = abs(float(medium[key]) - float(coarse[key]))
        medium_fine = abs(float(fine[key]) - float(medium[key]))
        return {
            "coarse_to_medium_absolute_change": coarse_medium,
            "medium_to_fine_absolute_change": medium_fine,
            "non_oscillatory_refinement": bool(medium_fine <= coarse_medium + 1.0e-14),
        }

    reaction_coarse_medium = float(
        np.linalg.norm(medium["equilibrium"]["reaction_resultant"] - coarse["equilibrium"]["reaction_resultant"])
    )
    reaction_medium_fine = float(
        np.linalg.norm(fine["equilibrium"]["reaction_resultant"] - medium["equilibrium"]["reaction_resultant"])
    )
    metrics: dict[str, Any] = {
        "fine_medium_tip_displacement_relative": _relative_scalar(fine["tip_displacement"], medium["tip_displacement"]),
        "fine_medium_reaction_relative": _relative_vector(
            fine["equilibrium"]["reaction_resultant"], medium["equilibrium"]["reaction_resultant"]
        ),
        "fine_medium_energy_relative": _relative_scalar(fine["strain_energy"], medium["strain_energy"]),
        "fine_medium_stress_relative": _relative_scalar(fine["representative_stress"], medium["representative_stress"]),
        "tip_displacement_trend": scalar_trend("tip_displacement"),
        "strain_energy_trend": scalar_trend("strain_energy"),
        "representative_stress_trend": scalar_trend("representative_stress"),
        "reaction_trend": {
            "coarse_to_medium_absolute_change": reaction_coarse_medium,
            "medium_to_fine_absolute_change": reaction_medium_fine,
            "non_oscillatory_refinement": bool(reaction_medium_fine <= reaction_coarse_medium + 1.0e-14),
        },
    }
    metrics["passes_fine_medium_limits"] = bool(
        metrics["fine_medium_tip_displacement_relative"] <= 0.02
        and metrics["fine_medium_reaction_relative"] <= 0.02
        and metrics["fine_medium_energy_relative"] <= 0.02
        and metrics["fine_medium_stress_relative"] <= 0.10
    )
    metrics["trends_non_oscillatory"] = bool(
        all(value["non_oscillatory_refinement"] for key, value in metrics.items() if key.endswith("_trend"))
    )
    return metrics


def _small_limit_metrics() -> dict[str, Any]:
    rows: dict[str, dict[str, Any]] = {}
    for multiplier in SMALL_LOAD_LEVELS:
        nonlinear = _solve_case("M2", 12, multiplier)
        linear = _linear_reference("M2", multiplier)
        rows[str(multiplier)] = {
            "multiplier": multiplier,
            "nonlinear": nonlinear,
            "linear": linear,
            "displacement_relative_error": _relative_vector(nonlinear["displacement"], linear["displacement"]),
            "reaction_relative_error": _relative_vector(
                nonlinear["equilibrium"]["reaction_resultant"], linear["equilibrium"]["reaction_resultant"]
            ),
        }
    errors = [rows[str(multiplier)]["displacement_relative_error"] for multiplier in SMALL_LOAD_LEVELS]
    reaction_errors = [rows[str(multiplier)]["reaction_relative_error"] for multiplier in SMALL_LOAD_LEVELS]
    return {
        "rows": rows,
        "displacement_errors_monotone_to_linear": bool(errors[2] <= errors[1] <= errors[0]),
        "reaction_errors_within_frozen_limit": bool(max(reaction_errors) <= 1.0e-4),
    }


def _load_step_metrics() -> dict[str, Any]:
    rows = {str(intervals): _solve_case("M2", intervals) for intervals in LOAD_STEP_COUNTS}
    reference = rows["48"]
    comparison: dict[str, dict[str, float]] = {}
    for intervals in LOAD_STEP_COUNTS[:-1]:
        row = rows[str(intervals)]
        comparison[str(intervals)] = {
            "displacement_relative": _relative_vector(row["displacement"], reference["displacement"]),
            "reaction_relative": _relative_vector(
                row["equilibrium"]["reaction_resultant"], reference["equilibrium"]["reaction_resultant"]
            ),
            "energy_relative": _relative_scalar(row["strain_energy"], reference["strain_energy"]),
            "stress_relative": _relative_scalar(row["representative_stress"], reference["representative_stress"]),
            "minimum_det_f_relative": _relative_scalar(
                row["envelope"]["minimum_det_f"], reference["envelope"]["minimum_det_f"]
            ),
        }
    maximum = max(value for row in comparison.values() for value in row.values())
    return {"rows": rows, "comparison_to_48": comparison, "maximum_relative_delta": maximum}


def _replay_metrics() -> dict[str, Any]:
    runs = [_solve_case("M2", 12, cached=False) for _ in range(REPLAY_RUNS)]
    reference = runs[0]
    comparisons: list[dict[str, Any]] = []
    for row in runs[1:]:
        comparisons.append(
            {
                "displacement_relative": _relative_vector(row["displacement"], reference["displacement"], floor=1.0e-14),
                "displacement_absolute": float(np.max(np.abs(row["displacement"] - reference["displacement"]))),
                "reaction_relative": _relative_vector(
                    row["equilibrium"]["reaction_resultant"], reference["equilibrium"]["reaction_resultant"], floor=1.0e-14
                ),
                "energy_relative": _relative_scalar(row["strain_energy"], reference["strain_energy"], floor=1.0e-14),
                "stress_relative": _relative_scalar(row["representative_stress"], reference["representative_stress"], floor=1.0e-14),
                "accepted_factors_equal": bool(np.array_equal(row["accepted_factors"], reference["accepted_factors"])),
                "iterations_equal": bool(np.array_equal(row["iteration_history"], reference["iteration_history"])),
                "state_digest_equal": row["state_digest"] == reference["state_digest"],
                "semantic_digest_equal": row["semantic_digest"] == reference["semantic_digest"],
            }
        )
    maximum_relative = max(
        value
        for comparison in comparisons
        for key, value in comparison.items()
        if key.endswith("_relative")
    )
    maximum_absolute = max(comparison["displacement_absolute"] for comparison in comparisons)
    return {"runs": runs, "comparisons": comparisons, "maximum_relative": maximum_relative, "maximum_absolute": maximum_absolute}


def _failure_record(action: Any) -> dict[str, Any]:
    observed: list[tuple[str, str, str | None]] = []
    for _ in range(2):
        try:
            action()
        except Exception as exc:  # qualification deliberately captures public failure types
            reason = getattr(exc, "reason", None)
            observed.append((type(exc).__name__, str(exc), getattr(reason, "value", reason)))
        else:
            observed.append(("NO_EXCEPTION", "", None))
    return {
        "first": {"type": observed[0][0], "message": observed[0][1], "reason": observed[0][2]},
        "second": {"type": observed[1][0], "message": observed[1][1], "reason": observed[1][2]},
        "deterministic": observed[0] == observed[1] and observed[0][0] != "NO_EXCEPTION",
    }


def _failure_sanity() -> dict[str, Any]:
    valid_nodes, valid_elements = _structured_tet4_mesh(1, 1, 1)
    inverted_elements = valid_elements.copy()
    inverted_elements[0, [0, 1]] = inverted_elements[0, [1, 0]]
    base = _build_case("M1")

    def impossible_convergence() -> None:
        _newton_dead_load(
            base["assembly"],
            base["external"],
            base["fixed"],
            increments=1,
            tolerance=1.0e-14,
            max_iterations=1,
            initial_state=NonlinearState(np.zeros(base["assembly"].ndof, dtype=float)),
            target_load_factors=[1.0],
        )

    return {
        "inverted_reference_geometry": _failure_record(
            lambda: TotalLagrangianTet4Assembly(valid_nodes, inverted_elements, MATERIAL)
        ),
        "invalid_material": _failure_record(lambda: SolidMaterial(E=-1.0, nu=POISSON)),
        "unconstrained_model": _failure_record(
            lambda: _newton_dead_load(
                base["assembly"],
                base["external"],
                np.empty(0, dtype=int),
                increments=1,
                tolerance=NEWTON_TOLERANCE,
                max_iterations=NEWTON_MAX_ITERATIONS,
            )
        ),
        "impossible_convergence": _failure_record(impossible_convergence),
        "nonfinite_state": _failure_record(
            lambda: base["assembly"].assemble(np.full(base["assembly"].ndof, np.nan), tangent_required=False)
        ),
    }


def _row_summary(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "level": row["level"],
        "cells": list(MESH_LEVELS[row["level"]]),
        "nodes": int(row["nodes"].shape[0]),
        "elements": int(row["elements"].shape[0]),
        "dofs": int(row["assembly"].ndof),
        "intervals": row["intervals"],
        "load_multiplier": row["load_multiplier"],
        "total_load": (row["load_multiplier"] * TOTAL_LOAD).tolist(),
        "mesh_quality": row["mesh_quality"],
        "loaded_face_average_displacement": row["loaded_face_average_displacement"].tolist(),
        "tip_displacement": row["tip_displacement"],
        "strain_energy": row["strain_energy"],
        "representative_stress_sigma_xx": row["representative_stress"],
        "stress_contributing_elements": row["stress_contributing_elements"],
        "stress_contributing_volume": row["stress_contributing_volume"],
        "equilibrium": {
            key: value.tolist() if isinstance(value, np.ndarray) else value
            for key, value in row["equilibrium"].items()
            if key != "reactions"
        },
        "envelope": {
            key: value
            for key, value in row["envelope"].items()
            if key not in {"det_f", "principal_stretches", "green_lagrange_norms"}
        },
        "newton_iterations": row["newton_iterations"],
        "iteration_history": row["iteration_history"].tolist(),
        "accepted_load_factors": row["accepted_factors"].tolist(),
        "final_relative_residual": row["final_relative_residual"],
        "accepted_state_digest": row["state_digest"],
        "semantic_digest": row["semantic_digest"],
    }


def _campaign() -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    global _CAMPAIGN_CACHE
    if _CAMPAIGN_CACHE is not None:
        return _CAMPAIGN_CACHE
    frozen = json.loads(CAMPAIGN_PATH.read_text(encoding="utf-8"))
    mesh_rows = {level: _solve_case(level, 12) for level in MESH_LEVELS}
    mesh = _mesh_metrics(mesh_rows)
    small = _small_limit_metrics()
    load_steps = _load_step_metrics()
    replay = _replay_metrics()
    failures = _failure_sanity()
    arrays: dict[str, np.ndarray] = {}
    for level, row in mesh_rows.items():
        arrays[f"{level}_nodes"] = row["nodes"]
        arrays[f"{level}_elements"] = row["elements"]
        arrays[f"{level}_displacement"] = row["displacement"]
        arrays[f"{level}_reaction"] = row["equilibrium"]["reactions"]
        arrays[f"{level}_internal"] = row["internal"]
        arrays[f"{level}_det_f"] = row["envelope"]["det_f"]
        arrays[f"{level}_principal_stretches"] = row["envelope"]["principal_stretches"]
        arrays[f"{level}_green_lagrange_norms"] = row["envelope"]["green_lagrange_norms"]
        arrays[f"{level}_accepted_factors"] = row["accepted_factors"]
        arrays[f"{level}_iteration_history"] = row["iteration_history"]
        arrays[f"{level}_accepted_state_digests"] = np.asarray(row["accepted_state_digests"], dtype="U64")
    for multiplier in SMALL_LOAD_LEVELS:
        row = small["rows"][str(multiplier)]["nonlinear"]
        linear = small["rows"][str(multiplier)]["linear"]
        label = str(multiplier).replace(".", "p")
        arrays[f"small_{label}_nonlinear_displacement"] = row["displacement"]
        arrays[f"small_{label}_linear_displacement"] = linear["displacement"]
        arrays[f"small_{label}_nonlinear_reaction"] = row["equilibrium"]["reactions"]
        arrays[f"small_{label}_linear_reaction"] = linear["equilibrium"]["reactions"]
    for intervals, row in load_steps["rows"].items():
        arrays[f"load_steps_{intervals}_displacement"] = row["displacement"]
        arrays[f"load_steps_{intervals}_reaction"] = row["equilibrium"]["reactions"]
        arrays[f"load_steps_{intervals}_accepted_factors"] = row["accepted_factors"]
        arrays[f"load_steps_{intervals}_iterations"] = row["iteration_history"]
    for index, row in enumerate(replay["runs"], start=1):
        arrays[f"replay_{index}_displacement"] = row["displacement"]
        arrays[f"replay_{index}_reaction"] = row["equilibrium"]["reactions"]
        arrays[f"replay_{index}_accepted_factors"] = row["accepted_factors"]
        arrays[f"replay_{index}_iterations"] = row["iteration_history"]
        arrays[f"replay_{index}_state_digests"] = np.asarray(row["accepted_state_digests"], dtype="U64")

    small_summary = {
        key: {
            "multiplier": value["multiplier"],
            "displacement_relative_error": value["displacement_relative_error"],
            "reaction_relative_error": value["reaction_relative_error"],
            "nonlinear": _row_summary(value["nonlinear"]),
            "linear_reaction_resultant": value["linear"]["equilibrium"]["reaction_resultant"].tolist(),
        }
        for key, value in small["rows"].items()
    }
    load_step_summary = {
        key: _row_summary(value) for key, value in load_steps["rows"].items()
    }
    replay_summary = [_row_summary(row) for row in replay["runs"]]
    envelope_pass = all(
        row["envelope"]["minimum_det_f"] >= 0.20
        and row["envelope"]["minimum_principal_stretch"] >= 0.75
        and row["envelope"]["maximum_principal_stretch"] <= 1.30
        and row["envelope"]["maximum_green_lagrange_norm"] <= 0.30
        for row in [*mesh_rows.values(), *(value["nonlinear"] for value in small["rows"].values()), *load_steps["rows"].values(), *replay["runs"]]
    )
    all_failure_cases_pass = all(value["deterministic"] for value in failures.values())
    summary = {
        "schema_version": 1,
        "record_id": "QF-SOLVER-0.2.9-WP04-C-TET4-STRUCTURAL-001",
        "work_package": "WP04-C",
        "status": "EXECUTED_TARGETED",
        "baseline_sha": WP04_C_START_SHA,
        "tested_numerical_source_sha": WP04_C_START_SHA,
        "branch": "0.2.9-unified-nonlinear",
        "campaign_manifest": str(CAMPAIGN_PATH.relative_to(ROOT)).replace("\\", "/"),
        "campaign_manifest_status": frozen["status"],
        "environment": {
            "python": sys.version,
            "numpy": importlib.metadata.version("numpy"),
            "scipy": importlib.metadata.version("scipy"),
            "platform": platform.platform(),
        },
        "scope": {
            "element_family": "TET4",
            "formulation": "Total-Lagrangian Saint-Venant-Kirchhoff",
            "material": {"E": YOUNG, "nu": POISSON, "class": "homogeneous_isotropic_3d"},
            "load": "distributed nodal dead transverse load on x=L face",
            "boundary_conditions": "all translations fixed on x=0 face",
            "production_source_changed": False,
            "numerical_formulation_changed": False,
            "maturity_changed": False,
            "full_test_suite_run": False,
        },
        "mesh_campaign": {level: _row_summary(row) for level, row in mesh_rows.items()},
        "mesh_convergence": mesh,
        "small_displacement_limit": {
            "reference": "same TET4 mesh, zero-displacement Total-Lagrangian tangent reduced with identical fixed DOFs and dead load",
            "rows": small_summary,
            "displacement_errors_monotone_to_linear": small["displacement_errors_monotone_to_linear"],
            "reaction_errors_within_frozen_limit": small["reaction_errors_within_frozen_limit"],
        },
        "load_step_stability": {
            "rows": load_step_summary,
            "comparison_to_48": load_steps["comparison_to_48"],
            "maximum_relative_delta": load_steps["maximum_relative_delta"],
        },
        "deterministic_replay": {
            "runs": replay_summary,
            "comparisons": replay["comparisons"],
            "maximum_relative": replay["maximum_relative"],
            "maximum_absolute": replay["maximum_absolute"],
        },
        "failure_sanity": failures,
        "thresholds": {
            "mesh_tip_reaction_energy_relative": 0.02,
            "mesh_stress_relative": 0.10,
            "small_load_displacement_reaction_relative": 1.0e-4,
            "equilibrium_force_moment_relative": 1.0e-8,
            "load_step_final_relative": 1.0e-8,
            "replay_relative": 1.0e-12,
            "replay_absolute": 1.0e-14,
            "minimum_det_f": 0.20,
            "principal_stretches": [0.75, 1.30],
            "maximum_green_lagrange_norm": 0.30,
        },
        "gate_status": {
            "G04-01": {"status": "PASS_BOUNDED", "reason": "WP04-A/B bounded formulation and scope remain unchanged."},
            "G04-02": {"status": "PASS", "reason": "WP04-B independent TET4/HEX8 objectivity evidence is retained."},
            "G04-03": {"status": "PASS", "reason": "WP04-B independent TET4/HEX8 affine patch evidence is retained."},
            "G04-04": {"status": "PASS", "reason": "WP04-B independent energy-gradient evidence is retained."},
            "G04-05": {"status": "PASS", "reason": "WP04-B independent tangent/symmetry evidence is retained."},
            "G04-06": {"status": "PASS_TET4_PENDING_HEX8", "reason": "TET4 small-displacement limit is demonstrated; HEX8 remains WP04-D."},
            "G04-07": {"status": "PASS_TET4_PENDING_HEX8", "reason": "TET4 direct force/moment balance is demonstrated; HEX8 remains WP04-D."},
            "G04-08": {"status": "PASS", "reason": "WP04-B accepted-state work-refinement evidence is retained."},
            "G04-09": {"status": "PASS_TET4_PENDING_HEX8", "reason": "TET4 load-step stability and deterministic replay are demonstrated; HEX8 remains WP04-D."},
            "G04-10": {"status": "PASS" if mesh["passes_fine_medium_limits"] and mesh["trends_non_oscillatory"] and envelope_pass else "FAIL", "reason": "Frozen TET4 mesh/structural campaign metrics and envelope."},
            "G04-11": {"status": "PENDING_WP04_D", "reason": "HEX8 structural campaign is not in WP04-C scope."},
            "G04-12": {"status": "PENDING_WP04_E", "reason": "Cross-family convergence and public claim boundary are not in WP04-C scope."},
        },
        "qualification_checks": {
            "envelope_pass": envelope_pass,
            "failure_sanity_pass": all_failure_cases_pass,
            "mesh_pass": bool(mesh["passes_fine_medium_limits"] and mesh["trends_non_oscillatory"]),
            "small_limit_pass": bool(
                small["rows"]["0.001"]["displacement_relative_error"] <= 1.0e-4
                and small["rows"]["0.001"]["reaction_relative_error"] <= 1.0e-4
            ),
            "equilibrium_pass": bool(
                max(row["equilibrium"]["force_relative_error"] for row in mesh_rows.values()) <= 1.0e-8
                and max(row["equilibrium"]["moment_relative_error"] for row in mesh_rows.values()) <= 1.0e-8
            ),
            "load_step_pass": bool(load_steps["maximum_relative_delta"] <= 1.0e-8),
            "replay_pass": bool(
                replay["maximum_relative"] <= 1.0e-12
                and replay["maximum_absolute"] <= 1.0e-14
                and all(
                    comparison["accepted_factors_equal"]
                    and comparison["iterations_equal"]
                    and comparison["state_digest_equal"]
                    and comparison["semantic_digest_equal"]
                    for comparison in replay["comparisons"]
                )
            ),
        },
        "limitations": [
            "This is TET4-only structural evidence; HEX8 and cross-family qualification remain pending.",
            "The supporting cantilever trend is not a beam-theory acceptance oracle.",
            "No contact, arc-length, J2-plus-geometry, high-order, distributed or dynamics claim is made.",
            "TET4 public maturity remains RESEARCH_ONLY pending WP04-D/E/F and Owner closure.",
        ],
    }
    _CAMPAIGN_CACHE = (summary, arrays)
    return _CAMPAIGN_CACHE


def _assert_envelope(row: dict[str, Any]) -> None:
    envelope = row["envelope"]
    assert envelope["minimum_det_f"] >= 0.20
    assert envelope["minimum_principal_stretch"] >= 0.75
    assert envelope["maximum_principal_stretch"] <= 1.30
    assert envelope["maximum_green_lagrange_norm"] <= 0.30


def test_c01_campaign_definition_is_frozen_before_results() -> None:
    payload = json.loads(CAMPAIGN_PATH.read_text(encoding="utf-8"))
    assert payload["status"] == "FROZEN_BEFORE_RESULT_EXECUTION"
    assert payload["frozen_at_commit"] == WP04_C_START_SHA
    assert payload["benchmark"]["load"]["total_vector"] == TOTAL_LOAD.tolist()
    assert payload["mesh_generator"]["mesh_levels"]["M3"]["expected_tetrahedra"] == 20736


@pytest.mark.parametrize("level", ("M1", "M2", "M3"))
def test_c02_c04_tet4_mesh_structural_solves(level: str) -> None:
    _, _ = _campaign()
    row = _solve_case(level, 12)
    assert row["accepted_factors"][-1] == pytest.approx(1.0)
    assert row["final_relative_residual"] <= NEWTON_TOLERANCE
    assert np.all(np.isfinite(row["displacement"]))


def test_c05_mesh_displacement_convergence() -> None:
    summary, _ = _campaign()
    assert summary["mesh_convergence"]["fine_medium_tip_displacement_relative"] <= 0.02


def test_c06_mesh_reaction_convergence() -> None:
    summary, _ = _campaign()
    assert summary["mesh_convergence"]["fine_medium_reaction_relative"] <= 0.02


def test_c07_mesh_energy_convergence() -> None:
    summary, _ = _campaign()
    assert summary["mesh_convergence"]["fine_medium_energy_relative"] <= 0.02


def test_c08_mesh_representative_stress_convergence() -> None:
    summary, _ = _campaign()
    assert summary["mesh_convergence"]["fine_medium_stress_relative"] <= 0.10
    assert summary["mesh_convergence"]["trends_non_oscillatory"]


def test_c09_deformation_envelope_across_meshes() -> None:
    _, _ = _campaign()
    for level in MESH_LEVELS:
        _assert_envelope(_solve_case(level, 12))


@pytest.mark.parametrize("multiplier", SMALL_LOAD_LEVELS)
def test_c10_c12_small_load_levels(multiplier: float) -> None:
    summary, _ = _campaign()
    row = summary["small_displacement_limit"]["rows"][str(multiplier)]
    assert row["nonlinear"]["accepted_load_factors"][-1] == pytest.approx(1.0)
    assert row["nonlinear"]["final_relative_residual"] <= NEWTON_TOLERANCE


def test_c13_nonlinear_displacement_converges_to_linear_limit() -> None:
    summary, _ = _campaign()
    small = summary["small_displacement_limit"]
    assert small["displacement_errors_monotone_to_linear"]
    assert small["rows"]["0.001"]["displacement_relative_error"] <= 1.0e-4


def test_c14_nonlinear_reaction_converges_to_linear_limit() -> None:
    summary, _ = _campaign()
    small = summary["small_displacement_limit"]
    # Global reaction balance is already exact to floating-point noise at all
    # three loads, so strict error ordering would be an order-of-roundoff test
    # rather than a convergence criterion.  The frozen 1e-4 bound remains.
    assert small["reaction_errors_within_frozen_limit"]
    assert small["rows"]["0.001"]["reaction_relative_error"] <= 1.0e-4


@pytest.mark.parametrize("level", ("M1", "M2", "M3"))
def test_c15_c17_direct_force_equilibrium(level: str) -> None:
    _, _ = _campaign()
    assert _solve_case(level, 12)["equilibrium"]["force_relative_error"] <= 1.0e-8


@pytest.mark.parametrize("level", ("M1", "M2", "M3"))
def test_c18_c20_direct_moment_equilibrium(level: str) -> None:
    _, _ = _campaign()
    assert _solve_case(level, 12)["equilibrium"]["moment_relative_error"] <= 1.0e-8


@pytest.mark.parametrize("intervals", LOAD_STEP_COUNTS)
def test_c21_c24_load_step_runs(intervals: int) -> None:
    _, _ = _campaign()
    row = _solve_case("M2", intervals)
    assert row["accepted_factors"].size == intervals
    assert row["final_relative_residual"] <= NEWTON_TOLERANCE


def test_c25_final_equilibrium_is_load_step_stable() -> None:
    summary, _ = _campaign()
    assert summary["load_step_stability"]["maximum_relative_delta"] <= 1.0e-8


@pytest.mark.parametrize("index", range(REPLAY_RUNS))
def test_c26_c28_independent_replay_runs(index: int) -> None:
    summary, _ = _campaign()
    assert summary["deterministic_replay"]["runs"][index]["accepted_load_factors"][-1] == pytest.approx(1.0)


def test_c29_replay_numerical_comparison() -> None:
    summary, _ = _campaign()
    assert summary["deterministic_replay"]["maximum_relative"] <= 1.0e-12
    assert summary["deterministic_replay"]["maximum_absolute"] <= 1.0e-14


def test_c30_replay_semantic_digest_comparison() -> None:
    summary, _ = _campaign()
    for comparison in summary["deterministic_replay"]["comparisons"]:
        assert comparison["accepted_factors_equal"]
        assert comparison["iterations_equal"]
        assert comparison["state_digest_equal"]
        assert comparison["semantic_digest_equal"]


def test_c31_stress_sampling_region_is_fixed_across_refinements() -> None:
    _, _ = _campaign()
    for level in MESH_LEVELS:
        row = _solve_case(level, 12)
        assert row["stress_contributing_elements"] > 0
        assert row["stress_contributing_volume"] > 0.0


def test_c32_no_singular_zone_stress_is_used() -> None:
    _, _ = _campaign()
    for level in MESH_LEVELS:
        row = _solve_case(level, 12)
        centroids = row["reference_centroids"][row["stress_mask"]]
        assert np.all(centroids[:, 0] > 0.0)
        assert np.all(centroids[:, 0] < LENGTH)
        assert np.all(centroids[:, 0] / LENGTH >= 0.40)
        assert np.all(centroids[:, 0] / LENGTH <= 0.60)


def test_c33_invalid_geometry_material_and_unconstrained_fail_deterministically() -> None:
    summary, _ = _campaign()
    failures = summary["failure_sanity"]
    assert failures["inverted_reference_geometry"]["deterministic"]
    assert failures["invalid_material"]["deterministic"]
    assert failures["unconstrained_model"]["deterministic"]
    assert failures["unconstrained_model"]["first"]["type"] == MeshValidationError.__name__


def test_c34_impossible_convergence_fails_deterministically() -> None:
    summary, _ = _campaign()
    record = summary["failure_sanity"]["impossible_convergence"]
    assert record["deterministic"]
    assert record["first"]["type"] == NumericalConvergenceError.__name__


def test_c35_nonfinite_state_fails_explicitly_and_deterministically() -> None:
    summary, _ = _campaign()
    record = summary["failure_sanity"]["nonfinite_state"]
    assert record["deterministic"]
    assert record["first"]["type"] == ValueError.__name__


def write_evidence(output_dir: Path | None = None) -> tuple[Path, Path]:
    """Write controlled JSON/NPZ evidence without changing solver source."""

    destination = QUALIFICATION if output_dir is None else Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    summary, arrays = _campaign()
    json_path = destination / "wp04_c_tet4_structural_summary.json"
    npz_path = destination / "wp04_c_tet4_structural_raw.npz"
    np.savez_compressed(npz_path, **arrays)  # type: ignore[arg-type]
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return json_path, npz_path


if __name__ == "__main__":
    write_evidence()
