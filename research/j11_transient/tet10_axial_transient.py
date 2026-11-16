"""J11 TET10 transient study against an independent guided-bar continuum solution."""

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
from matplotlib.animation import FuncAnimation, PillowWriter
import numpy as np
import scipy
import threadpoolctl

from solveur.api import solve_model
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.model import FiniteElementModel
from solveur.elements.solid.tet10 import Tet10Element
from solveur.io.dynamic_checkpoint import NpzDynamicCheckpointStore
from solveur.verification.transient_modal_oracle import PiecewiseLinearModalOracle

from research.j11_transient.axial_bar_reference import (
    axial_bar_response,
    constrained_axial_modulus,
)


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "research/j11_transient/contracts/tet10_axial_bar_contract.json"
NODEID = "tests/verification/test_j11_tet10_axial_transient.py::test_j11_tet10_axial_bar_time_mesh_and_animation"
LENGTH_M, WIDTH_M, HEIGHT_M = 2.0, 0.4, 0.4
YOUNG_MODULUS_PA, POISSON_RATIO, DENSITY_KG_M3 = 70.0e9, 0.30, 2700.0
CROSS_SECTION_M2 = WIDTH_M * HEIGHT_M
FORCE_N = 1.0
FORCE_SEGMENTS = ((0.0, 1.0e-3, 0.0, FORCE_N), (1.0e-3, 2.0e-3, FORCE_N, 0.0))
OBSERVATION_END_S = 8.0e-3
MESH_LEVELS = (2, 4, 8, 16)
TIME_STEPS_S = (1.0e-4, 5.0e-5, 2.5e-5)
PROBE_POSITION_M = np.asarray((1.0, WIDTH_M / 2.0, HEIGHT_M / 2.0), dtype=np.float64)
TIP_POSITION_M = np.asarray((LENGTH_M, WIDTH_M / 2.0, HEIGHT_M / 2.0), dtype=np.float64)
AMPLIFICATION = 1.0e8
CHECKPOINT_STRIDE = 8
CONTINUUM_MODES = 1024


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes().replace(b"\r\n", b"\n"))


def _atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".", suffix=".tmp", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _atomic_json(path: Path, payload: dict[str, Any]) -> str:
    encoded = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    _atomic_bytes(path, encoded)
    return _sha256_bytes(encoded)


def _atomic_npz(path: Path, **arrays: np.ndarray) -> str:
    buffer = io.BytesIO()
    np.savez_compressed(buffer, **arrays)
    encoded = buffer.getvalue()
    _atomic_bytes(path, encoded)
    return _sha256_bytes(encoded)


def _attempt_output_dir() -> tuple[Path, dict[str, Any]]:
    if os.environ.get("QF_DEVELOPMENT_AUTONOMOUS") != "1":
        raise RuntimeError("J11 transient outputs require the registered development launcher")
    temporary = Path(os.environ["TMP"]).resolve(strict=True)
    attempt_dir = temporary.parent
    record_path = attempt_dir / "run.json"
    if not record_path.is_file():
        raise RuntimeError("The development runner attempt record is missing")
    run = json.loads(record_path.read_text(encoding="utf-8"))
    if run.get("state") != "RUNNING" or run.get("worktree_id") != "j11" or run.get("target") != [NODEID]:
        raise RuntimeError("The development runner does not identify this exact J11 transient node")
    expected_root = (ROOT / ".codex/development-runs/worktrees/j11").resolve()
    try:
        attempt_dir.resolve().relative_to(expected_root)
    except ValueError as exc:
        raise RuntimeError("J11 output directory is outside its registered attempt namespace") from exc
    output = attempt_dir / "output" / "j11_tet10_axial_bar"
    output.mkdir(parents=True, exist_ok=False)
    return output, run


def _mesh(nx: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build a conforming quadratic mesh with one cell across each guided direction."""
    if nx not in MESH_LEVELS:
        raise ValueError(f"Unexpected axial mesh level: {nx}")
    coordinates: list[np.ndarray] = []
    vertex_ids: dict[tuple[int, int, int], int] = {}
    for k in range(2):
        for j in range(2):
            for i in range(nx + 1):
                vertex_ids[i, j, k] = len(coordinates)
                coordinates.append(np.asarray((LENGTH_M * i / nx, WIDTH_M * j, HEIGHT_M * k), dtype=np.float64))
    midpoint_ids: dict[tuple[int, int], int] = {}
    elements: list[list[int]] = []
    local_edges = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
    for i in range(nx):
        origin = np.asarray((i, 0, 0), dtype=int)
        for permutation in itertools.permutations((0, 1, 2)):
            p0 = origin
            p1 = origin.copy()
            p1[permutation[0]] += 1
            p2 = p1.copy()
            p2[permutation[1]] += 1
            p3 = origin + 1
            corners = [vertex_ids[tuple(point)] for point in (p0, p1, p2, p3)]
            corner_xyz = np.asarray([coordinates[node] for node in corners])
            determinant = float(np.linalg.det((corner_xyz[1:] - corner_xyz[0]).T))
            if determinant < 0.0:
                corners[1], corners[2] = corners[2], corners[1]
            elif determinant == 0.0:
                raise RuntimeError("Generated TET10 cell has a zero corner Jacobian")
            connectivity = list(corners)
            for left, right in local_edges:
                edge = tuple(sorted((corners[left], corners[right])))
                if edge not in midpoint_ids:
                    midpoint_ids[edge] = len(coordinates)
                    coordinates.append(0.5 * (coordinates[edge[0]] + coordinates[edge[1]]))
                connectivity.append(midpoint_ids[edge])
            elements.append(connectivity)
    xyz = np.asarray(coordinates, dtype=np.float64)
    conn = np.asarray(elements, dtype=np.int64)
    corner_volumes = np.asarray([Tet10Element.corner_signed_volume(xyz[row]) for row in conn], dtype=np.float64)
    if not np.all(corner_volumes > 0.0):
        raise RuntimeError("Generated TET10 mesh contains an inverted element")
    return xyz, conn, corner_volumes


def _uniform_tip_force(nx: int, coordinates: np.ndarray, connectivity: np.ndarray) -> tuple[list[dict[str, Any]], np.ndarray]:
    """Integrate uniform axial traction on six-node TET10 boundary triangles."""
    edge_local_index = {
        tuple(sorted(edge)): 4 + index
        for index, edge in enumerate(((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3)))
    }
    nodal = np.zeros(len(coordinates), dtype=np.float64)
    expected_area = CROSS_SECTION_M2
    integrated_area = 0.0
    tolerance = 1.0e-12
    for tet in connectivity:
        for opposite in range(4):
            local_corners = tuple(index for index in range(4) if index != opposite)
            corner_nodes = [int(tet[index]) for index in local_corners]
            face_xyz = coordinates[corner_nodes]
            if not np.all(np.isclose(face_xyz[:, 0], LENGTH_M, rtol=0.0, atol=tolerance)):
                continue
            area = 0.5 * float(np.linalg.norm(np.cross(face_xyz[1] - face_xyz[0], face_xyz[2] - face_xyz[0])))
            if area <= 0.0:
                raise RuntimeError("The TET10 top-face integration found a degenerate triangle")
            integrated_area += area
            for left_pos, right_pos in ((0, 1), (1, 2), (2, 0)):
                left_local = local_corners[left_pos]
                right_local = local_corners[right_pos]
                mid_local = edge_local_index[tuple(sorted((left_local, right_local)))]
                mid_node = int(tet[mid_local])
                nodal[mid_node] += FORCE_N * area / (expected_area * 3.0)
    if not math.isclose(integrated_area, expected_area, rel_tol=0.0, abs_tol=1.0e-12):
        raise RuntimeError(f"Integrated top surface area {integrated_area} differs from {expected_area}")
    if not math.isclose(math.fsum(float(value) for value in nodal), FORCE_N, rel_tol=0.0, abs_tol=1.0e-13):
        raise RuntimeError("Consistent surface load does not sum to the declared total force")
    first_moment_y = math.fsum(float(nodal[i] * coordinates[i, 1]) for i in range(len(nodal)))
    first_moment_z = math.fsum(float(nodal[i] * coordinates[i, 2]) for i in range(len(nodal)))
    if not math.isclose(first_moment_y, FORCE_N * WIDTH_M / 2.0, rel_tol=0.0, abs_tol=1.0e-13):
        raise RuntimeError("Uniform top load does not have the correct y first moment")
    if not math.isclose(first_moment_z, FORCE_N * HEIGHT_M / 2.0, rel_tol=0.0, abs_tol=1.0e-13):
        raise RuntimeError("Uniform top load does not have the correct z first moment")
    loads = [
        {"node": int(node), "dof": "UX", "value": float(value)}
        for node, value in enumerate(nodal)
        if value != 0.0
    ]
    return loads, nodal


def _load_table() -> list[dict[str, float]]:
    return [
        {"time": 0.0, "factor": 0.0},
        {"time": 1.0e-3, "factor": 1.0},
        {"time": 2.0e-3, "factor": 0.0},
        {"time": OBSERVATION_END_S, "factor": 0.0},
    ]


def _model(
    coordinates: np.ndarray,
    connectivity: np.ndarray,
    loads: list[dict[str, Any]],
    *,
    dt: float,
    checkpoint_path: Path | None = None,
) -> FiniteElementModel:
    steps = int(round(OBSERVATION_END_S / dt))
    if not math.isclose(steps * dt, OBSERVATION_END_S, rel_tol=0.0, abs_tol=1.0e-14):
        raise ValueError("Every frozen J11 time step must divide the observation horizon exactly")
    root_nodes = np.flatnonzero(np.isclose(coordinates[:, 0], 0.0, rtol=0.0, atol=1.0e-12))
    fixed_dofs = []
    root_set = set(map(int, root_nodes))
    for node in range(len(coordinates)):
        components = ["UY", "UZ"]
        if node in root_set:
            components.append("UX")
        fixed_dofs.append({"node": node, "dofs": components})
    parameters: dict[str, Any] = {
        "time_step": dt,
        "steps": steps,
        "newmark_beta": 0.25,
        "newmark_gamma": 0.5,
        "rayleigh_alpha": 0.0,
        "rayleigh_beta": 0.0,
        "load_table": _load_table(),
        "record_time_history": True,
        "history_probes": [
            {"node": int(_exact_node(coordinates, PROBE_POSITION_M)), "dof": "UX", "label": "midspan_ux"},
            {"node": int(_exact_node(coordinates, TIP_POSITION_M)), "dof": "UX", "label": "tip_center_ux"},
        ],
        "postprocess_mode": "summary",
    }
    if checkpoint_path is not None:
        parameters.update(
            {
                "checkpoint_path": str(checkpoint_path),
                "checkpoint_interval": CHECKPOINT_STRIDE,
                "checkpoint_keep_steps": True,
            }
        )
    return FiniteElementModel.from_raw(
        nodes=coordinates.tolist(),
        elements=[{"type": "TET10", "nodes": row.tolist(), "material": "bar_material"} for row in connectivity],
        materials={
            "bar_material": {
                "type": "isotropic_3d",
                "E": YOUNG_MODULUS_PA,
                "nu": POISSON_RATIO,
                "density": DENSITY_KG_M3,
            }
        },
        fixed_dofs=fixed_dofs,
        loads=loads,
        analysis={"type": "transient_dynamic", "method": "newmark", **parameters},
        units={"length": "m", "force": "N", "time": "s", "mass": "kg"},
        verification_profile="quick",
    )


def _exact_node(coordinates: np.ndarray, position: np.ndarray) -> int:
    distances = np.linalg.norm(coordinates - position, axis=1)
    node = int(np.argmin(distances))
    if distances[node] > 1.0e-12:
        raise RuntimeError(f"Declared physical probe {position.tolist()} is not a mesh node")
    return node


def _metrics(actual: np.ndarray, reference: np.ndarray, scale: float) -> dict[str, float]:
    difference = np.asarray(actual, dtype=np.float64) - np.asarray(reference, dtype=np.float64)
    return {
        "rms_absolute_error_m": float(np.sqrt(np.mean(difference**2))),
        "peak_absolute_error_m": float(np.max(np.abs(difference))),
        "rms_normalized_to_shared_continuum_peak": float(np.sqrt(np.mean(difference**2)) / scale),
        "peak_normalized_to_shared_continuum_peak": float(np.max(np.abs(difference)) / scale),
    }


def _environment() -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "matplotlib": metadata.version("matplotlib"),
        "pillow": metadata.version("Pillow"),
        "threadpools": [
            {key: pool.get(key) for key in ("user_api", "internal_api", "version", "num_threads")}
            for pool in threadpoolctl.threadpool_info()
        ],
    }


def _atomic_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", dir=path.parent, prefix=path.name + ".", suffix=".tmp", delete=False,
        newline="", encoding="utf-8",
    ) as stream:
        temporary = Path(stream.name)
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    return _sha256_file(path)


def _draw_meshes(meshes: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]], path: Path) -> None:
    figure = plt.figure(figsize=(10, 6))
    axis = figure.add_subplot(111, projection="3d")
    colors = ("#a7c7d5", "#6198b4", "#286b8e", "#143f5e")
    for (nx, (coordinates, connectivity, _)), color in zip(meshes.items(), colors, strict=True):
        if nx != 4:
            continue
        edge_set: set[tuple[int, int]] = set()
        for tet in connectivity:
            for left, right in itertools.combinations(tet[:4], 2):
                edge_set.add(tuple(sorted((int(left), int(right)))))
        for left, right in edge_set:
            axis.plot(*coordinates[[left, right]].T, color=color, linewidth=0.65, alpha=0.7)
    axis.set(xlabel="x [m]", ylabel="y [m]", zlabel="z [m]", title="Maillage TET10 — exemple 4 × 1 × 1")
    axis.set_box_aspect((LENGTH_M, WIDTH_M, HEIGHT_M))
    figure.tight_layout()
    figure.savefig(path, dpi=170)
    plt.close(figure)


def _plot_histories(
    rows: list[dict[str, Any]],
    mesh_results: list[dict[str, Any]],
    arrays: dict[str, np.ndarray],
    path: Path,
) -> None:
    figure, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    for result in mesh_results:
        nx = result["cells_x"]
        key = f"spatial_nx{nx}_dt{TIME_STEPS_S[-1]:.8g}"
        times = arrays[f"{key}_times_s"]
        qf = arrays[f"{key}_qf_m"]
        exact = arrays[f"{key}_continuum_m"]
        axes[0].plot(times * 1e3, qf * 1e9, label=f"QF nx={nx}")
        if nx == MESH_LEVELS[-1]:
            axes[0].plot(times * 1e3, exact * 1e9, "k--", linewidth=1.5, label="référence continue")
        axes[1].plot(times * 1e3, (qf - exact) * 1e9, label=f"nx={nx}")
    axes[0].set_ylabel("Ux au milieu [nm]")
    axes[0].legend(ncol=3)
    axes[1].set(xlabel="Temps [ms]", ylabel="QF − référence [nm]")
    axes[1].legend(ncol=4)
    figure.suptitle("Réponse axiale TET10 sous force répartie")
    figure.tight_layout()
    figure.savefig(path, dpi=170)
    plt.close(figure)


def _plot_time_refinement(arrays: dict[str, np.ndarray], path: Path) -> None:
    figure, axis = plt.subplots(figsize=(10, 5.5))
    nx = 8
    for dt in TIME_STEPS_S:
        key = f"temporal_nx{nx}_dt{dt:.8g}"
        times = arrays[f"{key}_times_s"]
        axis.plot(times * 1e3, arrays[f"{key}_qf_m"] * 1e9, label=f"Newmark Δt={dt * 1e6:g} µs")
    reference_key = f"spatial_nx{nx}_dt{TIME_STEPS_S[-1]:.8g}"
    axis.plot(
        arrays[f"{reference_key}_times_s"] * 1e3,
        arrays[f"{reference_key}_continuum_m"] * 1e9,
        "k--",
        linewidth=1.7,
        label="solution continue 1D",
    )
    axis.set(xlabel="Temps [ms]", ylabel="Ux au milieu [nm]", title="Raffinement temporel à maillage nx=8 constant")
    axis.legend(ncol=2)
    figure.tight_layout()
    figure.savefig(path, dpi=170)
    plt.close(figure)


def _make_animation(
    path: Path,
    coordinates: np.ndarray,
    center_nodes: np.ndarray,
    times: np.ndarray,
    snapshots_ux: np.ndarray,
) -> None:
    figure = plt.figure(figsize=(9, 5))
    axis = figure.add_subplot(111, projection="3d")
    center = coordinates[center_nodes]
    axis.plot(center[:, 0], center[:, 1], center[:, 2], "--", color="#777777", label="axe non déformé")
    line, = axis.plot([], [], [], color="#c74343", linewidth=3, label="état Newmark archivé")
    title = axis.set_title("")
    max_amplified = AMPLIFICATION * float(np.max(np.abs(snapshots_ux)))
    axis.set_xlim(-max_amplified * 1.2, LENGTH_M + max_amplified * 1.2)
    axis.set_ylim(0.0, WIDTH_M)
    axis.set_zlim(0.0, HEIGHT_M)
    axis.set(xlabel="x déformé [m]", ylabel="y [m]", zlabel="z [m]")
    axis.set_box_aspect((LENGTH_M, WIDTH_M, HEIGHT_M))
    axis.legend(loc="upper left")

    def update(frame: int) -> tuple[Any, ...]:
        displacement = AMPLIFICATION * snapshots_ux[frame]
        line.set_data_3d(center[:, 0] + displacement, center[:, 1], center[:, 2])
        title.set_text(f"t = {times[frame] * 1e3:.2f} ms — déplacement × {AMPLIFICATION:.0e}")
        return line, title

    animation = FuncAnimation(figure, update, frames=len(times), blit=False, interval=100)
    animation.save(path, writer=PillowWriter(fps=8), dpi=110)
    plt.close(figure)


def run_study() -> dict[str, Any]:
    output_dir, run = _attempt_output_dir()
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    contract_sha = _canonical_sha256(CONTRACT_PATH)
    for item in contract["source_identity"]:
        if _canonical_sha256(ROOT / item["path"]) != item["canonical_sha256"]:
            raise RuntimeError(f"J11 source differs from the frozen contract: {item['path']}")

    axial_modulus = constrained_axial_modulus(YOUNG_MODULUS_PA, POISSON_RATIO)
    geometry: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]] = {nx: _mesh(nx) for nx in MESH_LEVELS}
    exact_probe = _exact_node(geometry[8][0], PROBE_POSITION_M)
    del exact_probe
    scale_times = TIME_STEPS_S[-1] * np.arange(1, int(round(OBSERVATION_END_S / TIME_STEPS_S[-1])) + 1)
    reference_fine = axial_bar_response(
        scale_times,
        length_m=LENGTH_M,
        area_m2=CROSS_SECTION_M2,
        density_kg_m3=DENSITY_KG_M3,
        axial_modulus_pa=axial_modulus,
        force_segments=FORCE_SEGMENTS,
        position_m=PROBE_POSITION_M[0],
        mode_count=CONTINUUM_MODES,
    )
    global_scale = float(np.max(np.abs(reference_fine)))
    if not math.isfinite(global_scale) or global_scale <= np.finfo(float).tiny:
        raise RuntimeError("The independent continuum reference has no usable nonzero scale")

    arrays: dict[str, np.ndarray] = {}
    mesh_results: list[dict[str, Any]] = []
    temporal_results: list[dict[str, Any]] = []
    csv_rows: list[dict[str, Any]] = []
    qf_cache: dict[tuple[int, float], dict[str, Any]] = {}
    checkpoint_path: Path | None = None

    def solve_level(nx: int, dt: float, *, record_states: bool = False) -> dict[str, Any]:
        nonlocal checkpoint_path
        cache_key = (nx, dt)
        if cache_key in qf_cache:
            return qf_cache[cache_key]
        coordinates, connectivity, volumes = geometry[nx]
        loads, nodal_load = _uniform_tip_force(nx, coordinates, connectivity)
        probe_node = _exact_node(coordinates, PROBE_POSITION_M)
        tip_node = _exact_node(coordinates, TIP_POSITION_M)
        model = _model(coordinates, connectivity, loads, dt=dt)
        dofs = model.dof_manager()
        probe_index = dofs.index(probe_node, "UX")
        full_load = GlobalAssembler().assemble_loads(model, dofs)
        assembled_resultant = [
            math.fsum(float(full_load[dofs.index(node, component)]) for node in range(len(coordinates)))
            for component in ("UX", "UY", "UZ")
        ]
        if not np.allclose(assembled_resultant, (FORCE_N, 0.0, 0.0), rtol=0.0, atol=1.0e-12):
            raise RuntimeError("The QF assembled load resultant differs from the frozen axial 1 N force")
        if not np.all(np.isclose(volumes, volumes[0], rtol=0.0, atol=1.0e-14)):
            raise RuntimeError("The regular axial TET10 mesh unexpectedly has unequal corner volumes")
        oracle_model = _model(coordinates, connectivity, loads, dt=TIME_STEPS_S[-1])
        oracle = PiecewiseLinearModalOracle(oracle_model)
        if oracle.eigenvalues.size == 0:
            raise RuntimeError("The constrained TET10 model has no positive semidiscrete modes")
        steps = int(round(OBSERVATION_END_S / dt))
        times_expected = dt * np.arange(1, steps + 1, dtype=np.float64)
        factors = np.asarray([_force_factor(float(time)) for time in times_expected], dtype=np.float64)
        semidiscrete = oracle.propagate(full_load, factors, dt, displacement_probe_index=probe_index)
        state_checkpoint = None
        if record_states:
            state_checkpoint = output_dir / f"tet10_nx{nx}_state.npz"
            checkpoint_path = state_checkpoint
            model = _model(coordinates, connectivity, loads, dt=dt, checkpoint_path=state_checkpoint)
        result = solve_model(model, enforce_policy=False)
        history = list(result.solver.get("time_history", []))
        if len(history) != steps:
            raise RuntimeError("The QF Newmark history length differs from the frozen time grid")
        times = np.asarray([float(row["time"]) for row in history], dtype=np.float64)
        qf_values = np.asarray([float(row["probes"]["midspan_ux"]["displacement"]) for row in history])
        if not np.array_equal(times, times_expected):
            raise RuntimeError("The QF Newmark history does not use the contracted physical time grid")
        continuum = axial_bar_response(
            times,
            length_m=LENGTH_M,
            area_m2=CROSS_SECTION_M2,
            density_kg_m3=DENSITY_KG_M3,
            axial_modulus_pa=axial_modulus,
            force_segments=FORCE_SEGMENTS,
            position_m=PROBE_POSITION_M[0],
            mode_count=CONTINUUM_MODES,
        )
        if not np.allclose(continuum, reference_fine, rtol=0.0, atol=1e-14 * global_scale):
            raise RuntimeError("The continuum reference changed between identical physical observation times")
        semidiscrete_values = np.asarray(semidiscrete.displacement_probe, dtype=np.float64)
        if semidiscrete_values.shape != qf_values.shape:
            raise RuntimeError("Semidiscrete oracle and Newmark histories have different time grids")
        residuals = np.asarray(result.solver.get("residual_history", []), dtype=np.float64)
        if residuals.size != steps or not np.all(np.isfinite(residuals)):
            raise RuntimeError("The QF Newmark dynamic residual history is incomplete or nonfinite")
        key = f"{'spatial' if dt == TIME_STEPS_S[-1] else 'temporal'}_nx{nx}_dt{dt:.8g}"
        arrays[f"{key}_times_s"] = times
        arrays[f"{key}_qf_m"] = qf_values
        arrays[f"{key}_semidiscrete_m"] = semidiscrete_values
        arrays[f"{key}_continuum_m"] = continuum
        for index, time in enumerate(times):
            csv_rows.append(
                {
                    "route": key.split("_", 1)[0],
                    "nx": nx,
                    "dt_s": dt,
                    "step": index + 1,
                    "time_s": float(time),
                    "qf_newmark_ux_m": float(qf_values[index]),
                    "qf_semidiscrete_oracle_ux_m": float(semidiscrete_values[index]),
                    "independent_continuum_ux_m": float(continuum[index]),
                }
            )
        payload = {
            "nx": nx,
            "dt_s": dt,
            "steps": steps,
            "node_count": int(len(coordinates)),
            "element_count": int(len(connectivity)),
            "free_dof_count": int(oracle.reducer.stiffness.shape[0]),
            "probe_node": probe_node,
            "probe_position_m": coordinates[probe_node].tolist(),
            "tip_center_node": tip_node,
            "integrated_area_m2": CROSS_SECTION_M2,
            "consistent_nodal_force_sum_n": math.fsum(float(value) for value in nodal_load),
            "force_first_moments_n_m": [
                math.fsum(float(nodal_load[i] * coordinates[i, j]) for i in range(len(nodal_load)))
                for j in (1, 2)
            ],
            "minimum_corner_volume_m3": float(np.min(volumes)),
            "first_semidiscrete_frequency_hz": float(math.sqrt(float(oracle.eigenvalues[0])) / (2.0 * math.pi)),
            "newmark_status": result.status,
            "maximum_dynamic_residual_n": float(np.max(residuals)),
            "newmark_to_semidiscrete": _metrics(qf_values, semidiscrete_values, global_scale),
            "semidiscrete_to_continuum": _metrics(semidiscrete_values, continuum, global_scale),
            "newmark_to_continuum": _metrics(qf_values, continuum, global_scale),
            "checkpoint_names": [],
        }
        if record_states:
            assert state_checkpoint is not None
            checkpoint_names = sorted(
                path.name for path in output_dir.glob(f"{state_checkpoint.stem}.step*.npz")
            )
            payload["checkpoint_names"] = checkpoint_names
            if not checkpoint_names:
                raise RuntimeError("No durable step checkpoints were emitted for the animation states")
        qf_cache[cache_key] = {
            "payload": payload,
            "coordinates": coordinates,
            "connectivity": connectivity,
            "times": times,
            "qf": qf_values,
            "oracle": semidiscrete_values,
            "continuum": continuum,
            "result": result,
        }
        return qf_cache[cache_key]

    for nx in MESH_LEVELS:
        solved = solve_level(nx, TIME_STEPS_S[-1], record_states=(nx == MESH_LEVELS[-1]))
        mesh_results.append({"cells_x": nx, **solved["payload"]})
    for dt in TIME_STEPS_S:
        solved = solve_level(8, dt)
        temporal_results.append(solved["payload"])

    finest_time_key = f"spatial_nx8_dt{TIME_STEPS_S[-1]:.8g}"
    finest_time_alias = f"temporal_nx8_dt{TIME_STEPS_S[-1]:.8g}"
    for quantity in ("times_s", "qf_m", "semidiscrete_m", "continuum_m"):
        arrays[f"{finest_time_alias}_{quantity}"] = arrays[f"{finest_time_key}_{quantity}"]

    temporal_orders: list[float | None] = []
    temporal_errors = [row["newmark_to_semidiscrete"]["rms_normalized_to_shared_continuum_peak"] for row in temporal_results]
    for index in range(len(temporal_errors) - 1):
        coarse, fine = float(temporal_errors[index]), float(temporal_errors[index + 1])
        temporal_orders.append(math.log(coarse / fine, 2.0) if coarse > 0.0 and fine > 0.0 else None)

    fine_exact_512 = axial_bar_response(
        scale_times,
        length_m=LENGTH_M,
        area_m2=CROSS_SECTION_M2,
        density_kg_m3=DENSITY_KG_M3,
        axial_modulus_pa=axial_modulus,
        force_segments=FORCE_SEGMENTS,
        position_m=PROBE_POSITION_M[0],
        mode_count=CONTINUUM_MODES // 2,
    )
    truncation_error = _metrics(reference_fine, fine_exact_512, global_scale)

    fine = qf_cache[(MESH_LEVELS[-1], TIME_STEPS_S[-1])]
    checkpoint_store = NpzDynamicCheckpointStore()
    checkpoint_names = fine["payload"]["checkpoint_names"]
    checkpoint_states = [checkpoint_store.load(output_dir / name) for name in checkpoint_names]
    checkpoint_states.sort(key=lambda state: state.completed_step)
    if any(
        right.completed_step - left.completed_step != CHECKPOINT_STRIDE
        for left, right in zip(checkpoint_states, checkpoint_states[1:])
    ):
        raise RuntimeError("The archived animation checkpoints do not follow the frozen temporal stride")
    snapshot_times = np.asarray([state.time for state in checkpoint_states], dtype=np.float64)
    snapshot_vectors = np.asarray([state.displacement for state in checkpoint_states], dtype=np.float64)
    fine_dofs = fine["result"].dofs
    center_nodes = np.asarray(
        [
            _exact_node(fine["coordinates"], np.asarray((float(x), WIDTH_M / 2.0, HEIGHT_M / 2.0)))
            for x in np.linspace(0.0, LENGTH_M, 2 * MESH_LEVELS[-1] + 1)
        ],
        dtype=np.int64,
    )
    snapshots_ux = np.asarray(
        [[float(state[dofs_index]) for dofs_index in (fine_dofs.index(int(node), "UX") for node in center_nodes)] for state in snapshot_vectors],
        dtype=np.float64,
    )
    initial_time = np.asarray([0.0], dtype=np.float64)
    initial_snapshots = np.zeros((1, len(center_nodes)), dtype=np.float64)
    animation_times = np.concatenate((initial_time, snapshot_times))
    animation_ux = np.concatenate((initial_snapshots, snapshots_ux), axis=0)

    mesh_arrays: dict[str, np.ndarray] = {}
    for nx, (coordinates, connectivity, volumes) in geometry.items():
        mesh_arrays[f"mesh_nx{nx}_coordinates_m"] = coordinates
        mesh_arrays[f"mesh_nx{nx}_connectivity_tet10"] = connectivity
        mesh_arrays[f"mesh_nx{nx}_corner_volumes_m3"] = volumes
    state_path = output_dir / "tet10_axial_bar_states.npz"
    state_sha = _atomic_npz(
        state_path,
        **mesh_arrays,
        animation_times_s=animation_times,
        animation_centerline_nodes=center_nodes,
        animation_centerline_ux_m=animation_ux,
        animation_full_state_times_s=np.concatenate((initial_time, snapshot_times)),
        animation_full_state_displacements=np.vstack((np.zeros((1, fine_dofs.ndof)), snapshot_vectors)),
    )
    history_path = output_dir / "tet10_axial_bar_history.csv"
    history_sha = _atomic_csv(
        history_path,
        csv_rows,
        ["route", "nx", "dt_s", "step", "time_s", "qf_newmark_ux_m", "qf_semidiscrete_oracle_ux_m", "independent_continuum_ux_m"],
    )
    mesh_figure = output_dir / "tet10_axial_bar_mesh.png"
    _draw_meshes(geometry, mesh_figure)
    history_figure = output_dir / "tet10_axial_bar_history.png"
    _plot_histories(csv_rows, mesh_results, arrays, history_figure)
    time_figure = output_dir / "tet10_axial_bar_time_refinement.png"
    _plot_time_refinement(arrays, time_figure)
    animation_path = output_dir / "tet10_axial_bar_animation.gif"
    _make_animation(animation_path, fine["coordinates"], center_nodes, animation_times, animation_ux)

    result_payload: dict[str, Any] = {
        "schema": "qf-j11-tet10-guided-axial-transient-v1",
        "classification": "DEVELOPMENT_EXPLORATORY_NOT_QUALIFICATION",
        "execution_status": "COMPLETED_EXPLORATORY",
        "contract_id": contract["contract_id"],
        "contract_sha256": contract_sha,
        "nodeid": NODEID,
        "source_head": run["identity"]["head"],
        "source_fingerprint": run["source_fingerprint"],
        "model": {
            "geometry_m": {"length_x": LENGTH_M, "width_y": WIDTH_M, "height_z": HEIGHT_M},
            "material": {"young_modulus_pa": YOUNG_MODULUS_PA, "poisson_ratio": POISSON_RATIO, "density_kg_m3": DENSITY_KG_M3},
            "constitutive_axial_modulus_pa": axial_modulus,
            "one_dimensional_wave_speed_m_s": math.sqrt(axial_modulus / DENSITY_KG_M3),
            "element": "quadratic TET10, consistent mass",
            "mass_matrix": "consistent mass assembled by QF GlobalAssembler",
            "mesh_levels_cells_x_y_z": [[nx, 1, 1] for nx in MESH_LEVELS],
            "boundary_conditions": "UX fixed at x=0; UY and UZ fixed at every node (transversely guided bar)",
            "initial_conditions": "zero displacement and velocity",
            "load": "uniform axial traction-equivalent nodal load on x=L, 1 N total, quadratic triangle consistent integration",
            "load_time_function": "0 N at 0 ms, linear to +1 N at 1 ms, linear to 0 N at 2 ms, zero afterward",
            "primary_probe": {"position_m": PROBE_POSITION_M.tolist(), "component": "UX", "units": "m"},
            "newmark": {"beta": 0.25, "gamma": 0.5, "rayleigh_alpha_s_inv": 0.0, "rayleigh_beta_s": 0.0},
        },
        "independent_reference": {
            "type": "continuum fixed-free axial-bar modal series",
            "equation": "rho A u_tt = (lambda + 2 mu) A u_xx",
            "wave_speed_m_s": math.sqrt(axial_modulus / DENSITY_KG_M3),
            "boundary_conditions": "u(0,t)=0; (lambda+2 mu) A u_x(L,t)=F(t)",
            "initial_conditions": "u(x,0)=0 and u_t(x,0)=0",
            "modal_count": CONTINUUM_MODES,
            "truncation_comparison_512_vs_1024": truncation_error,
            "scope": "independent of QF M/K assembly; exact continuum solution for the stated transverse-guidance constraints and uniform axial end force",
            "limitation": "this guided-bar configuration is not the free-sided J10 cantilever; its reference is not transferable to J10 cantilever results",
        },
        "normalization": {
            "formula": "RMS and peak absolute difference divided by the global peak absolute continuum displacement on the fixed physical comparison grid",
            "global_continuum_peak_m": global_scale,
            "near_zero_handling": "one shared nonzero physical scale avoids division by response values near zero crossings",
            "formal_acceptance_thresholds": "none; all reference differences and refinement trends are descriptive",
        },
        "time_study": {
            "mesh_nx": 8,
            "time_steps_s": list(TIME_STEPS_S),
            "observation_end_s": OBSERVATION_END_S,
            "comparison_times": "identical physical grid points for each time step; all pulse knots divide each time grid exactly",
            "results": temporal_results,
            "observed_orders_vs_qf_semidiscrete_oracle": temporal_orders,
            "oracle_scope": "full-order propagation of the same QF-assembled M/K; used only for time-integration separation, not as the independent mechanical reference",
        },
        "mesh_study": {
            "time_step_s": TIME_STEPS_S[-1],
            "mesh_levels": mesh_results,
            "spatial_indicator": "QF semi-discrete oracle against the independent continuum series; direct Newmark-to-continuum is also reported and includes its residual time error",
            "transverse_resolution": "one cell across each transverse direction; exact continuum field is constant over the cross-section under the contracted transverse guidance",
        },
        "animation": {
            "status": "GENERATED_FROM_DURABLE_QF_CHECKPOINTS",
            "mesh_nx": MESH_LEVELS[-1],
            "checkpoint_stride_steps": CHECKPOINT_STRIDE,
            "frame_count_including_initial_zero_state": int(len(animation_times)),
            "time_step_s": TIME_STEPS_S[-1],
            "time_range_s": [float(animation_times[0]), float(animation_times[-1])],
            "displacement_amplification": AMPLIFICATION,
            "deformation_source": "actual full nodal Newmark displacements read from atomic NPZ checkpoints; only centerline nodes are plotted",
            "animation_gif": animation_path.name,
        },
        "checks": {
            "all_meshes_positive_corner_volumes": True,
            "uniform_end_load_resultant_and_first_moments": "1 N at the physical face center on every mesh",
            "all_newmark_statuses": "PASS",
            "all_dynamic_residuals_finite": True,
            "formal_pass_thresholds": "none for continuum correlation or spatial convergence",
        },
        "artifacts": {
            state_path.name: state_sha,
            history_path.name: history_sha,
            mesh_figure.name: _sha256_file(mesh_figure),
            history_figure.name: _sha256_file(history_figure),
            time_figure.name: _sha256_file(time_figure),
            animation_path.name: _sha256_file(animation_path),
        },
        "environment": _environment(),
    }
    _atomic_json(output_dir / "result.json", result_payload)
    _atomic_bytes(output_dir / "result.sha256", (_sha256_file(output_dir / "result.json") + "\n").encode("ascii"))
    return result_payload


def _force_factor(time_s: float) -> float:
    if time_s <= FORCE_SEGMENTS[0][1]:
        return time_s / FORCE_SEGMENTS[0][1]
    if time_s < FORCE_SEGMENTS[1][1]:
        return 1.0 - (time_s - FORCE_SEGMENTS[0][1]) / (FORCE_SEGMENTS[1][1] - FORCE_SEGMENTS[0][1])
    return 0.0
