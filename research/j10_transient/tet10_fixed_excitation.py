"""J10 TET10/Newmark study with common physical loading and observation times."""

from __future__ import annotations

import csv
import hashlib
import io
import itertools
import json
import math
import os
import platform
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
from solveur.elements.solid.tet10 import Tet10Element
from solveur.verification.transient_modal_oracle import PiecewiseLinearModalOracle


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "research/j10_transient/contracts/tet10_fixed_excitation_contract.json"
NODEID = "tests/verification/test_j10_tet10_fixed_excitation.py::test_j10_tet10_same_physical_excitation_time_mesh_study"
LENGTH_M, WIDTH_M, HEIGHT_M = 2.0, 0.4, 0.4
YOUNG_MODULUS_PA, POISSON_RATIO, DENSITY_KG_M3 = 70.0e9, 0.30, 2700.0
MESH_LEVELS = ((2, 1, 1), (4, 1, 1), (4, 2, 1), (4, 2, 2))
TIME_STEPS_S = (5.0e-4, 2.5e-4, 1.25e-4)
PULSE_PEAK_TIME_S, PULSE_END_TIME_S, OBSERVATION_END_TIME_S = 1.0e-3, 2.0e-3, 24.0e-3
FORCE_N = -1.0
MIDSPAN_PROBE = np.asarray((1.0, 0.2, 0.2), dtype=np.float64)
TIP_LOAD_POINT = np.asarray((LENGTH_M, WIDTH_M / 2.0, HEIGHT_M / 2.0), dtype=np.float64)
PROBE_LABEL = "midspan_center_uz"
TIP_LABEL = "tip_center_uz"


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _file_sha256(path: Path) -> str:
    return _sha256(path.read_bytes())


def _canonical_sha256(path: Path) -> str:
    return _sha256(path.read_bytes().replace(b"\r\n", b"\n"))


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


def _attempt_output_dir() -> tuple[Path, dict[str, Any]]:
    if os.environ.get("QF_DEVELOPMENT_AUTONOMOUS") != "1":
        raise RuntimeError("J10 transient outputs require the registered development launcher")
    temp = Path(os.environ["TMP"]).resolve(strict=True)
    attempt_dir = temp.parent
    run_path = attempt_dir / "run.json"
    if not run_path.is_file():
        raise RuntimeError("The development runner attempt record is missing")
    run = json.loads(run_path.read_text(encoding="utf-8"))
    if run.get("state") != "RUNNING" or run.get("worktree_id") != "j10" or run.get("target") != [NODEID]:
        raise RuntimeError("The development runner does not identify this exact J10 transient node")
    expected = (ROOT / ".codex/development-runs/worktrees/j10").resolve()
    try:
        attempt_dir.resolve().relative_to(expected)
    except ValueError as exc:
        raise RuntimeError("The J10 transient output directory is outside its registered attempt namespace") from exc
    output = attempt_dir / "output" / "j10_tet10_same_excitation"
    output.mkdir(parents=True, exist_ok=False)
    return output, run


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
                    p1 = origin.copy()
                    p1[permutation[0]] += 1
                    p2 = p1.copy()
                    p2[permutation[1]] += 1
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
    corner_volumes = np.asarray([Tet10Element.corner_signed_volume(xyz[row]) for row in connectivity])
    if not np.all(corner_volumes > 0.0):
        raise RuntimeError("Generated TET10 mesh contains an inverted element")
    return xyz, connectivity, corner_volumes


def _load_factor(time_s: float) -> float:
    if time_s <= PULSE_PEAK_TIME_S:
        return float(time_s / PULSE_PEAK_TIME_S)
    if time_s < PULSE_END_TIME_S:
        return float((PULSE_END_TIME_S - time_s) / (PULSE_END_TIME_S - PULSE_PEAK_TIME_S))
    return 0.0


def _time_table(time_step_s: float) -> tuple[np.ndarray, np.ndarray, list[dict[str, float]]]:
    steps = int(round(OBSERVATION_END_TIME_S / time_step_s))
    if not math.isclose(steps * time_step_s, OBSERVATION_END_TIME_S, rel_tol=0.0, abs_tol=1.0e-15):
        raise ValueError("The frozen time step must divide the common observation interval exactly")
    times = time_step_s * np.arange(steps + 1, dtype=np.float64)
    factors = np.asarray([_load_factor(float(time)) for time in times], dtype=np.float64)
    table = [{"time": float(time), "factor": float(factor)} for time, factor in zip(times, factors, strict=True)]
    return times, factors, table


def _make_model(
    coordinates: np.ndarray,
    connectivity: np.ndarray,
    tip_node: int,
    root_nodes: np.ndarray,
    midspan_node: int,
    *,
    time_step_s: float,
    table: list[dict[str, float]],
) -> FiniteElementModel:
    steps = int(round(OBSERVATION_END_TIME_S / time_step_s))
    parameters: dict[str, Any] = {
        "time_step": time_step_s,
        "steps": steps,
        "newmark_beta": 0.25,
        "newmark_gamma": 0.5,
        "rayleigh_alpha": 0.0,
        "rayleigh_beta": 0.0,
        "load_table": table,
        "record_time_history": True,
        "history_probes": [
            {"node": int(midspan_node), "dof": "UZ", "label": PROBE_LABEL},
            {"node": int(tip_node), "dof": "UZ", "label": TIP_LABEL},
        ],
        "postprocess_mode": "summary",
    }
    return FiniteElementModel.from_raw(
        nodes=coordinates.tolist(),
        elements=[{"type": "TET10", "nodes": row.tolist(), "material": "aluminium"} for row in connectivity],
        materials={"aluminium": {
            "type": "isotropic_3d",
            "E": YOUNG_MODULUS_PA,
            "nu": POISSON_RATIO,
            "density": DENSITY_KG_M3,
        }},
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in root_nodes],
        loads=[{"node": int(tip_node), "dof": "UZ", "value": FORCE_N}],
        analysis={"type": "transient_dynamic", "method": "newmark", **parameters},
        units={"length": "m", "force": "N", "time": "s", "mass": "kg"},
        verification_profile="quick",
    )


def _probe_values(rows: list[dict[str, Any]], label: str) -> np.ndarray:
    return np.asarray([float(row["probes"][label]["displacement"]) for row in rows], dtype=np.float64)


def _error_metrics(actual: np.ndarray, reference: np.ndarray, global_scale_m: float) -> dict[str, float]:
    delta = np.asarray(actual, dtype=np.float64) - np.asarray(reference, dtype=np.float64)
    rms = float(np.sqrt(np.mean(delta**2)))
    peak = float(np.max(np.abs(delta)))
    return {
        "rms_absolute_error_m": rms,
        "peak_absolute_difference_m": peak,
        "rms_normalized_by_global_oracle_peak": rms / global_scale_m,
        "peak_normalized_by_global_oracle_peak": peak / global_scale_m,
    }


def _environment() -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "matplotlib": metadata.version("matplotlib"),
        "threadpools": [
            {key: item.get(key) for key in ("user_api", "internal_api", "version", "num_threads")}
            for item in threadpoolctl.threadpool_info()
        ],
    }


def run_study() -> dict[str, Any]:
    output_dir, run = _attempt_output_dir()
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    contract_sha = _canonical_sha256(CONTRACT_PATH)
    for item in contract["source_identity"]:
        if _canonical_sha256(ROOT / item["path"]) != item["canonical_sha256"]:
            raise RuntimeError(f"TET10/J10 source differs from the frozen contract: {item['path']}")

    models: dict[tuple[int, int, int], dict[str, Any]] = {}
    oracle_histories: dict[tuple[tuple[int, int, int], float], Any] = {}
    mesh_rows: dict[tuple[int, int, int], dict[str, Any]] = {}
    state_arrays: dict[str, np.ndarray] = {}
    csv_rows: list[dict[str, Any]] = []
    global_scale = 0.0

    for mesh_index, cells in enumerate(MESH_LEVELS):
        coordinates, connectivity, corner_volumes = _mesh(cells)
        tip_distances = np.linalg.norm(coordinates - TIP_LOAD_POINT, axis=1)
        midspan_distances = np.linalg.norm(coordinates - MIDSPAN_PROBE, axis=1)
        tip_node = int(np.argmin(tip_distances))
        midspan_node = int(np.argmin(midspan_distances))
        if tip_distances[tip_node] > 1.0e-12 or midspan_distances[midspan_node] > 1.0e-12:
            raise RuntimeError("A declared physical TET10 load/probe coordinate is absent from a selected mesh")
        root_nodes = np.flatnonzero(np.isclose(coordinates[:, 0], 0.0, rtol=0.0, atol=1.0e-12))
        reference_step = min(TIME_STEPS_S)
        zero_table = [{"time": 0.0, "factor": 0.0}, {"time": reference_step, "factor": 0.0}]
        reference_model = _make_model(
            coordinates, connectivity, tip_node, root_nodes, midspan_node,
            time_step_s=reference_step, table=zero_table,
        )
        oracle = PiecewiseLinearModalOracle(reference_model)
        if oracle.eigenvalues.size == 0:
            raise RuntimeError("The constrained TET10 model has no positive structural modes")
        dofs = reference_model.dof_manager()
        full_load = GlobalAssembler().assemble_loads(reference_model, dofs)
        load_resultant = [
            math.fsum(float(full_load[dofs.index(node, component)]) for node in range(len(coordinates)))
            for component in ("UX", "UY", "UZ")
        ]
        if not np.allclose(load_resultant, (0.0, 0.0, FORCE_N), rtol=0.0, atol=1.0e-14):
            raise RuntimeError("The assembled TET10 force resultant differs from the frozen 1 N load")
        first_frequency_hz = float(math.sqrt(float(oracle.eigenvalues[0])) / (2.0 * math.pi))
        mesh_row: dict[str, Any] = {
            "cells": list(cells),
            "node_count": int(len(coordinates)),
            "element_count": int(len(connectivity)),
            "free_dof_count": int(oracle.reducer.stiffness.shape[0]),
            "root_fixed_node_count": int(len(root_nodes)),
            "load_node": tip_node,
            "load_position_m": coordinates[tip_node].tolist(),
            "measurement_node": midspan_node,
            "measurement_position_m": coordinates[midspan_node].tolist(),
            "assembled_force_resultant_n": load_resultant,
            "minimum_tet_corner_volume_m3": float(np.min(corner_volumes)),
            "maximum_tet_corner_volume_m3": float(np.max(corner_volumes)),
            "first_semidiscrete_frequency_hz": first_frequency_hz,
            "time_levels": [],
        }
        mesh_rows[cells] = mesh_row
        models[cells] = {
            "coordinates": coordinates,
            "connectivity": connectivity,
            "corner_volumes": corner_volumes,
            "root_nodes": root_nodes,
            "tip_node": tip_node,
            "midspan_node": midspan_node,
            "reference_model": reference_model,
            "oracle": oracle,
            "full_load": full_load,
            "dofs": dofs,
        }
        state_arrays[f"coordinates_m_{mesh_index}"] = coordinates
        state_arrays[f"connectivity_tet10_{mesh_index}"] = connectivity
        state_arrays[f"corner_volumes_m3_{mesh_index}"] = corner_volumes
        state_arrays[f"reduced_stiffness_n_per_m_{mesh_index}"] = oracle.reducer.stiffness.toarray()
        state_arrays[f"reduced_mass_kg_{mesh_index}"] = oracle.reducer.mass.toarray()
        state_arrays[f"eigenvalues_s2_{mesh_index}"] = oracle.eigenvalues
        state_arrays[f"free_dofs_{mesh_index}"] = np.asarray(oracle.reducer.free, dtype=np.int64)

        for time_step_s in TIME_STEPS_S:
            times, factors, _table = _time_table(time_step_s)
            exact = oracle.propagate(
                full_load,
                factors,
                time_step_s,
                displacement_probe_index=dofs.index(midspan_node, "UZ"),
            )
            if not np.allclose(exact.times, times[1:], rtol=0.0, atol=1.0e-14):
                raise RuntimeError("The semidiscrete oracle times differ from the frozen common physical grid")
            oracle_histories[(cells, time_step_s)] = exact
            if time_step_s == min(TIME_STEPS_S):
                global_scale = max(global_scale, float(np.max(np.abs(exact.displacement_probe))))
            state_arrays[f"oracle_m{mesh_index}_dt{time_step_s:.7f}_uz_m"] = exact.displacement_probe
            state_arrays[f"times_dt{time_step_s:.7f}_s"] = times[1:]
        state_arrays[f"tip_load_vector_m{mesh_index}_n"] = full_load

    if not math.isfinite(global_scale) or global_scale <= 0.0:
        raise RuntimeError("A positive global oracle response scale is required for robust normalization")

    direct_curves: dict[tuple[tuple[int, int, int], float], tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for mesh_index, cells in enumerate(MESH_LEVELS):
        model_data = models[cells]
        mesh_row = mesh_rows[cells]
        for time_step_s in TIME_STEPS_S:
            times, factors, table = _time_table(time_step_s)
            model = _make_model(
                model_data["coordinates"],
                model_data["connectivity"],
                model_data["tip_node"],
                model_data["root_nodes"],
                model_data["midspan_node"],
                time_step_s=time_step_s,
                table=table,
            )
            result = solve_model(model, enforce_policy=False)
            rows = list(result.solver.get("time_history", []))
            if len(rows) != len(times) - 1:
                raise RuntimeError("Newmark history length differs from the frozen time grid")
            actual_times = np.asarray([float(row["time"]) for row in rows], dtype=np.float64)
            if not np.allclose(actual_times, times[1:], rtol=0.0, atol=1.0e-14):
                raise RuntimeError("Newmark history times differ from the common physical time grid")
            actual_midspan = _probe_values(rows, PROBE_LABEL)
            actual_tip = _probe_values(rows, TIP_LABEL)
            exact = oracle_histories[(cells, time_step_s)]
            errors = _error_metrics(actual_midspan, exact.displacement_probe, global_scale)
            energy = np.asarray(
                [float(row["strain_energy"]) + float(row["kinetic_energy"]) for row in rows],
                dtype=np.float64,
            )
            tail = energy[actual_times >= PULSE_END_TIME_S]
            tail_range = float(np.ptp(tail) / max(float(np.max(np.abs(tail))), np.finfo(float).tiny))
            factors_at_times = np.asarray([_load_factor(float(time)) for time in actual_times])
            full_factors = np.concatenate(([0.0], factors_at_times))
            full_tip = np.concatenate(([0.0], actual_tip))
            force_at_times = FORCE_N * full_factors
            external_work = float(np.sum(0.5 * (force_at_times[1:] + force_at_times[:-1]) * np.diff(full_tip)))
            final_energy = float(energy[-1])
            work_energy_relative = abs(final_energy - external_work) / max(
                abs(final_energy), abs(external_work), np.finfo(float).tiny
            )
            row = {
                "time_step_s": time_step_s,
                "step_count": int(len(rows)),
                "observation_end_time_s": OBSERVATION_END_TIME_S,
                "pulse_peak_time_s": PULSE_PEAK_TIME_S,
                "pulse_end_time_s": PULSE_END_TIME_S,
                "assembled_force_resultant_n": [0.0, 0.0, FORCE_N],
                "direct_status": str(result.status),
                **errors,
                "peak_midspan_displacement_m": float(np.max(np.abs(actual_midspan))),
                "maximum_dynamic_residual_norm_n": float(max(result.solver.get("residual_history", [0.0]))),
                "post_pulse_total_energy_relative_range": tail_range,
                "external_work_to_final_energy_relative_difference": work_energy_relative,
                "external_work_j": external_work,
                "final_total_energy_j": final_energy,
            }
            mesh_row["time_levels"].append(row)
            direct_curves[(cells, time_step_s)] = (actual_times, actual_midspan, exact.displacement_probe)
            state_arrays[f"direct_m{mesh_index}_dt{time_step_s:.7f}_uz_m"] = actual_midspan
            state_arrays[f"tip_direct_m{mesh_index}_dt{time_step_s:.7f}_uz_m"] = actual_tip
            state_arrays[f"total_energy_m{mesh_index}_dt{time_step_s:.7f}_j"] = energy
            for step, (time, value, reference) in enumerate(
                zip(actual_times, actual_midspan, exact.displacement_probe, strict=True), start=1
            ):
                csv_rows.append({
                    "mesh_cells": "x".join(map(str, cells)),
                    "time_step_s": time_step_s,
                    "step": step,
                    "time_s": float(time),
                    "midspan_uz_newmark_m": float(value),
                    "midspan_uz_semidiscrete_oracle_m": float(reference),
                    "difference_m": float(value - reference),
                })
        temporal_errors = [float(level["rms_normalized_by_global_oracle_peak"]) for level in mesh_row["time_levels"]]
        mesh_row["observed_time_refinement_orders"] = [
            math.log(temporal_errors[index] / temporal_errors[index + 1], 2.0)
            if temporal_errors[index] > 0.0 and temporal_errors[index + 1] > 0.0 else None
            for index in range(len(temporal_errors) - 1)
        ]

    finest_cells = MESH_LEVELS[-1]
    finest_oracle = oracle_histories[(finest_cells, min(TIME_STEPS_S))].displacement_probe
    spatial_rows = []
    for mesh_index, cells in enumerate(MESH_LEVELS):
        curve = oracle_histories[(cells, min(TIME_STEPS_S))].displacement_probe
        metrics = _error_metrics(curve, finest_oracle, global_scale)
        spatial_rows.append({"cells": list(cells), **metrics})
        state_arrays[f"finest_mesh_difference_m{mesh_index}_uz_m"] = curve - finest_oracle
    for mesh_row in mesh_rows.values():
        mesh_row["spatial_comparison_at_finest_time_step"] = next(
            row for row in spatial_rows if row["cells"] == mesh_row["cells"]
        )

    result_payload: dict[str, Any] = {
        "schema": "qf-j10-tet10-fixed-excitation-result-v1",
        "classification": "DEVELOPMENT_EXPLORATORY_NOT_QUALIFICATION",
        "execution_status": "COMPLETED_EXPLORATORY",
        "nodeid": NODEID,
        "source_head": run["identity"]["head"],
        "source_fingerprint": run["source_fingerprint"],
        "contract_sha256": contract_sha,
        "model": {
            "geometry_m": [LENGTH_M, WIDTH_M, HEIGHT_M],
            "material": {"young_modulus_pa": YOUNG_MODULUS_PA, "poisson_ratio": POISSON_RATIO, "density_kg_m3": DENSITY_KG_M3},
            "units": "SI",
            "mesh_family": "quadratic TET10; structured boxes split into six conforming tetrahedra per cube with shared midside nodes",
            "boundary_condition": "all three translations fixed on the complete x=0 face",
            "load": "negative Z nodal force at the x=L face center; common triangular 1 N pulse with peak at 1 ms and zero by 2 ms",
            "initial_conditions": "zero displacement and velocity",
            "newmark": {"beta": 0.25, "gamma": 0.5, "rayleigh_alpha_s_inv": 0.0, "rayleigh_beta_s": 0.0},
            "probe": {"position_m": MIDSPAN_PROBE.tolist(), "component": "UZ", "units": "m", "location": "fixed physical midspan center, away from the point load"},
            "point_load_limit": "The nodal tip load is spatially singular; the reported primary displacement probe is at a fixed midspan position away from that node.",
        },
        "environment": _environment(),
        "excitation": {
            "time_function": "triangular force, f(0)=0, f(1 ms)=-1 N, f(2 ms)=0 N, f(t)=0 afterward",
            "time_steps_s": list(TIME_STEPS_S),
            "observation_end_time_s": OBSERVATION_END_TIME_S,
            "same_physical_load_all_meshes": True,
            "same_physical_observation_times_all_meshes": True,
        },
        "reference": {
            "type": "full-order semidiscrete modal state-space oracle",
            "method": "generalized eigendecomposition and exact state transition per affine load step; no Newmark recurrence",
            "spatial_operator": "the same assembled consistent TET10 mass and stiffness matrices used for each direct run",
            "validates": "time integration on each assembled mesh/system",
            "does_not_validate": "TET10 spatial discretization against the continuum or an independent external solver",
            "spatial_mesh_comparison": "coarser semidiscrete response against the finest selected mesh at common physical times; descriptive only and not a continuum error",
        },
        "mesh_levels": [mesh_rows[cells] for cells in MESH_LEVELS],
        "spatial_sensitivity": spatial_rows,
        "normalization": {
            "global_oracle_peak_m": global_scale,
            "definition": "all temporal RMS and peak errors are normalized by the maximum absolute midspan oracle response over all four meshes at the finest common time step",
            "reason": "one shared scale avoids unstable relative errors near response zero crossings",
        },
        "criteria": {
            "formal_acceptance_thresholds": "none; time-step errors, energy indicators and spatial differences remain descriptive",
            "completion_invariants": "positive TET10 corner volumes, both physical points represented exactly, identical common load/time grids, force resultant (-1 N in Z), finite responses, and solver route returns completed results",
        },
        "interpretation": "This controlled study compares time integration against each mesh's own semidiscrete oracle and compares mesh-dependent semidiscrete curves at common physical points and times. It does not establish continuum convergence or external correlation.",
        "animation": {"status": "NOT_AVAILABLE", "reason": "the solver history records selected probes and energy summaries, not full nodal displacement fields at every time step"},
    }
    result_payload["states_npz"] = {
        "path": "tet10_fixed_excitation_states.npz",
        "sha256": _atomic_npz(output_dir / "tet10_fixed_excitation_states.npz", **state_arrays),
    }
    csv_path = output_dir / "tet10_fixed_excitation_history.csv"
    fields = ["mesh_cells", "time_step_s", "step", "time_s", "midspan_uz_newmark_m", "midspan_uz_semidiscrete_oracle_m", "difference_m"]
    with tempfile.NamedTemporaryFile(mode="w", dir=output_dir, prefix=csv_path.name + ".", suffix=".tmp", delete=False, newline="", encoding="utf-8") as stream:
        temporary_csv = Path(stream.name)
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(csv_rows)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary_csv, csv_path)
    result_payload["history_csv"] = {"path": csv_path.name, "sha256": _file_sha256(csv_path)}
    figures = _write_figures(output_dir, models, mesh_rows, direct_curves, oracle_histories)
    result_payload["figures"] = figures
    result_hash = _atomic_json(output_dir / "result.json", result_payload)
    _atomic_json(output_dir / "result.sha256.json", {"sha256": result_hash})
    return result_payload


def _write_figures(
    output_dir: Path,
    models: dict[tuple[int, int, int], dict[str, Any]],
    mesh_rows: dict[tuple[int, int, int], dict[str, Any]],
    direct_curves: dict[tuple[tuple[int, int, int], float], tuple[np.ndarray, np.ndarray, np.ndarray]],
    oracle_histories: dict[tuple[tuple[int, int, int], float], Any],
) -> dict[str, str]:
    mesh_path = output_dir / "tet10_fixed_excitation_meshes.png"
    figure = plt.figure(figsize=(12, 8))
    for index, cells in enumerate(MESH_LEVELS):
        axis = figure.add_subplot(2, 2, index + 1, projection="3d")
        _draw_mesh(axis, models[cells]["coordinates"], models[cells]["connectivity"])
        row = mesh_rows[cells]
        axis.set_title(f"{cells[0]}×{cells[1]}×{cells[2]} cubes; {row['free_dof_count']} DDL libres")
    figure.suptitle("TET10 cantilever: root fixed, common nodal pulse at tip center")
    figure.tight_layout()
    figure.savefig(mesh_path, dpi=160)
    plt.close(figure)

    time_path = output_dir / "tet10_fixed_excitation_time_refinement.png"
    figure, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True)
    colors = ("#356a75", "#b45845", "#667a42")
    for index, cells in enumerate(MESH_LEVELS):
        axis = axes.flat[index]
        for color, time_step_s in zip(colors, TIME_STEPS_S, strict=True):
            times, direct, _oracle = direct_curves[(cells, time_step_s)]
            axis.plot(times * 1.0e3, direct * 1.0e6, color=color, linewidth=1.1, label=f"Newmark Δt={time_step_s * 1.0e3:g} ms")
        exact = oracle_histories[(cells, min(TIME_STEPS_S))]
        axis.plot(exact.times * 1.0e3, exact.displacement_probe * 1.0e6, color="black", linestyle="--", linewidth=1.0, label="oracle semi-discret fin")
        axis.axvline(PULSE_END_TIME_S * 1.0e3, color="#888888", linestyle=":", linewidth=0.8)
        axis.set_title("Maillage " + "×".join(map(str, cells)))
        axis.set_ylabel("UZ au milieu [µm]")
        axis.grid(True, alpha=0.2)
    for axis in axes[-1, :]:
        axis.set_xlabel("Temps physique [ms]")
    axes.flat[0].legend(fontsize=7, loc="best")
    figure.suptitle("Même impulsion physique, même point de mesure, plusieurs Δt")
    figure.tight_layout()
    figure.savefig(time_path, dpi=160)
    plt.close(figure)

    spatial_path = output_dir / "tet10_fixed_excitation_mesh_sensitivity.png"
    figure, axis = plt.subplots(figsize=(8, 4.5))
    finest = MESH_LEVELS[-1]
    finest_history = oracle_histories[(finest, min(TIME_STEPS_S))]
    for cells in MESH_LEVELS[:-1]:
        history = oracle_histories[(cells, min(TIME_STEPS_S))]
        axis.plot(history.times * 1.0e3, history.displacement_probe * 1.0e6, label="oracle " + "×".join(map(str, cells)))
    axis.plot(finest_history.times * 1.0e3, finest_history.displacement_probe * 1.0e6, color="black", linestyle="--", label="oracle " + "×".join(map(str, finest)))
    axis.set(xlabel="Temps physique [ms]", ylabel="UZ au milieu [µm]", title="Sensibilité spatiale semi-discrète; comparaison descriptive")
    axis.grid(True, alpha=0.2)
    axis.legend()
    figure.tight_layout()
    figure.savefig(spatial_path, dpi=160)
    plt.close(figure)
    return {path.name: _file_sha256(path) for path in (mesh_path, time_path, spatial_path)}


def _draw_mesh(axis: Any, coordinates: np.ndarray, connectivity: np.ndarray) -> None:
    edges: set[tuple[int, int]] = set()
    for tet in connectivity:
        for left, right in itertools.combinations(tet[:4], 2):
            edges.add(tuple(sorted((int(left), int(right)))))
    for left, right in edges:
        axis.plot(*coordinates[[left, right]].T, color="#557464", linewidth=0.4, alpha=0.6)
    axis.scatter(*TIP_LOAD_POINT, color="#b5483a", s=10)
    axis.scatter(*MIDSPAN_PROBE, color="#295a7a", s=10)
    axis.set(xlabel="x [m]", ylabel="y [m]", zlabel="z [m]")
    axis.set_box_aspect((LENGTH_M, WIDTH_M, HEIGHT_M))
