"""Bounded TET10 cantilever transient study with exact semi-discrete oracle."""

from __future__ import annotations

import csv
import hashlib
import io
import itertools
import json
import math
import os
import platform
import sys
import tempfile
from importlib import metadata
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
import numpy as np
import scipy
import threadpoolctl

from solveur.api import solve_model
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.model import FiniteElementModel
from solveur.core.analyses.modal_newmark import ModalNewmarkTransientSolver
from solveur.elements.solid.tet10 import Tet10Element
from solveur.verification.transient_modal_oracle import PiecewiseLinearModalOracle


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "research/j9_transient/contracts/tet10_newmark_transient_contract.json"
NODEID = "tests/verification/test_j9_tet10_newmark.py::test_j9_tet10_direct_and_modal_newmark_time_mesh_study"
DIRECT_CONTRACT_PATH = ROOT / "research/j9_transient/contracts/tet10_newmark_direct_contract.json"
DIRECT_NODEID = "tests/verification/test_j9_tet10_newmark.py::test_j9_tet10_direct_newmark_time_mesh_study"
LENGTH_M, WIDTH_M, HEIGHT_M = 2.0, 0.4, 0.4
YOUNG_MODULUS_PA, POISSON_RATIO, DENSITY_KG_M3 = 70.0e9, 0.30, 2700.0
MESH_LEVELS = ((2, 1, 1), (4, 1, 1))
STEPS_PER_PERIOD = (16, 32, 64)
FORCE_N = -1.0
PULSE_DURATION_PERIODS = 0.25
PROBE_LABEL = "tip_center_uz"


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _file_sha256(path: Path) -> str:
    return _sha256(path.read_bytes())


def _atomic_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".", suffix=".tmp", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _atomic_json(path: Path, payload: dict[str, Any]) -> str:
    encoded = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    _atomic_bytes(path, encoded)
    return _sha256(encoded)


def _atomic_npz(path: Path, **arrays: np.ndarray) -> str:
    buffer = io.BytesIO()
    np.savez_compressed(buffer, **arrays)
    encoded = buffer.getvalue()
    _atomic_bytes(path, encoded)
    return _sha256(encoded)


def _threadpool_summary() -> list[dict[str, Any]]:
    keep = ("user_api", "internal_api", "num_threads", "version", "prefix")
    return [{key: item[key] for key in keep if key in item} for item in threadpoolctl.threadpool_info()]


def _mesh(cells: tuple[int, int, int]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    nx, ny, nz = cells
    vertices: list[list[float]] = []
    vertex_ids: dict[tuple[int, int, int], int] = {}
    for k in range(nz + 1):
        for j in range(ny + 1):
            for i in range(nx + 1):
                vertex_ids[i, j, k] = len(vertices)
                vertices.append([LENGTH_M * i / nx, WIDTH_M * j / ny, HEIGHT_M * k / nz])
    coordinates = [np.asarray(value, dtype=np.float64) for value in vertices]
    midpoint_ids: dict[tuple[int, int], int] = {}
    elements: list[list[int]] = []
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                origin = np.asarray((i, j, k), dtype=int)
                for permutation in itertools.permutations((0, 1, 2)):
                    p0 = origin
                    p1 = origin.copy(); p1[permutation[0]] += 1
                    p2 = p1.copy(); p2[permutation[1]] += 1
                    p3 = origin + 1
                    corners = [vertex_ids[tuple(point)] for point in (p0, p1, p2, p3)]
                    corner_xyz = np.asarray([coordinates[node] for node in corners])
                    jacobian = float(np.linalg.det((corner_xyz[1:] - corner_xyz[0]).T))
                    if jacobian < 0.0:
                        corners[1], corners[2] = corners[2], corners[1]
                        jacobian = -jacobian
                    if jacobian <= 0.0:
                        raise RuntimeError("Generated TET10 cell has a non-positive corner Jacobian")
                    local_edges = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
                    connectivity = list(corners)
                    for left, right in local_edges:
                        edge = tuple(sorted((corners[left], corners[right])))
                        if edge not in midpoint_ids:
                            midpoint_ids[edge] = len(coordinates)
                            coordinates.append(0.5 * (coordinates[edge[0]] + coordinates[edge[1]]))
                        connectivity.append(midpoint_ids[edge])
                    elements.append(connectivity)
    xyz = np.asarray(coordinates, dtype=np.float64)
    connectivity = np.asarray(elements, dtype=np.int64)
    corner_volumes = np.asarray(
        [Tet10Element.corner_signed_volume(xyz[row]) for row in connectivity], dtype=np.float64
    )
    if not np.all(corner_volumes > 0.0):
        raise RuntimeError("Generated TET10 mesh contains an inverted element")
    return xyz, connectivity, corner_volumes


def _make_model(
    coordinates: np.ndarray,
    connectivity: np.ndarray,
    tip_node: int,
    root_nodes: np.ndarray,
    *,
    dt: float,
    steps: int,
    table: list[dict[str, float]],
    method: str,
    modal_modes: int | None = None,
) -> FiniteElementModel:
    parameters: dict[str, Any] = {
        "time_step": dt,
        "steps": steps,
        "newmark_beta": 0.25,
        "newmark_gamma": 0.5,
        "rayleigh_alpha": 0.0,
        "rayleigh_beta": 0.0,
        "load_table": table,
        "record_time_history": True,
        "history_probes": [{"node": int(tip_node), "dof": "UZ", "label": PROBE_LABEL}],
        "postprocess_mode": "summary",
    }
    if method == "modal_newmark":
        if modal_modes is None:
            raise ValueError("Modal Newmark needs an explicitly fixed mode count")
        parameters.update({
            "modal_mode_count": int(modal_modes),
            "modal_extraction_method": "dense",
            "modal_dense_limit": 256,
            "modal_validation_policy": "strict",
        })
    return FiniteElementModel.from_raw(
        nodes=coordinates.tolist(),
        elements=[{"type": "TET10", "nodes": row.tolist(), "material": "aluminium"} for row in connectivity],
        materials={"aluminium": {"type": "isotropic_3d", "E": YOUNG_MODULUS_PA, "nu": POISSON_RATIO, "density": DENSITY_KG_M3}},
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in root_nodes],
        loads=[{"node": int(tip_node), "dof": "UZ", "value": FORCE_N}],
        analysis={"type": "transient_dynamic", "method": method, **parameters},
        units={"length": "m", "force": "N", "time": "s", "mass": "kg"},
        verification_profile="quick",
    )


def _pulse_table(period: float, steps_per_period: int) -> tuple[float, int, list[dict[str, float]], np.ndarray]:
    dt = period / steps_per_period
    steps = 2 * steps_per_period
    times = dt * np.arange(steps + 1, dtype=np.float64)
    peak = period / 8.0
    end = period / 4.0
    factors = np.asarray([
        max(0.0, min(float(time / peak), float((end - time) / peak))) if time <= end else 0.0
        for time in times
    ], dtype=np.float64)
    table = [{"time": float(time), "factor": float(factor)} for time, factor in zip(times, factors, strict=True)]
    return float(dt), steps, table, factors


def _response_values(rows: Any) -> np.ndarray:
    return np.asarray([float(row["probes"][PROBE_LABEL]["displacement"]) for row in rows], dtype=np.float64)


def _error_metrics(actual: np.ndarray, reference: np.ndarray) -> dict[str, float]:
    delta = np.asarray(actual, dtype=np.float64) - np.asarray(reference, dtype=np.float64)
    scale = max(float(np.max(np.abs(reference))), np.finfo(float).tiny)
    return {
        "rms_absolute_error_m": float(np.sqrt(np.mean(delta**2))),
        "rms_normalized_to_reference_peak": float(np.sqrt(np.mean(delta**2)) / scale),
        "peak_absolute_difference_m": float(np.max(np.abs(delta))),
    }


def _attempt_output_dir(nodeid: str) -> tuple[Path, dict[str, Any]]:
    if os.environ.get("QF_DEVELOPMENT_AUTONOMOUS") != "1":
        raise RuntimeError("J9 mechanics outputs require the registered development launcher")
    temp = Path(os.environ["TMP"]).resolve(strict=True)
    attempt_dir = temp.parent
    run_path = attempt_dir / "run.json"
    if not run_path.is_file():
        raise RuntimeError("The development runner attempt record is missing")
    run = json.loads(run_path.read_text(encoding="utf-8"))
    if run.get("state") != "RUNNING" or run.get("worktree_id") != "j9" or run.get("target") != [nodeid]:
        raise RuntimeError("The development runner does not identify this exact J9 TET10 node")
    output = attempt_dir / "output" / "j9_tet10_newmark"
    output.mkdir(parents=True, exist_ok=False)
    return output, run


def _draw_mesh(axis: Any, coordinates: np.ndarray, connectivity: np.ndarray, *, color: str) -> None:
    edges: set[tuple[int, int]] = set()
    for tet in connectivity:
        for left, right in itertools.combinations(tet[:4], 2):
            edges.add(tuple(sorted((int(left), int(right)))))
    for left, right in edges:
        axis.plot(*coordinates[[left, right]].T, color=color, linewidth=0.45, alpha=0.55)
    axis.set(xlabel="x [m]", ylabel="y [m]", zlabel="z [m]")
    axis.set_box_aspect((LENGTH_M, WIDTH_M, HEIGHT_M))
    axis.scatter([0.0], [0.0], [0.0], color="#246b83", s=25, label="encastrement x=0")
    axis.quiver(LENGTH_M, WIDTH_M / 2, HEIGHT_M / 2, 0.0, 0.0, -0.12, color="#ba3e2d", arrow_length_ratio=0.2, label="Fz(t)")


def run_transient_study(
    *,
    contract_path: Path = CONTRACT_PATH,
    nodeid: str = NODEID,
    include_modal: bool = True,
) -> dict[str, Any]:
    output_dir, run = _attempt_output_dir(nodeid)
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract_hash = _file_sha256(contract_path)
    for source in contract["source_identity"]["files"]:
        if _file_sha256(ROOT / source["path"]) != source["sha256"]:
            raise RuntimeError(f"TET10/Newmark source differs from the frozen J9 contract: {source['path']}")
    for source in contract["source_identity"]["analysis_files"]:
        if _file_sha256(ROOT / source["path"]) != source["sha256"]:
            raise RuntimeError(f"TET10/Newmark analysis code differs from its frozen contract: {source['path']}")
    levels: list[dict[str, Any]] = []
    mesh_states: list[dict[str, np.ndarray]] = []
    mesh_frequency: dict[tuple[int, int, int], float] = {}
    direct_curves: dict[tuple[tuple[int, int, int], int], tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    modal_comparison: dict[str, Any] | None = None
    modal_route_curve: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None
    csv_rows: list[dict[str, Any]] = []
    npz_arrays: dict[str, np.ndarray] = {}

    for mesh_index, cells in enumerate(MESH_LEVELS):
        coordinates, connectivity, volumes = _mesh(cells)
        root = np.flatnonzero(np.isclose(coordinates[:, 0], 0.0, atol=1.0e-12))
        tip_candidates = np.linalg.norm(coordinates - np.asarray([LENGTH_M, WIDTH_M / 2.0, HEIGHT_M / 2.0]), axis=1)
        tip_node = int(np.argmin(tip_candidates))
        if tip_candidates[tip_node] > 1.0e-12:
            raise RuntimeError("The declared tip-center load/probe node is absent from the TET10 mesh")

        reference_model = _make_model(coordinates, connectivity, tip_node, root, dt=1.0e-6, steps=1,
                                      table=[{"time": 0.0, "factor": 0.0}, {"time": 1.0e-6, "factor": 0.0}],
                                      method="newmark")
        oracle = PiecewiseLinearModalOracle(reference_model)
        if oracle.eigenvalues.size == 0:
            raise RuntimeError("The constrained TET10 model has no positive structural modes")
        frequency_hz = float(math.sqrt(oracle.eigenvalues[0]) / (2.0 * math.pi))
        period = 1.0 / frequency_hz
        mesh_frequency[cells] = frequency_hz
        dofs = reference_model.dof_manager()
        probe_index = dofs.index(tip_node, "UZ")
        full_load = GlobalAssembler().assemble_loads(reference_model, dofs)
        load_resultant = [
            math.fsum(float(full_load[dofs.index(node, dof)]) for node in range(len(coordinates)))
            for dof in ("UX", "UY", "UZ")
        ]
        if not np.allclose(load_resultant, [0.0, 0.0, FORCE_N], rtol=0.0, atol=1.0e-14):
            raise RuntimeError("Assembled nodal pulse resultant differs from the frozen 1 N vertical load")
        mesh_row: dict[str, Any] = {
            "mesh_level": mesh_index,
            "cells": list(cells),
            "node_count": int(len(coordinates)),
            "element_count": int(len(connectivity)),
            "root_fixed_node_count": int(len(root)),
            "free_dof_count": int(dofs.ndof - len(GlobalAssembler().fixed_indices(reference_model, dofs))),
            "tip_center_node": tip_node,
            "tip_probe_position_m": coordinates[tip_node].tolist(),
            "assembled_load_resultant_n": load_resultant,
            "minimum_tet_corner_volume_m3": float(np.min(volumes)),
            "maximum_tet_corner_volume_m3": float(np.max(volumes)),
            "first_semi_discrete_frequency_hz": frequency_hz,
            "period_s": period,
            "time_levels": [],
        }
        mesh_states.append({"coordinates_m": coordinates, "connectivity_tet10": connectivity,
                            "corner_volumes_m3": volumes, "root_nodes": root,
                            "tip_node": np.asarray([tip_node]), "stiffness_eigenvalues_s2": oracle.eigenvalues,
                            "reduced_stiffness_n_per_m": oracle.reducer.stiffness.toarray(),
                            "reduced_mass_kg": oracle.reducer.mass.toarray()})

        for steps_per_period in STEPS_PER_PERIOD:
            dt, steps, table, factors = _pulse_table(period, steps_per_period)
            model = _make_model(coordinates, connectivity, tip_node, root, dt=dt, steps=steps, table=table,
                                method="newmark")
            exact = oracle.propagate(full_load, factors, dt, displacement_probe_index=probe_index)
            result = solve_model(model, enforce_policy=False)
            times = np.asarray([row["time"] for row in result.solver["time_history"]], dtype=np.float64)
            values = _response_values(result.solver["time_history"])
            errors = _error_metrics(values, exact.displacement_probe)
            rows = result.solver["time_history"]
            energy = np.asarray([float(row["strain_energy"]) + float(row["kinetic_energy"]) for row in rows])
            pulse_end = period * PULSE_DURATION_PERIODS
            tail = energy[times >= pulse_end]
            tail_energy_range = (
                float((np.max(tail) - np.min(tail)) / max(float(np.max(np.abs(tail))), np.finfo(float).tiny))
                if tail.size else 0.0
            )
            row = {
                "steps_per_period": steps_per_period,
                "time_step_s": dt,
                "step_count": steps,
                "duration_s": dt * steps,
                "pulse_duration_s": pulse_end,
                "force_resultant_n": FORCE_N,
                "oracle_modal_count": int(oracle.eigenvalues.size),
                "direct_status": result.status,
                **errors,
                "max_dynamic_residual_norm": float(max(result.solver["residual_history"], default=0.0)),
                "maximum_tail_energy_range_relative": tail_energy_range,
                "peak_tip_displacement_m": float(np.max(np.abs(values))),
            }
            mesh_row["time_levels"].append(row)
            direct_curves[(cells, steps_per_period)] = (times, values, exact.displacement_probe)
            for step, (time, actual, reference) in enumerate(zip(times, values, exact.displacement_probe, strict=True), start=1):
                csv_rows.append({
                    "route": "direct_newmark",
                    "cells": "x".join(map(str, cells)),
                    "steps_per_period": steps_per_period,
                    "step": step,
                    "time_s": float(time),
                    "tip_uz_qf_m": float(actual),
                    "tip_uz_oracle_m": float(reference),
                    "difference_m": float(actual - reference),
                })
            npz_arrays[f"times_m{mesh_index}_n{steps_per_period}_s"] = times
            npz_arrays[f"direct_m{mesh_index}_n{steps_per_period}_m"] = values
            npz_arrays[f"oracle_m{mesh_index}_n{steps_per_period}_m"] = exact.displacement_probe
        errors_in_time_order = [float(row["rms_normalized_to_reference_peak"]) for row in mesh_row["time_levels"]]
        mesh_row["observed_time_refinement_orders"] = [
            (
                math.log(errors_in_time_order[index] / errors_in_time_order[index + 1], 2.0)
                if errors_in_time_order[index] > 0.0 and errors_in_time_order[index + 1] > 0.0
                else None
            )
            for index in range(len(errors_in_time_order) - 1)
        ]
        levels.append(mesh_row)

        if mesh_index == 0 and include_modal:
            steps_per_period = 32
            dt, steps, table, factors = _pulse_table(period, steps_per_period)
            free_dofs = int(mesh_row["free_dof_count"])
            if free_dofs > 256:
                raise RuntimeError("The prospective full-basis modal comparison exceeds the frozen dense limit of 256 DOFs")
            modal_model = _make_model(coordinates, connectivity, tip_node, root, dt=dt, steps=steps, table=table,
                                      method="modal_newmark", modal_modes=free_dofs)
            modal = ModalNewmarkTransientSolver().solve(modal_model, source_sha=str(run["identity"]["head"]))
            modal_values = _response_values(modal.time_history)
            exact = oracle.propagate(full_load, factors, dt, displacement_probe_index=probe_index)
            direct_values = direct_curves[(cells, steps_per_period)][1]
            modal_comparison = {
                "mesh_cells": list(cells),
                "mode_count": free_dofs,
                "basis_is_full_order": True,
                "modal_numerical_status": modal.numerical_status,
                "direct_vs_modal": _error_metrics(modal_values, direct_values),
                "modal_vs_exact_semidiscrete": _error_metrics(modal_values, exact.displacement_probe),
                "modal_time_step_s": dt,
                "modal_step_count": steps,
            }
            modal_route_curve = (np.asarray(modal.times, dtype=np.float64), modal_values, exact.displacement_probe)
            for step, (time, actual, reference) in enumerate(zip(modal.times, modal_values, exact.displacement_probe, strict=True), start=1):
                csv_rows.append({
                    "route": "modal_newmark_full_basis",
                    "cells": "x".join(map(str, cells)),
                    "steps_per_period": steps_per_period,
                    "step": step,
                    "time_s": float(time),
                    "tip_uz_qf_m": float(actual),
                    "tip_uz_oracle_m": float(reference),
                    "difference_m": float(actual - reference),
                })
            npz_arrays["modal_coarse_m"] = modal_values
            npz_arrays["modal_coarse_times_s"] = np.asarray(modal.times)

    first, last = levels[0], levels[-1]
    result_payload: dict[str, Any] = {
        "schema": "qf-j9-tet10-newmark-result-v1",
        "classification": "DEVELOPMENT_EXPLORATORY_NOT_QUALIFICATION",
        "execution_status": "COMPLETED_EXPLORATORY",
        "nodeid": nodeid,
        "source_head": run["identity"]["head"],
        "source_fingerprint": run["source_fingerprint"],
        "contract_sha256": contract_hash,
        "model": {
            "geometry_m": [LENGTH_M, WIDTH_M, HEIGHT_M],
            "material": {"young_modulus_pa": YOUNG_MODULUS_PA, "poisson_ratio": POISSON_RATIO, "density_kg_m3": DENSITY_KG_M3},
            "mass_matrix": "consistent TET10 mass assembled by GlobalAssembler",
            "boundary_condition": "all translational DOFs fixed on the complete x=0 face",
            "load": "1 N triangular vertical nodal pulse at the center node of x=L face",
            "initial_conditions": "zero displacement and velocity",
            "newmark": {"beta": 0.25, "gamma": 0.5, "rayleigh_alpha_s_inv": 0.0, "rayleigh_beta_s": 0.0},
            "probe": {"node_definition": "tip-face center", "dof": "UZ", "units": "m"},
        },
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "matplotlib": metadata.version("matplotlib"),
            "threadpools": _threadpool_summary(),
        },
        "reference": {
            "type": "exact full-order modal state-space propagation of the assembled semi-discrete M/K system under the same piecewise-linear load table",
            "formula": "independent scipy.linalg.eigh(M,K) plus matrix-exponential propagation per affine load segment; no Newmark recurrence or modal truncation",
            "validates": "time integration against the same assembled spatial system and load table",
            "does_not_validate": "TET10 spatial discretization against an independent continuum or external solver",
        },
        "mesh_levels": levels,
        "mesh_frequency_increment_relative": abs(float(last["first_semi_discrete_frequency_hz"]) - float(first["first_semi_discrete_frequency_hz"])) / float(last["first_semi_discrete_frequency_hz"]),
        "modal_route_comparison": modal_comparison,
        "criteria": {
            "formal_acceptance_thresholds": "none; numerical differences are descriptive indicators fixed before execution",
            "structural_checks": "positive tetra corner volumes; assembled load resultant equals (0,0,-1) N; finite response; direct and modal routes return completed results; tip probe remains at a fixed physical location",
        },
        "interpretation": "The time-step study isolates Newmark temporal integration against a full-order semi-discrete oracle. The two axial mesh levels are a descriptive spatial sensitivity study with one cross-section cell; they do not establish spatial convergence.",
    }
    state_sha = _atomic_npz(output_dir / "tet10_newmark_states.npz", **npz_arrays,
                            coarse_coordinates_m=mesh_states[0]["coordinates_m"],
                            coarse_connectivity_tet10=mesh_states[0]["connectivity_tet10"],
                            coarse_reduced_stiffness_n_per_m=mesh_states[0]["reduced_stiffness_n_per_m"],
                            coarse_reduced_mass_kg=mesh_states[0]["reduced_mass_kg"],
                            fine_coordinates_m=mesh_states[1]["coordinates_m"],
                            fine_connectivity_tet10=mesh_states[1]["connectivity_tet10"],
                            fine_reduced_stiffness_n_per_m=mesh_states[1]["reduced_stiffness_n_per_m"],
                            fine_reduced_mass_kg=mesh_states[1]["reduced_mass_kg"])
    result_payload["states_npz"] = {"path": "tet10_newmark_states.npz", "sha256": state_sha}
    csv_path = output_dir / "tet10_newmark_history.csv"
    with tempfile.NamedTemporaryFile(mode="w", dir=output_dir, prefix=csv_path.name + ".", suffix=".tmp", delete=False, newline="", encoding="utf-8") as stream:
        temporary_csv = Path(stream.name)
        writer = csv.DictWriter(stream, fieldnames=["route", "cells", "steps_per_period", "step", "time_s", "tip_uz_qf_m", "tip_uz_oracle_m", "difference_m"])
        writer.writeheader()
        writer.writerows(csv_rows)
        stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary_csv, csv_path)
    result_payload["history_csv"] = {"path": csv_path.name, "sha256": _file_sha256(csv_path)}
    mesh_figure = output_dir / "tet10_newmark_mesh.png"
    _plot_meshes(mesh_states, mesh_figure)
    history_figure = output_dir / "tet10_newmark_history.png"
    _plot_histories(direct_curves, mesh_frequency, modal_route_curve, history_figure)
    result_payload["figures"] = {
        mesh_figure.name: _file_sha256(mesh_figure),
        history_figure.name: _file_sha256(history_figure),
    }
    result_hash = _atomic_json(output_dir / "result.json", result_payload)
    _atomic_json(output_dir / "result.sha256.json", {"sha256": result_hash})
    return result_payload


def _plot_meshes(states: list[dict[str, np.ndarray]], path: Path) -> None:
    figure = plt.figure(figsize=(10, 4.5))
    for index, state in enumerate(states):
        axis = figure.add_subplot(1, 2, index + 1, projection="3d")
        _draw_mesh(axis, state["coordinates_m"], state["connectivity_tet10"], color="#486b58")
        axis.set_title(f"TET10 {MESH_LEVELS[index][0]}×{MESH_LEVELS[index][1]}×{MESH_LEVELS[index][2]} cubes")
    figure.suptitle("Cantilever 3D : encastrement et impulsion triangulaire au centre de la face libre")
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def _plot_histories(
    curves: dict[tuple[tuple[int, int, int], int], tuple[np.ndarray, np.ndarray, np.ndarray]],
    frequencies: dict[tuple[int, int, int], float],
    modal_curve: tuple[np.ndarray, np.ndarray, np.ndarray] | None,
    path: Path,
) -> None:
    figure, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for cells in MESH_LEVELS:
        key = (cells, 64)
        times, values, exact = curves[key]
        axes[0].plot(times * frequencies[cells], values * 1.0e6, label=f"QF {cells[0]} axial cells")
        axes[0].plot(times * frequencies[cells], exact * 1.0e6, "--", label=f"oracle {cells[0]} axial cells")
    axes[0].set(xlabel="Temps / période propre [–]", ylabel="UZ du point de mesure [µm]", title="Newmark direct vs oracle semi-discret exact")
    axes[0].legend(fontsize=7)
    axes[0].grid(True, alpha=0.3)
    cells = MESH_LEVELS[0]
    times, direct, exact = curves[(cells, 32)]
    axes[1].plot(times * frequencies[cells], direct * 1.0e6, label="Newmark direct")
    axes[1].plot(times * frequencies[cells], exact * 1.0e6, "--", label="Propagation modale exacte")
    if modal_curve is not None:
        modal_times, modal_values, _modal_exact = modal_curve
        axes[1].plot(modal_times * frequencies[cells], modal_values * 1.0e6, ":", label="Newmark modal, base complète")
    axes[1].set(xlabel="Temps / période propre [–]", ylabel="UZ du point de mesure [µm]", title="Mêmes M/K : étude de l’intégrateur")
    axes[1].legend(fontsize=8)
    axes[1].grid(True, alpha=0.3)
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)
