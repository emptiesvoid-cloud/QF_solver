"""Execute the frozen WP04-D HEX8 structural qualification campaign.

This is qualification infrastructure only.  It deliberately uses the
existing HEX8 Total-Lagrangian assembly and the owner-approved C2R6 nonlinear
route; it does not modify mechanics or solver production code.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from time import perf_counter, process_time
from typing import Any

import numpy as np
from scipy.sparse.linalg import spsolve


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUTPUT = ROOT / "qualification" / "0_2_9" / "wp04d"
CONTRACT_PATH = OUTPUT / "hex8_contract.json"
FORENSICS_ROOT = Path(tempfile.gettempdir()) / "qf_solver_029_wp04d_forensics"

LENGTH = 4.0
HEIGHT = 0.5
DEPTH = 0.5
YOUNG_MODULUS = 1.0e6
POISSON_RATIO = 0.30
TOTAL_RESULTANT = np.asarray([0.0, -50.0, 0.0], dtype=float)
SURFACE_TRACTION = TOTAL_RESULTANT / (HEIGHT * DEPTH)
MESHES: dict[str, tuple[int, int, int]] = {
    "H1": (16, 8, 8),
    "H2": (24, 12, 12),
    "H3": (32, 16, 16),
}
SMALL_LOAD_MULTIPLIERS = (0.1, 0.01, 0.001)
INCREMENTS = 12
NEWTON_TOLERANCE = 1.0e-10
MAX_NEWTON_ITERATIONS = 40
MINRES_RTOL = 1.0e-11
MINRES_ATOL = 1.0e-14
MINRES_MAXITER = 10_000
LINEAR_BACKWARD_ERROR_TOLERANCE = 1.0e-10
ENVELOPE_MIN_DET_F = 0.20
ENVELOPE_STRETCH_MIN = 0.75
ENVELOPE_STRETCH_MAX = 1.30
ENVELOPE_MAX_GREEN_NORM = 0.30


def _slug(label: str) -> str:
    return label.lower().replace("-", "_").replace(".", "p")


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int, float)):
        if isinstance(value, float) and not np.isfinite(value):
            return None
        return value
    if isinstance(value, np.generic):
        return _jsonable(value.item())
    if isinstance(value, np.ndarray):
        return [_jsonable(item) for item in value.tolist()]
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    temporary.write_text(
        json.dumps(_jsonable(payload), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _percentile(values: Sequence[int | float], percentile: float) -> float | None:
    if not values:
        return None
    return float(np.percentile(np.asarray(values, dtype=float), percentile, method="linear"))


class _PeakMemorySampler:
    def __init__(self) -> None:
        self.stop = threading.Event()
        self.thread: threading.Thread | None = None
        self.peak_rss: int | None = None
        self.peak_private: int | None = None

    def _sample(self) -> None:
        from solveur.core.nonlinear.telemetry import process_memory_bytes

        while not self.stop.is_set():
            rss, private = process_memory_bytes()
            if rss is not None:
                self.peak_rss = max(self.peak_rss or 0, int(rss))
            if private is not None:
                self.peak_private = max(self.peak_private or 0, int(private))
            self.stop.wait(0.10)

    def __enter__(self) -> "_PeakMemorySampler":
        self.thread = threading.Thread(target=self._sample, name="wp04d-memory", daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop.set()
        if self.thread is not None:
            self.thread.join(timeout=2.0)


class _FailureSystemCapture:
    """Capture at most one failed reduced system outside the repository."""

    def __init__(self, label: str) -> None:
        self.label = label
        self.pending: tuple[Any, np.ndarray, dict[str, Any]] | None = None
        self.written: dict[str, Any] | None = None

    def hold(self, matrix: Any, rhs: np.ndarray, diagnostics: Mapping[str, Any]) -> None:
        if self.pending is None and self.written is None:
            self.pending = (matrix.copy(), np.array(rhs, dtype=float, copy=True), dict(diagnostics))

    def flush(self, context: Mapping[str, Any]) -> dict[str, Any] | None:
        if self.pending is None or self.written is not None:
            return self.written
        matrix, rhs, diagnostics = self.pending
        FORENSICS_ROOT.mkdir(parents=True, exist_ok=True)
        step = context.get("load_step", diagnostics.get("load_step", "unknown"))
        iteration = context.get("newton_iteration", diagnostics.get("newton_iteration", "unknown"))
        target = FORENSICS_ROOT / f"{_slug(self.label)}_linear_failure_step{step}_iter{iteration}.npz"
        np.savez_compressed(
            target,
            data=np.asarray(matrix.data),
            indices=np.asarray(matrix.indices),
            indptr=np.asarray(matrix.indptr),
            shape=np.asarray(matrix.shape, dtype=np.int64),
            rhs=rhs,
        )
        self.written = {
            "label": self.label,
            "load_step": step,
            "newton_iteration": iteration,
            "path": str(target),
            "size_bytes": int(target.stat().st_size),
            "sha256": _sha256(target),
            "shape": [int(item) for item in matrix.shape],
            "nnz": int(matrix.nnz),
            "linear_method": diagnostics.get("linear_method"),
            "linear_backend": diagnostics.get("linear_backend"),
        }
        self.pending = None
        return self.written


def _mesh(cells: tuple[int, int, int]) -> tuple[np.ndarray, np.ndarray]:
    nx, ny, nz = cells
    nodes = np.stack(
        np.meshgrid(
            np.linspace(0.0, LENGTH, nx + 1),
            np.linspace(0.0, HEIGHT, ny + 1),
            np.linspace(0.0, DEPTH, nz + 1),
            indexing="ij",
        ),
        axis=-1,
    ).reshape(-1, 3)

    def node(i: int, j: int, k: int) -> int:
        return i * (ny + 1) * (nz + 1) + j * (nz + 1) + k

    elements: list[list[int]] = []
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                # Matches Hex8Element.node_signs exactly.
                cube = [
                    node(i, j, k),
                    node(i + 1, j, k),
                    node(i + 1, j + 1, k),
                    node(i, j + 1, k),
                    node(i, j, k + 1),
                    node(i + 1, j, k + 1),
                    node(i + 1, j + 1, k + 1),
                    node(i, j + 1, k + 1),
                ]
                elements.append(cube)
    return np.asarray(nodes, dtype=np.float64), np.asarray(elements, dtype=np.int64)


def _consistent_q4_face_load(nodes: np.ndarray, cells: tuple[int, int, int]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Integrate constant traction over every x=L Q4 face consistently."""

    nx, ny, nz = cells
    hy = HEIGHT / ny
    hz = DEPTH / nz
    external = np.zeros(nodes.shape[0] * 3, dtype=np.float64)

    def node(i: int, j: int, k: int) -> int:
        return i * (ny + 1) * (nz + 1) + j * (nz + 1) + k

    # x=L local HEX8 face is (4,5,6,7).  For a rectangular Q4 face the
    # consistent constant-traction integral assigns one quarter to each corner.
    face_weight = SURFACE_TRACTION * (hy * hz / 4.0)
    for j in range(ny):
        for k in range(nz):
            face_nodes = (
                node(nx, j, k),
                node(nx, j, k + 1),
                node(nx, j + 1, k + 1),
                node(nx, j + 1, k),
            )
            for index in face_nodes:
                external[3 * index : 3 * index + 3] += face_weight
    loaded = np.flatnonzero(np.linalg.norm(external.reshape(-1, 3), axis=1) > 0.0)
    return external, loaded, face_weight


def _reference_mesh_metrics(nodes: np.ndarray, elements: np.ndarray, assembly: Any) -> dict[str, Any]:
    from solveur.elements.solid.hex8 import Hex8Element

    gauss_determinants: list[float] = []
    scaled_jacobians: list[float] = []
    element_volumes: list[float] = []
    for element_nodes in nodes[elements]:
        volume = 0.0
        for point, weight, _, determinant in assembly._reference_data[len(element_volumes)]:
            jacobian = Hex8Element.jacobian(element_nodes, point)
            column_product = float(np.prod(np.linalg.norm(jacobian, axis=0)))
            scaled = float(determinant / column_product) if column_product > 0.0 else float("nan")
            gauss_determinants.append(float(determinant))
            scaled_jacobians.append(scaled)
            volume += float(weight) * float(determinant)
        element_volumes.append(volume)
    return {
        "nodes": int(nodes.shape[0]),
        "elements": int(elements.shape[0]),
        "dofs": int(assembly.ndof),
        "element_volume_minimum": float(np.min(element_volumes)),
        "element_volume_maximum": float(np.max(element_volumes)),
        "element_volume_ratio": max(element_volumes) / min(element_volumes),
        "reference_gauss_jacobian_minimum": float(np.min(gauss_determinants)),
        "reference_gauss_jacobian_maximum": float(np.max(gauss_determinants)),
        "minimum_scaled_jacobian": float(np.min(scaled_jacobians)),
        "orientation_failures": int(np.count_nonzero(np.asarray(gauss_determinants) <= 0.0)),
        "element_volumes": np.asarray(element_volumes, dtype=np.float64),
        "reference_gauss_determinants": np.asarray(gauss_determinants, dtype=np.float64).reshape(-1, 8),
        "reference_scaled_jacobians": np.asarray(scaled_jacobians, dtype=np.float64).reshape(-1, 8),
    }


def _case(label: str) -> dict[str, Any]:
    from solveur.elements.solid.hex8_total_lagrangian_batch import TotalLagrangianHex8Assembly
    from solveur.materials.solid import SolidMaterial

    cells = MESHES[label]
    nodes, elements = _mesh(cells)
    material = SolidMaterial(E=YOUNG_MODULUS, nu=POISSON_RATIO)
    assembly = TotalLagrangianHex8Assembly(nodes, elements, material)
    external, loaded_nodes, face_weight = _consistent_q4_face_load(nodes, cells)
    fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    fixed = (3 * fixed_nodes[:, None] + np.arange(3)).reshape(-1).astype(np.int64)
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
        raise AssertionError(f"Frozen HEX8 stress region has no contributing elements for {label}.")
    reference = _reference_mesh_metrics(nodes, elements, assembly)
    return {
        "label": label,
        "cells": cells,
        "nodes": nodes,
        "elements": elements,
        "assembly": assembly,
        "external": external,
        "fixed": fixed,
        "fixed_nodes": fixed_nodes,
        "loaded_nodes": loaded_nodes,
        "face_weight": face_weight,
        "centroid": centroid,
        "stress_mask": stress_mask,
        "reference": reference,
    }


def _load_checks(case: Mapping[str, Any]) -> dict[str, Any]:
    nodes = np.asarray(case["nodes"], dtype=float)
    external = np.asarray(case["external"], dtype=float).reshape(-1, 3)
    resultant = np.sum(external, axis=0)
    moment = np.sum(np.cross(nodes, external), axis=0)
    return {
        "resultant": resultant.tolist(),
        "resultant_error": float(np.linalg.norm(resultant - TOTAL_RESULTANT)),
        "resultant_relative_error": float(np.linalg.norm(resultant - TOTAL_RESULTANT) / max(float(np.linalg.norm(TOTAL_RESULTANT)), 1.0e-12)),
        "reference_moment": moment.tolist(),
        "face_area": HEIGHT * DEPTH,
        "traction": SURFACE_TRACTION.tolist(),
        "q4_face_weight_per_corner": np.asarray(case["face_weight"], dtype=float).tolist(),
        "loaded_node_count": int(np.count_nonzero(np.linalg.norm(external, axis=1) > 0.0)),
        "equal_share_used": False,
    }


def _free_dofs(ndof: int, fixed: np.ndarray) -> np.ndarray:
    return np.setdiff1d(np.arange(ndof, dtype=np.int64), fixed)


def _equilibrium(case: Mapping[str, Any], displacement: np.ndarray, internal: np.ndarray) -> dict[str, Any]:
    fixed = np.asarray(case["fixed"], dtype=np.int64)
    external = np.asarray(case["external"], dtype=float)
    reactions = np.zeros_like(internal)
    reactions[fixed] = internal[fixed] - external[fixed]
    physical_nodes = np.asarray(case["nodes"], dtype=float) + np.asarray(displacement).reshape(-1, 3)
    external_vectors = external.reshape(-1, 3)
    reaction_vectors = reactions.reshape(-1, 3)
    external_resultant = np.sum(external_vectors, axis=0)
    reaction_resultant = np.sum(reaction_vectors, axis=0)
    external_moment = np.sum(np.cross(physical_nodes, external_vectors), axis=0)
    reaction_moment = np.sum(np.cross(physical_nodes, reaction_vectors), axis=0)
    force_imbalance = external_resultant + reaction_resultant
    moment_imbalance = external_moment + reaction_moment
    force_scale = max(float(np.linalg.norm(external_resultant)), float(np.linalg.norm(reaction_resultant)), 1.0)
    moment_scale = max(float(np.linalg.norm(external_moment)), float(np.linalg.norm(reaction_moment)), 1.0)
    return {
        "external_resultant": external_resultant.tolist(),
        "reaction_resultant": reaction_resultant.tolist(),
        "force_imbalance": force_imbalance.tolist(),
        "moment_imbalance": moment_imbalance.tolist(),
        "external_moment": external_moment.tolist(),
        "reaction_moment": reaction_moment.tolist(),
        "force_relative_error": float(np.linalg.norm(force_imbalance) / force_scale),
        "moment_relative_error": float(np.linalg.norm(moment_imbalance) / moment_scale),
        "reactions": reactions,
    }


def _gauss_envelope(case: Mapping[str, Any], displacement: np.ndarray) -> dict[str, np.ndarray]:
    assembly = case["assembly"]
    local_displacements = assembly._local_displacements(np.asarray(displacement, dtype=float))
    determinant_rows: list[list[float]] = []
    stretch_rows: list[list[np.ndarray]] = []
    green_rows: list[list[float]] = []
    identity = np.eye(3)
    for element_index, local_u in enumerate(local_displacements):
        determinants: list[float] = []
        stretches: list[np.ndarray] = []
        green_norms: list[float] = []
        for _, _, gradients, _ in assembly._reference_data[element_index]:
            deformation = assembly._deformation_gradient(local_u, gradients)
            green = 0.5 * (deformation.T @ deformation - identity)
            determinants.append(float(np.linalg.det(deformation)))
            stretches.append(np.linalg.svd(deformation, compute_uv=False))
            green_norms.append(float(np.linalg.norm(green)))
        determinant_rows.append(determinants)
        stretch_rows.append(stretches)
        green_rows.append(green_norms)
    return {
        "det_f": np.asarray(determinant_rows, dtype=np.float64),
        "principal_stretches": np.asarray(stretch_rows, dtype=np.float64),
        "green_norm": np.asarray(green_rows, dtype=np.float64),
    }


def _observables(case: Mapping[str, Any], displacement: np.ndarray, internal: np.ndarray) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    assembly = case["assembly"]
    state_fields = assembly.element_states(np.asarray(displacement, dtype=float))
    envelope = _gauss_envelope(case, displacement)
    volumes = np.asarray(case["reference"]["element_volumes"], dtype=float)
    mask = np.asarray(case["stress_mask"], dtype=bool)
    sigma_xx = np.asarray(state_fields["cauchy_stress"], dtype=float)[mask, 0, 0]
    sampled_volumes = volumes[mask]
    node_displacement = np.asarray(displacement).reshape(-1, 3)
    loaded_average = np.mean(node_displacement[np.asarray(case["loaded_nodes"])], axis=0)
    equilibrium = _equilibrium(case, displacement, internal)
    principal = envelope["principal_stretches"]
    det_f = envelope["det_f"]
    green_norm = envelope["green_norm"]
    observed = {
        "tip_displacement": float(loaded_average[1]),
        "loaded_face_average_displacement": loaded_average.tolist(),
        "strain_energy": float(assembly.strain_energy(displacement)),
        "representative_stress_sigma_xx": float(np.dot(sampled_volumes, sigma_xx) / np.sum(sampled_volumes)),
        "stress_contributing_elements": int(np.count_nonzero(mask)),
        "stress_contributing_volume": float(np.sum(sampled_volumes)),
        "equilibrium": {key: value for key, value in equilibrium.items() if key != "reactions"},
        "minimum_det_f": float(np.min(det_f)),
        "minimum_principal_stretch": float(np.min(principal)),
        "maximum_principal_stretch": float(np.max(principal)),
        "maximum_green_lagrange_norm": float(np.max(green_norm)),
        "envelope_status": bool(
            np.all(np.isfinite(det_f))
            and np.all(np.isfinite(principal))
            and np.all(np.isfinite(green_norm))
            and float(np.min(det_f)) >= ENVELOPE_MIN_DET_F
            and float(np.min(principal)) >= ENVELOPE_STRETCH_MIN
            and float(np.max(principal)) <= ENVELOPE_STRETCH_MAX
            and float(np.max(green_norm)) <= ENVELOPE_MAX_GREEN_NORM
        ),
    }
    arrays = {
        "displacement": np.asarray(displacement, dtype=np.float64),
        "internal_force": np.asarray(internal, dtype=np.float64),
        "reaction_force": np.asarray(equilibrium["reactions"], dtype=np.float64),
        "det_f": det_f,
        "principal_stretches": principal,
        "green_lagrange_norm": green_norm,
    }
    return observed, arrays


def _floor_evidence(case: Mapping[str, Any], state: Any, response: Any, external: np.ndarray, free: np.ndarray, factor: float) -> Mapping[str, Any]:
    internal = np.asarray(response.internal_force, dtype=float)
    fixed = np.setdiff1d(np.arange(internal.size, dtype=np.int64), np.asarray(free, dtype=np.int64))
    target = float(factor) * np.asarray(external, dtype=float)
    reactions = np.zeros_like(internal)
    reactions[fixed] = internal[fixed] - target[fixed]
    physical_nodes = np.asarray(case["nodes"], dtype=float) + np.asarray(state.displacement).reshape(-1, 3)
    target_vectors = target.reshape(-1, 3)
    reaction_vectors = reactions.reshape(-1, 3)
    force = np.sum(target_vectors, axis=0) + np.sum(reaction_vectors, axis=0)
    moment = np.sum(np.cross(physical_nodes, target_vectors), axis=0) + np.sum(
        np.cross(physical_nodes, reaction_vectors), axis=0
    )
    force_scale = max(float(np.linalg.norm(np.sum(target_vectors, axis=0))), float(np.linalg.norm(np.sum(reaction_vectors, axis=0))), 1.0)
    moment_scale = max(float(np.linalg.norm(np.sum(np.cross(physical_nodes, target_vectors), axis=0))), float(np.linalg.norm(np.sum(np.cross(physical_nodes, reaction_vectors), axis=0))), 1.0)
    fields = case["assembly"].element_states(np.asarray(state.displacement, dtype=float))
    deformation = np.asarray(fields["deformation_gradient"], dtype=float)
    stretches = np.linalg.svd(deformation, compute_uv=False)
    green = np.asarray(fields["green_lagrange_strain"], dtype=float)
    det_f = np.asarray(fields["det_f"], dtype=float)
    finite = bool(
        np.all(np.isfinite(deformation))
        and np.all(np.isfinite(stretches))
        and np.all(np.isfinite(green))
        and np.all(np.isfinite(det_f))
    )
    valid = finite and bool(
        np.min(det_f) >= ENVELOPE_MIN_DET_F
        and np.min(stretches) >= ENVELOPE_STRETCH_MIN
        and np.max(stretches) <= ENVELOPE_STRETCH_MAX
        and np.max(np.linalg.norm(green, axis=(1, 2))) <= ENVELOPE_MAX_GREEN_NORM
    )
    return {
        "state_valid": valid,
        "force_equilibrium": float(np.linalg.norm(force) / force_scale),
        "moment_equilibrium": float(np.linalg.norm(moment) / moment_scale),
        "minimum_det_f": float(np.min(det_f)),
        "minimum_principal_stretch": float(np.min(stretches)),
        "maximum_principal_stretch": float(np.max(stretches)),
        "maximum_green_lagrange_norm": float(np.max(np.linalg.norm(green, axis=(1, 2)))),
    }


def _aggregate(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    iterations = [event for event in events if event.get("event") == "ITERATION"]
    solves = [
        event for event in iterations
        if event.get("linear_method") is not None or event.get("status") == "LINEAR_FAILED"
    ]
    krylov = [
        int(event["krylov_iterations"])
        for event in solves
        if isinstance(event.get("krylov_iterations"), (int, float))
    ]
    solve_times = [
        float(event["linear_solve_time_s"])
        for event in solves
        if isinstance(event.get("linear_solve_time_s"), (int, float))
    ]
    etas = [
        float(event["linear_backward_error_eta_inf"])
        for event in solves
        if isinstance(event.get("linear_backward_error_eta_inf"), (int, float))
        and np.isfinite(float(event["linear_backward_error_eta_inf"]))
    ]
    raw = [
        float(event["linear_relative_residual"])
        for event in solves
        if isinstance(event.get("linear_relative_residual"), (int, float))
        and np.isfinite(float(event["linear_relative_residual"]))
    ]
    accepted = [event for event in events if event.get("event") == "STEP_ACCEPTED"]
    floors = [event for event in iterations if event.get("termination_classification") == "CONVERGED_NUMERICAL_FLOOR"]
    primary = [event for event in iterations if event.get("termination_classification") == "CONVERGED_RESIDUAL"]
    return {
        "accepted_step_count": len(accepted),
        "accepted_load_factors": [event.get("target_load_factor") for event in accepted],
        "total_newton_iterations": len(iterations),
        "total_linear_solves": len(solves),
        "termination_counts": {"CONVERGED_RESIDUAL": len(primary), "CONVERGED_NUMERICAL_FLOOR": len(floors)},
        "krylov_iterations": {
            "min": min(krylov) if krylov else None,
            "median": float(np.median(krylov)) if krylov else None,
            "p95": _percentile(krylov, 95.0),
            "max": max(krylov) if krylov else None,
            "total": int(sum(krylov)),
        },
        "linear_solve_time_s": {
            "total": float(sum(solve_times)),
            "median": float(np.median(solve_times)) if solve_times else None,
            "p95": _percentile(solve_times, 95.0),
            "max": max(solve_times) if solve_times else None,
        },
        "max_eta_inf": max(etas) if etas else None,
        "max_raw_linear_relative_residual": max(raw) if raw else None,
        "fallback_count": int(sum(1 for event in solves if bool(event.get("fallback_used")))),
        "line_search_alphas": [event.get("line_search_alpha") for event in iterations],
    }


def _route_options() -> Any:
    from solveur.core.nonlinear.robustness import NonlinearRobustnessOptions

    options = NonlinearRobustnessOptions(
        linear_solver="minres",
        linear_preconditioner="jacobi",
        linear_rtol=MINRES_RTOL,
        linear_atol=MINRES_ATOL,
        linear_maxiter=MINRES_MAXITER,
        linear_residual_tolerance=LINEAR_BACKWARD_ERROR_TOLERANCE,
        linear_backward_error_tolerance=LINEAR_BACKWARD_ERROR_TOLERANCE,
        linear_direct_fallback=False,
        line_search="existing",
        floor_aware_termination=True,
    )
    options.validate()
    return options


def _run_nonlinear(
    case: Mapping[str, Any],
    label: str,
    external: np.ndarray,
    output: Path,
    *,
    write_raw: bool = True,
) -> dict[str, Any]:
    from solveur.core.analyses.geometric_nonlinear import _newton_dead_load
    from solveur.core.errors import NumericalConvergenceError
    from solveur.core.nonlinear.linear_solver import NonlinearLinearSolverAdapter
    from solveur.core.nonlinear.state import NonlinearState
    from solveur.core.nonlinear.telemetry import JsonlNonlinearTelemetry, process_memory_bytes

    output.mkdir(parents=True, exist_ok=True)
    slug = _slug(label)
    status_path = output / f"{slug}_status.json"
    result_path = output / f"{slug}_result.json"
    telemetry_path = output / f"{slug}_telemetry.jsonl"
    raw_path = output / f"{slug}_raw.npz"
    started_wall = perf_counter()
    started_cpu = process_time()
    started_timestamp = datetime.now(timezone.utc).isoformat()
    cells = tuple(int(value) for value in case["cells"])
    status: dict[str, Any] = {
        "label": label,
        "mesh_cells": list(cells),
        "status": "RUNNING",
        "pid": os.getpid(),
        "load_step": 0,
        "Newton_iteration": 0,
        "latest_eta_inf": None,
        "latest_Krylov_iterations": None,
        "latest_linear_solve_time": None,
        "latest_line_search_alpha": None,
        "RSS": None,
        "private_memory": None,
        "elapsed_wall_time": 0.0,
        "last_update_timestamp": started_timestamp,
        "started_timestamp": started_timestamp,
    }
    _write_json(status_path, status)
    events: list[dict[str, Any]] = []
    accepted_states: list[Any] = []
    failure_capture = _FailureSystemCapture(label)
    original_solve = NonlinearLinearSolverAdapter.solve
    outcome = "PASS"
    failure: dict[str, Any] | None = None
    observed: dict[str, Any] | None = None
    raw_arrays: dict[str, np.ndarray] = {}
    diagnostics: dict[str, Any] | None = None
    summary_steps: list[dict[str, Any]] = []
    peak_rss: int | None = None
    peak_private: int | None = None

    def wrapped_solve(self: Any, matrix: Any, rhs: np.ndarray, **kwargs: Any) -> Any:
        try:
            return original_solve(self, matrix, rhs, **kwargs)
        except NumericalConvergenceError as exc:
            failure_capture.hold(matrix, rhs, exc.diagnostics)
            raise

    NonlinearLinearSolverAdapter.solve = wrapped_solve
    try:
        def accepted(_step: int, state: Any) -> None:
            accepted_states.append(state.detached_copy())

        def observe(event: Mapping[str, object]) -> None:
            enriched: dict[str, Any] = {
                **dict(event),
                "case": label,
                "mesh": list(cells),
                "phase": "WP04-D",
            }
            events.append(_jsonable(enriched))
            json_writer(enriched)
            rss, private = process_memory_bytes()
            status.update(
                {
                    "load_step": enriched.get("load_step", status["load_step"]),
                    "Newton_iteration": enriched.get("newton_iteration", status["Newton_iteration"]),
                    "latest_eta_inf": enriched.get("linear_backward_error_eta_inf", status["latest_eta_inf"]),
                    "latest_Krylov_iterations": enriched.get("krylov_iterations", status["latest_Krylov_iterations"]),
                    "latest_linear_solve_time": enriched.get("linear_solve_time_s", status["latest_linear_solve_time"]),
                    "latest_line_search_alpha": enriched.get("line_search_alpha", status["latest_line_search_alpha"]),
                    "RSS": rss,
                    "private_memory": private,
                    "elapsed_wall_time": perf_counter() - started_wall,
                    "last_update_timestamp": datetime.now(timezone.utc).isoformat(),
                    "last_event": enriched.get("event"),
                    "last_event_status": enriched.get("status"),
                }
            )
            if enriched.get("status") == "LINEAR_FAILED":
                failure_capture.flush(enriched)
            _write_json(status_path, status)

        with _PeakMemorySampler() as sampler:
            with JsonlNonlinearTelemetry(telemetry_path) as json_writer:
                try:
                    displacement, diagnostics = _newton_dead_load(
                        case["assembly"],
                        np.asarray(external, dtype=float),
                        np.asarray(case["fixed"], dtype=np.int64),
                        increments=INCREMENTS,
                        tolerance=NEWTON_TOLERANCE,
                        max_iterations=MAX_NEWTON_ITERATIONS,
                        robustness_options=_route_options(),
                        initial_state=NonlinearState(
                            np.zeros(case["assembly"].ndof, dtype=float),
                            load_factor=0.0,
                            continuation_state={"accepted_step": 0},
                        ),
                        target_load_factors=[step / INCREMENTS for step in range(1, INCREMENTS + 1)],
                        accepted_state_callback=accepted,
                        telemetry_observer=observe,
                        floor_aware_evidence=lambda state, response, load, free, factor: _floor_evidence(
                            case, state, response, load, free, factor
                        ),
                    )
                    internal, _ = case["assembly"].assemble(displacement, tangent_required=False)
                    observed, raw_arrays = _observables(case, displacement, internal)
                except NumericalConvergenceError as exc:
                    outcome = "NUMERICAL_FAILURE"
                    failure = {
                        "reason": exc.reason.value if hasattr(exc.reason, "value") else str(exc.reason),
                        "message": str(exc),
                        "diagnostics": _jsonable(exc.diagnostics),
                    }
                    failure_event = {
                        "event": "SOLVE_FAILED",
                        "case": label,
                        "mesh": list(cells),
                        "status": "FAILED",
                        "reason": failure["reason"],
                        "load_step": exc.diagnostics.get("load_step"),
                        "newton_iteration": exc.diagnostics.get("newton_iteration"),
                    }
                    events.append(failure_event)
                    json_writer(failure_event)
                    failure_capture.flush(exc.diagnostics)
                except MemoryError as exc:
                    outcome = "RESOURCE_LIMIT"
                    failure = {"reason": "MemoryError", "message": str(exc)}
                except OSError as exc:
                    outcome = "RESOURCE_LIMIT"
                    failure = {"reason": type(exc).__name__, "message": str(exc)}
                except Exception as exc:  # pragma: no cover - unattended campaign guard
                    outcome = "RUNNER_ERROR"
                    failure = {"reason": type(exc).__name__, "message": str(exc)}
            peak_rss = sampler.peak_rss
            peak_private = sampler.peak_private
    finally:
        NonlinearLinearSolverAdapter.solve = original_solve

    rss, private = process_memory_bytes()
    peak_rss = max(peak_rss or 0, rss or 0) or None
    peak_private = max(peak_private or 0, private or 0) or None
    if outcome == "PASS" and diagnostics is not None and observed is not None:
        rows = diagnostics.get("increments", [])
        if not isinstance(rows, list) or len(rows) != INCREMENTS or len(accepted_states) != INCREMENTS:
            outcome = "RUNNER_ERROR"
            failure = {"reason": "INCOMPLETE_ACCEPTED_PATH", "message": "Expected twelve accepted increments."}
        else:
            accepted_displacements = np.stack([np.asarray(state.displacement, dtype=float) for state in accepted_states])
            accepted_factors = np.asarray([float(state.load_factor) for state in accepted_states], dtype=np.float64)
            accepted_digests = [state.digest for state in accepted_states]
            raw_arrays.update(
                {
                    "nodes": np.asarray(case["nodes"], dtype=np.float64),
                    "elements": np.asarray(case["elements"], dtype=np.int64),
                    "external": np.asarray(external, dtype=np.float64),
                    "fixed": np.asarray(case["fixed"], dtype=np.int64),
                    "loaded_nodes": np.asarray(case["loaded_nodes"], dtype=np.int64),
                    "centroid": np.asarray(case["centroid"], dtype=np.float64),
                    "stress_mask": np.asarray(case["stress_mask"], dtype=np.int8),
                    "reference_element_volumes": np.asarray(case["reference"]["element_volumes"], dtype=np.float64),
                    "reference_gauss_determinants": np.asarray(case["reference"]["reference_gauss_determinants"], dtype=np.float64),
                    "reference_scaled_jacobians": np.asarray(case["reference"]["reference_scaled_jacobians"], dtype=np.float64),
                    "accepted_displacements": accepted_displacements,
                    "accepted_load_factors": accepted_factors,
                }
            )
            increment_rows = [
                {
                    "step": int(row["increment"]),
                    "load_factor": float(row["load_factor"]),
                    "iterations": int(row["iterations"]),
                    "relative_residual": float(row["relative_residual"]),
                    "termination_classification": row.get("termination_classification"),
                    "line_search_iterations": int(row.get("line_search_iterations", 0)),
                    "last_correction_norm": float(row.get("last_correction_norm", 0.0)),
                    "residual_initial": float(row.get("residual_initial", 0.0)),
                    "residual_final": float(row.get("residual_final", 0.0)),
                }
                for row in rows
            ]
            summary_steps = increment_rows
    else:
        accepted_digests = [state.digest for state in accepted_states]
        accepted_factors = np.asarray([float(state.load_factor) for state in accepted_states], dtype=np.float64)
        accepted_displacements = (
            np.stack([np.asarray(state.displacement, dtype=float) for state in accepted_states])
            if accepted_states
            else np.empty((0, case["assembly"].ndof), dtype=np.float64)
        )
        raw_arrays.update(
            {
                "nodes": np.asarray(case["nodes"], dtype=np.float64),
                "elements": np.asarray(case["elements"], dtype=np.int64),
                "external": np.asarray(external, dtype=np.float64),
                "fixed": np.asarray(case["fixed"], dtype=np.int64),
                "loaded_nodes": np.asarray(case["loaded_nodes"], dtype=np.int64),
                "accepted_displacements": accepted_displacements,
                "accepted_load_factors": accepted_factors,
            }
        )
        accepted_digests = [state.digest for state in accepted_states]
        summary_steps = []

    raw_info: dict[str, Any] | None = None
    if write_raw and raw_arrays:
        np.savez_compressed(raw_path, **raw_arrays)  # type: ignore[arg-type]
        raw_info = {"path": str(raw_path), "size_bytes": int(raw_path.stat().st_size), "sha256": _sha256(raw_path), "array_names": sorted(raw_arrays)}

    performance = _aggregate(events)
    terminal_classification = "COMPLETED" if outcome == "PASS" else (failure or {}).get("reason", outcome)
    result: dict[str, Any] = {
        "schema_version": 1,
        "record_id": f"QF-SOLVER-0.2.9-WP04-D-{slug.upper()}",
        "work_package": "WP04-D",
        "gate": "G04-11",
        "label": label,
        "mesh_cells": list(cells),
        "mesh": {key: value for key, value in case["reference"].items() if not isinstance(value, np.ndarray)},
        "status": outcome,
        "process_end_reason": terminal_classification,
        "route": {
            "linear_solver": "MINRES",
            "preconditioner": "Jacobi",
            "rtol": MINRES_RTOL,
            "atol": MINRES_ATOL,
            "maxiter": MINRES_MAXITER,
            "direct_fallback": False,
            "line_search": "existing/enabled",
            "floor_aware_termination": True,
            "newton_tolerance": NEWTON_TOLERANCE,
            "increments": INCREMENTS,
        },
        "frozen_contract": str(CONTRACT_PATH.relative_to(ROOT)).replace("\\", "/"),
        "execution_sha": _git_sha(),
        "started_timestamp": started_timestamp,
        "ended_timestamp": datetime.now(timezone.utc).isoformat(),
        "wall_time_s": perf_counter() - started_wall,
        "cpu_time_s": process_time() - started_cpu,
        "status_path": str(status_path.relative_to(ROOT)).replace("\\", "/"),
        "telemetry_path": str(telemetry_path.relative_to(ROOT)).replace("\\", "/"),
        "telemetry_event_count": len(events),
        "accepted_load_factors": accepted_factors.tolist(),
        "accepted_state_digests": accepted_digests,
        "termination_classifications": [row.get("termination_classification") for row in summary_steps],
        "step_diagnostics": summary_steps,
        "performance": {
            **performance,
            "peak_rss_process": peak_rss,
            "peak_private_or_uss_process": peak_private,
            "telemetry_sample_peak_rss": max(
                [int(event["RSS_bytes"]) for event in events if isinstance(event.get("RSS_bytes"), (int, float))],
                default=None,
            ),
            "telemetry_sample_peak_private": max(
                [int(event["private_or_USS_bytes"]) for event in events if isinstance(event.get("private_or_USS_bytes"), (int, float))],
                default=None,
            ),
        },
        "observables": observed,
        "failure": failure,
        "failure_system_capture": failure_capture.written,
        "raw_npz": raw_info,
        "load_check": _load_checks(case),
        "reference_mesh_quality": {
            key: value
            for key, value in case["reference"].items()
            if not isinstance(value, np.ndarray)
        },
        "full_test_suite_run": False,
        "production_mechanics_changed": False,
        "maturity_changed": False,
    }
    _write_json(result_path, result)
    status.update(
        {
            "status": outcome,
            "elapsed_wall_time": perf_counter() - started_wall,
            "last_update_timestamp": datetime.now(timezone.utc).isoformat(),
            "terminal_reason": terminal_classification,
            "result_path": str(result_path.relative_to(ROOT)).replace("\\", "/"),
        }
    )
    _write_json(status_path, status)
    return result


def _relative_scalar(value: float, reference: float) -> float:
    return float(abs(float(value) - float(reference)) / max(abs(float(value)), abs(float(reference)), 1.0e-12))


def _relative_vector(value: Sequence[float], reference: Sequence[float]) -> float:
    current = np.asarray(value, dtype=float)
    baseline = np.asarray(reference, dtype=float)
    return float(
        np.linalg.norm(current - baseline)
        / max(float(np.linalg.norm(current)), float(np.linalg.norm(baseline)), 1.0e-12)
    )


def _linear_reference(case: Mapping[str, Any], external: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    zero = np.zeros(case["assembly"].ndof, dtype=np.float64)
    _, tangent = case["assembly"].assemble(zero, tangent_required=True)
    if tangent is None:
        raise AssertionError("HEX8 zero-state tangent is required for the linear reference.")
    free = _free_dofs(case["assembly"].ndof, np.asarray(case["fixed"], dtype=np.int64))
    displacement = np.zeros(case["assembly"].ndof, dtype=np.float64)
    displacement[free] = np.asarray(spsolve(tangent[free, :][:, free], np.asarray(external)[free]), dtype=float)
    linear_internal = np.asarray(tangent @ displacement, dtype=float)
    equilibrium = _equilibrium(case, displacement, linear_internal)
    return displacement, {
        "equilibrium": {key: value for key, value in equilibrium.items() if key != "reactions"},
        "strain_energy": float(0.5 * displacement @ linear_internal),
    }


def _run_small_load_checks(case: Mapping[str, Any], output: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for multiplier in SMALL_LOAD_MULTIPLIERS:
        label = f"H1-small-{multiplier:g}"
        external = np.asarray(case["external"], dtype=float) * multiplier
        linear_displacement, linear_observed = _linear_reference(case, external)
        nonlinear = _run_nonlinear(case, label, external, output)
        if nonlinear.get("status") == "PASS" and nonlinear.get("observables") is not None:
            nonlinear_displacement = np.asarray(nonlinear.get("raw_npz"), dtype=object) if False else None
            raw_path = ROOT / str(nonlinear["raw_npz"]["path"])
            with np.load(raw_path, allow_pickle=False) as raw:
                nonlinear_displacement = np.asarray(raw["displacement"], dtype=float)
            nonlinear_reaction = nonlinear["observables"]["equilibrium"]["reaction_resultant"]
            linear_internal, _ = case["assembly"].assemble(linear_displacement, tangent_required=False)
            linear_eq = _equilibrium(case, linear_displacement, linear_internal)
            row = {
                "multiplier": multiplier,
                "status": "PASS",
                "displacement_relative_error": float(
                    np.linalg.norm(nonlinear_displacement - linear_displacement)
                    / max(float(np.linalg.norm(linear_displacement)), 1.0e-12)
                ),
                "reaction_relative_error": _relative_vector(nonlinear_reaction, linear_eq["reaction_resultant"]),
                "nonlinear_result": nonlinear["status_path"],
                "linear_strain_energy": linear_observed["strain_energy"],
            }
            row["gate_status"] = bool(
                row["displacement_relative_error"] <= 1.0e-4
                and row["reaction_relative_error"] <= 1.0e-4
            )
        else:
            row = {
                "multiplier": multiplier,
                "status": "FAIL_NONLINEAR",
                "gate_status": False,
                "nonlinear_result": nonlinear.get("status_path"),
                "failure": nonlinear.get("failure"),
            }
        rows.append(row)
    return rows


def _child(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(SRC))
    sys.path.insert(0, str(ROOT))
    if args.label == "H1-replay":
        base_label = "H1"
    elif args.label.startswith("H1-small-"):
        base_label = "H1"
    else:
        base_label = args.label
    case = _case(base_label)
    result = _run_nonlinear(case, args.label, np.asarray(case["external"], dtype=float), OUTPUT)
    if args.small_loads:
        result["small_load_checks"] = _run_small_load_checks(case, OUTPUT)
        _write_json(OUTPUT / f"{_slug(args.label)}_result.json", result)
    print(json.dumps({"label": args.label, "status": result.get("status"), "wall_time_s": result.get("wall_time_s")}, sort_keys=True), flush=True)
    return 0


def _read_or_status(label: str) -> dict[str, Any]:
    result_path = OUTPUT / f"{_slug(label)}_result.json"
    if result_path.exists():
        return json.loads(result_path.read_text(encoding="utf-8"))
    status_path = OUTPUT / f"{_slug(label)}_status.json"
    if status_path.exists():
        return json.loads(status_path.read_text(encoding="utf-8"))
    return {"label": label, "status": "MISSING"}


def _launch(label: str, env: Mapping[str, str]) -> dict[str, Any]:
    command = [sys.executable, str(Path(__file__).resolve()), "--child", "--label", label]
    if label == "H1":
        command.append("--small-loads")
    completed = subprocess.run(command, cwd=ROOT, env=dict(env), check=False)
    result = _read_or_status(label)
    result.setdefault("process_returncode", completed.returncode)
    if result.get("status") == "RUNNING":
        result["status"] = "EXTERNALLY_INTERRUPTED"
    return result


def _campaign(args: argparse.Namespace) -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("status") != "FROZEN_BEFORE_RESULT_EXECUTION" or contract.get("result_execution_started") is not False:
        raise RuntimeError("HEX8 contract is not frozen before execution.")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(SRC), str(ROOT), env.get("PYTHONPATH", "")])
    campaign_started = datetime.now(timezone.utc).isoformat()
    labels = ("H1", "H1-replay", "H2", "H3")
    results: dict[str, Any] = {}
    for label in labels:
        print(f"[{datetime.now(timezone.utc).isoformat()}] launching {label} with frozen WP04-D route", flush=True)
        results[label] = _launch(label, env)

    successful = {label: row for label, row in results.items() if row.get("status") == "PASS"}
    pair: dict[str, Any] | None = None
    if "H2" in successful and "H3" in successful:
        h2 = successful["H2"].get("observables") or {}
        h3 = successful["H3"].get("observables") or {}
        pair = {
            "displacement": _relative_scalar(float(h3["tip_displacement"]), float(h2["tip_displacement"])),
            "reaction": _relative_vector(h3["equilibrium"]["reaction_resultant"], h2["equilibrium"]["reaction_resultant"]),
            "energy": _relative_scalar(float(h3["strain_energy"]), float(h2["strain_energy"])),
            "representative_sigma_xx": _relative_scalar(
                float(h3["representative_stress_sigma_xx"]), float(h2["representative_stress_sigma_xx"])
            ),
        }
        pair["threshold_status"] = bool(
            pair["displacement"] <= 0.02
            and pair["reaction"] <= 0.02
            and pair["energy"] <= 0.02
            and pair["representative_sigma_xx"] <= 0.10
        )

    replay: dict[str, Any] | None = None
    if "H1" in successful and "H1-replay" in successful:
        first = successful["H1"].get("observables") or {}
        second = successful["H1-replay"].get("observables") or {}
        replay = {
            "tip_displacement_relative": _relative_scalar(
                float(second["tip_displacement"]), float(first["tip_displacement"])
            ),
            "reaction_relative": _relative_vector(second["equilibrium"]["reaction_resultant"], first["equilibrium"]["reaction_resultant"]),
            "energy_relative": _relative_scalar(float(second["strain_energy"]), float(first["strain_energy"])),
            "stress_relative": _relative_scalar(
                float(second["representative_stress_sigma_xx"]), float(first["representative_stress_sigma_xx"])
            ),
            "accepted_load_path_equal": second.get("accepted_load_factors") == first.get("accepted_load_factors"),
            "termination_classifications_equal": second.get("termination_classifications") == first.get("termination_classifications"),
        }
        replay["status"] = bool(
            replay["tip_displacement_relative"] <= 1.0e-12
            and replay["reaction_relative"] <= 1.0e-12
            and replay["energy_relative"] <= 1.0e-12
            and replay["stress_relative"] <= 1.0e-12
            and replay["accepted_load_path_equal"]
            and replay["termination_classifications_equal"]
        )

    envelope = {
        "status": all(
            bool((row.get("observables") or {}).get("envelope_status", False))
            for label, row in successful.items()
            if label in ("H1", "H2", "H3")
        ) and all(label in successful for label in ("H1", "H2", "H3")),
        "minimum_det_f": min(
            [float((row.get("observables") or {})["minimum_det_f"]) for label, row in successful.items() if label in ("H1", "H2", "H3")],
            default=None,
        ),
        "minimum_principal_stretch": min(
            [float((row.get("observables") or {})["minimum_principal_stretch"]) for label, row in successful.items() if label in ("H1", "H2", "H3")],
            default=None,
        ),
        "maximum_principal_stretch": max(
            [float((row.get("observables") or {})["maximum_principal_stretch"]) for label, row in successful.items() if label in ("H1", "H2", "H3")],
            default=None,
        ),
        "maximum_green_lagrange_norm": max(
            [float((row.get("observables") or {})["maximum_green_lagrange_norm"])
             for label, row in successful.items() if label in ("H1", "H2", "H3")],
            default=None,
        ),
    }
    required_complete = all(results[label].get("status") == "PASS" for label in ("H1", "H2", "H3"))
    equilibrium_pass = required_complete and all(
        float((results[label].get("observables") or {}).get("equilibrium", {}).get("force_relative_error", float("inf"))) <= 1.0e-8
        and float((results[label].get("observables") or {}).get("equilibrium", {}).get("moment_relative_error", float("inf"))) <= 1.0e-8
        for label in ("H1", "H2", "H3")
    )
    g04_11_pass = bool(required_complete and pair and pair.get("threshold_status") and equilibrium_pass and envelope["status"] and (replay is None or replay.get("status")))
    h4_status = "NOT_RUN_OPTIONAL_RESCUE_NOT_TRIGGERED" if g04_11_pass else "NOT_RUN_REQUIRES_OWNER_REVIEW"
    campaign = {
        "schema_version": 1,
        "record_id": "QF-SOLVER-0.2.9-WP04-D-HEX8-CAMPAIGN-001",
        "work_package": "WP04-D",
        "gate": "G04-11",
        "status": "PASS_CANDIDATE" if g04_11_pass else "HOLD",
        "contract": "qualification/0_2_9/wp04d/hex8_contract.json",
        "contract_frozen_sha": contract.get("frozen_from_sha"),
        "execution_sha": _git_sha(),
        "branch": "0.2.9-unified-nonlinear",
        "campaign_started": campaign_started,
        "cases": results,
        "required_meshes": {label: list(cells) for label, cells in MESHES.items()},
        "h4_status": h4_status,
        "h2_to_h3": pair,
        "h1_replay": replay,
        "deformation_envelope": envelope,
        "equilibrium_status": equilibrium_pass,
        "g04_11_status": "PASS" if g04_11_pass else "HOLD",
        "g04_12_inputs_prepared": bool("H3" in successful),
        "g04_12_inputs": {
            "source": "H3",
            "observables": successful.get("H3", {}).get("observables"),
            "raw_npz": successful.get("H3", {}).get("raw_npz"),
            "decision": "PREPARED_ONLY_NO_CROSS_FAMILY_DECISION",
        },
        "full_test_suite_run": False,
        "petsc_run": False,
        "production_mechanics_changed": False,
        "maturity_changed": False,
        "wp04_points": "0/12",
        "validated_total": 29,
    }
    _write_json(OUTPUT / "hex8_campaign_result.json", campaign)
    audit = {
        "schema_version": 1,
        "record_id": "QF-SOLVER-0.2.9-WP04-D-G04-11-AUDIT-001",
        "audit_sha": _git_sha(),
        "contract_status": contract.get("status"),
        "physical_load": {
            "expected_resultant": TOTAL_RESULTANT.tolist(),
            "all_case_checks": {label: results[label].get("load_check") for label in results if "load_check" in results[label]},
        },
        "mesh_convergence": pair,
        "equilibrium": equilibrium_pass,
        "envelope": envelope,
        "replay": replay,
        "termination_routes": {label: results[label].get("termination_classifications") for label in results},
        "direct_fallback_counts": {label: (results[label].get("performance") or {}).get("fallback_count") for label in results},
        "g04_11": "PASS" if g04_11_pass else "HOLD",
        "g04_12": "INPUTS_PREPARED_ONLY",
        "limitations": [
            "HEX8 only; TET4 and cross-family decision remain outside this audit",
            "H4 was predeclared but not run unless the H2->H3 pair requires an owner-authorized rescue",
            "No maturity promotion or WP04 point award in WP04-D",
        ],
        "production_mechanics_changed": False,
        "full_test_suite_run": False,
    }
    _write_json(OUTPUT / "g04_11_audit.json", audit)
    print(json.dumps({"g04_11": campaign["g04_11_status"], "h2_to_h3": pair, "replay": replay}, sort_keys=True), flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--label", choices=("H1", "H1-replay", "H2", "H3"))
    parser.add_argument("--small-loads", action="store_true")
    args = parser.parse_args()
    if args.child:
        if args.label is None:
            raise SystemExit("--label is required with --child")
        return _child(args)
    return _campaign(args)


if __name__ == "__main__":
    raise SystemExit(main())
