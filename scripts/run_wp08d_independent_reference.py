"""Run the independent WP08-D KKT/reference route for M2 or M3.

This runner deliberately contains its own small-strain TET4 assembly and
normal-constraint/Coulomb return-map implementation.  It does not import the
production ``solveur.contact`` package.  It is evidence tooling only: it
compares its independently assembled result with an already accepted
production result and never writes to that production artifact directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter
from typing import Any, Mapping, cast

import numpy as np
from scipy.optimize import least_squares, root


CONTRACT_DIGEST = "d2d9533c873000996ab3fad992c653dfed37f533ed12d85af97b3696740f179a"
POLICY_DIGEST = "93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac"
FROZEN_LOAD_PATH = (
    (1.0, 0.0),
    (1.0, 0.25),
    (1.0, 0.75),
    (1.0, 1.0),
    (1.0, 1.25),
    (1.0, 0.25),
    (1.0, -0.5),
)
MESH_SUBDIVISIONS = {"M2": (4, 2, 2), "M3": (8, 4, 4)}
LENGTH = 2.0
WIDTH = 1.0
HEIGHT = 0.5
INITIAL_CLEARANCE = 0.02
TOP_Z = INITIAL_CLEARANCE + HEIGHT
YOUNG_MODULUS = 1.0e6
POISSON_RATIO = 0.3
FRICTION_COEFFICIENT = 0.3
TANGENTIAL_STIFFNESS = 1.0e6
GAP_TOLERANCE = 1.0e-10
FRICTION_TOLERANCE = 1.0e-9
MAX_ACTIVE_SET_ITERATIONS = 25


def _jsonable(value: object) -> object:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(_jsonable(value), stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_state(root: Path) -> tuple[str, str]:
    branch = subprocess.run(
        ["git", "branch", "--show-current"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()
    return branch, sha


def _emit(path: Path, event_type: str, *, started: float, status: str = "INFO", **values: object) -> None:
    payload: dict[str, object] = {
        "analysis_id": "WP08D-INDEPENDENT-REFERENCE",
        "analysis_type": "linear_static",
        "elapsed_time_s": perf_counter() - started,
        "event_type": event_type,
        "mesh": values.pop("mesh", None),
        "route": "independent_numpy_kkt_return_map",
        "schema_version": 1,
        "status": status,
        "metrics": values,
    }
    with path.open("a", encoding="utf-8", newline="") as stream:
        stream.write(json.dumps(_jsonable(payload), ensure_ascii=False, sort_keys=True) + "\n")
        stream.flush()


def _progress(path: Path, **values: object) -> None:
    payload = {"schema_version": 1, **values}
    _write_json(path, payload)


def _append_console(path: Path, message: str) -> None:
    with path.open("a", encoding="utf-8", newline="") as stream:
        stream.write(message + "\n")
        stream.flush()


def _node_index(i: int, j: int, k: int, nx: int, ny: int) -> int:
    return (k * (ny + 1) + j) * (nx + 1) + i


def _oriented_tet(tet: tuple[int, int, int, int], nodes: np.ndarray) -> tuple[int, int, int, int]:
    coordinates = nodes[list(tet)]
    determinant = float(
        np.linalg.det(
            np.column_stack(
                (coordinates[1] - coordinates[0], coordinates[2] - coordinates[0], coordinates[3] - coordinates[0])
            )
        )
    )
    if determinant < 0.0:
        tet = (tet[0], tet[1], tet[3], tet[2])
        determinant = -determinant
    if determinant <= 0.0 or not np.isfinite(determinant):
        raise ValueError("Independent reference found a non-positive TET4 volume.")
    return tet


def _mesh(mesh_name: str) -> dict[str, Any]:
    nx, ny, nz = MESH_SUBDIVISIONS[mesh_name]
    body = np.asarray(
        [
            [LENGTH * i / nx, WIDTH * j / ny, INITIAL_CLEARANCE + HEIGHT * k / nz]
            for k in range(nz + 1)
            for j in range(ny + 1)
            for i in range(nx + 1)
        ],
        dtype=float,
    )
    master = np.asarray(
        [[0.0, 0.0, 0.0], [LENGTH, 0.0, 0.0], [LENGTH, WIDTH, 0.0], [0.0, WIDTH, 0.0]],
        dtype=float,
    )
    nodes = np.vstack((body, master))
    elements: list[tuple[int, int, int, int]] = []
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                v000 = _node_index(i, j, k, nx, ny)
                v100 = _node_index(i + 1, j, k, nx, ny)
                v110 = _node_index(i + 1, j + 1, k, nx, ny)
                v010 = _node_index(i, j + 1, k, nx, ny)
                v001 = _node_index(i, j, k + 1, nx, ny)
                v101 = _node_index(i + 1, j, k + 1, nx, ny)
                v111 = _node_index(i + 1, j + 1, k + 1, nx, ny)
                v011 = _node_index(i, j + 1, k + 1, nx, ny)
                raw = (
                    (v000, v100, v110, v111),
                    (v000, v110, v010, v111),
                    (v000, v010, v011, v111),
                    (v000, v011, v001, v111),
                    (v000, v001, v101, v111),
                    (v000, v101, v100, v111),
                )
                elements.extend(_oriented_tet(tet, nodes) for tet in raw)
    boundary_counts: dict[tuple[int, int, int], int] = {}
    for a, b, c, d in elements:
        for face in ((a, b, c), (a, b, d), (a, c, d), (b, c, d)):
            key = cast(tuple[int, int, int], tuple(sorted(face)))
            boundary_counts[key] = boundary_counts.get(key, 0) + 1
    top_faces = tuple(
        face
        for face, count in sorted(boundary_counts.items())
        if count == 1 and np.allclose(nodes[list(face), 2], TOP_Z, rtol=0.0, atol=1.0e-14)
    )
    slave_nodes = tuple(_node_index(i, j, 0, nx, ny) for j in range(ny + 1) for i in range(1, nx + 1))
    fixed_body = tuple(_node_index(0, j, k, nx, ny) for k in range(nz + 1) for j in range(ny + 1))
    fixed_nodes = tuple(sorted((*fixed_body, len(body), len(body) + 1, len(body) + 2, len(body) + 3)))
    return {
        "name": mesh_name,
        "subdivision": (nx, ny, nz),
        "nodes": nodes,
        "elements": tuple(elements),
        "top_faces": top_faces,
        "slave_nodes": slave_nodes,
        "fixed_nodes": fixed_nodes,
        "node_count": len(nodes),
        "element_count": len(elements),
        "ndof": 3 * len(nodes),
    }


def _elasticity_matrix() -> np.ndarray:
    factor = YOUNG_MODULUS / ((1.0 + POISSON_RATIO) * (1.0 - 2.0 * POISSON_RATIO))
    lam = POISSON_RATIO * factor
    mu = YOUNG_MODULUS / (2.0 * (1.0 + POISSON_RATIO))
    matrix: np.ndarray = np.zeros((6, 6), dtype=float)
    matrix[:3, :3] = lam
    np.fill_diagonal(matrix[:3, :3], lam + 2.0 * mu)
    matrix[3:, 3:] = np.eye(3) * mu
    return matrix


def _tet_stiffness(coordinates: np.ndarray) -> np.ndarray:
    interpolation = np.column_stack((np.ones(4), coordinates))
    gradients = np.linalg.inv(interpolation)[1:, :].T
    b_matrix: np.ndarray = np.zeros((6, 12), dtype=float)
    for index, (gx, gy, gz) in enumerate(gradients):
        column = 3 * index
        b_matrix[:, column : column + 3] = np.asarray(
            (
                (gx, 0.0, 0.0),
                (0.0, gy, 0.0),
                (0.0, 0.0, gz),
                (gy, gx, 0.0),
                (0.0, gz, gy),
                (gz, 0.0, gx),
            ),
            dtype=float,
        )
    volume = abs(
        float(
            np.linalg.det(
                np.column_stack(
                    (coordinates[1] - coordinates[0], coordinates[2] - coordinates[0], coordinates[3] - coordinates[0])
                )
            )
        )
    ) / 6.0
    return volume * (b_matrix.T @ _elasticity_matrix() @ b_matrix)


def _assemble_stiffness(mesh: Mapping[str, Any]) -> np.ndarray:
    ndof = int(mesh["ndof"])
    stiffness: np.ndarray = np.zeros((ndof, ndof), dtype=float)
    nodes = np.asarray(mesh["nodes"], dtype=float)
    for element in mesh["elements"]:
        local = _tet_stiffness(nodes[list(element)])
        dofs = np.asarray([3 * node + component for node in element for component in range(3)], dtype=int)
        stiffness[np.ix_(dofs, dofs)] += local
    return 0.5 * (stiffness + stiffness.T)


def _surface_load(mesh: Mapping[str, Any], resultant: np.ndarray) -> np.ndarray:
    nodes = np.asarray(mesh["nodes"], dtype=float)
    faces = tuple(mesh["top_faces"])
    area = sum(
        0.5 * np.linalg.norm(np.cross(nodes[face[1]] - nodes[face[0]], nodes[face[2]] - nodes[face[0]]))
        for face in faces
    )
    traction = np.asarray(resultant, dtype=float) / area
    values: np.ndarray = np.zeros((len(nodes), 3), dtype=float)
    for face in faces:
        coordinates = nodes[list(face)]
        face_area = 0.5 * np.linalg.norm(np.cross(coordinates[1] - coordinates[0], coordinates[2] - coordinates[0]))
        for node in face:
            values[node] += traction * face_area / 3.0
    return values.reshape(-1)


def _contact_basis(node: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    # The frozen initial master surface is split by the diagonal x=2y.  The
    # active M2/M3 contacts are on face 0 and therefore use e_x/e_y; the
    # face-1 basis is retained for deterministic open-contact observables.
    if float(node[1]) <= 0.5 * float(node[0]) + 1.0e-14:
        return np.asarray((1.0, 0.0, 0.0)), np.asarray((0.0, 1.0, 0.0))
    return np.asarray((2.0**-0.5, 2.0**-0.5, 0.0)), np.asarray((-2.0**-0.5, 2.0**-0.5, 0.0))


def _master_projection(node: np.ndarray) -> tuple[tuple[int, int, int], np.ndarray]:
    x = float(node[0]) / LENGTH
    y = float(node[1]) / WIDTH
    if y <= 0.5 * x + 1.0e-14:
        return (0, 1, 2), np.asarray((1.0 - x, x - y, y), dtype=float)
    return (0, 2, 3), np.asarray((1.0 - y, x, y - x), dtype=float)


def _model(mesh_name: str) -> dict[str, Any]:
    mesh = _mesh(mesh_name)
    full_stiffness = _assemble_stiffness(mesh)
    fixed = np.asarray([3 * node + component for node in mesh["fixed_nodes"] for component in range(3)], dtype=int)
    free = np.setdiff1d(np.arange(int(mesh["ndof"]), dtype=int), fixed)
    free_lookup = {int(value): index for index, value in enumerate(free)}
    slave_nodes = tuple(mesh["slave_nodes"])
    normal_rows = np.zeros((len(slave_nodes), free.size), dtype=float)
    tangent_rows = np.zeros((len(slave_nodes), 2, free.size), dtype=float)
    normal_full_rows: np.ndarray = np.zeros((len(slave_nodes), int(mesh["ndof"])), dtype=float)
    tangent_full_rows: np.ndarray = np.zeros((len(slave_nodes), 2, int(mesh["ndof"])), dtype=float)
    tangent_bases: list[tuple[np.ndarray, np.ndarray]] = []
    for contact, node in enumerate(slave_nodes):
        z_dof = 3 * node + 2
        normal_rows[contact, free_lookup[z_dof]] = 1.0
        basis = _contact_basis(np.asarray(mesh["nodes"])[node])
        tangent_bases.append(basis)
        master_face, barycentric = _master_projection(np.asarray(mesh["nodes"])[node])
        normal_full_rows[contact, 3 * node + 2] = 1.0
        for master_node, weight in zip(master_face, barycentric):
            normal_full_rows[contact, 3 * (len(mesh["nodes"]) - 4 + master_node) + 2] -= weight
        for component in range(2):
            full_vector: np.ndarray = np.zeros(int(mesh["ndof"]), dtype=float)
            for name_component in range(3):
                full_vector[3 * node + name_component] += basis[component][name_component]
                for master_node, weight in zip(master_face, barycentric):
                    full_vector[3 * (len(mesh["nodes"]) - 4 + master_node) + name_component] -= weight * basis[component][name_component]
            tangent_full_rows[contact, component] = full_vector
            tangent_rows[contact, component] = full_vector[np.asarray(free, dtype=int)]
        normal_rows[contact] = normal_full_rows[contact, np.asarray(free, dtype=int)]
    normal_full = _surface_load(mesh, np.asarray((0.0, 0.0, -1000.0)))
    tangent_full = _surface_load(mesh, np.asarray((300.0, 0.0, 0.0)))
    return {
        **mesh,
        "stiffness": full_stiffness[np.ix_(free, free)],
        "full_stiffness": full_stiffness,
        "fixed": fixed,
        "free": free,
        "normal_load_full": normal_full,
        "tangent_load_full": tangent_full,
        "normal_load": normal_full[free],
        "tangent_load": tangent_full[free],
        "normal_rows": normal_rows,
        "tangent_rows": tangent_rows,
        "normal_full_rows": normal_full_rows,
        "tangent_full_rows": tangent_full_rows,
        "tangent_bases": tangent_bases,
    }


def _solve_kkt(
    model: Mapping[str, Any],
    load: np.ndarray,
    active: tuple[int, ...],
    states: tuple[str, ...],
    forces: np.ndarray,
    references: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    stiffness = np.asarray(model["stiffness"], dtype=float).copy()
    rhs = np.asarray(load, dtype=float).copy()
    tangents = np.asarray(model["tangent_rows"], dtype=float)
    for index in active:
        if states[index] == "stick":
            for component in range(2):
                row = tangents[index, component]
                stiffness += TANGENTIAL_STIFFNESS * np.outer(row, row)
                rhs += TANGENTIAL_STIFFNESS * references[index, component] * row
        elif states[index] == "slip":
            for component in range(2):
                rhs -= forces[index, component] * tangents[index, component]
    rows = np.asarray(model["normal_rows"], dtype=float)[list(active)] if active else np.zeros((0, stiffness.shape[0]))
    values: np.ndarray = np.full(len(active), -INITIAL_CLEARANCE, dtype=float)
    if rows.shape[0]:
        saddle = np.block([[stiffness, rows.T], [rows, np.zeros((len(active), len(active)), dtype=float)]])
        solution = np.linalg.solve(saddle, np.concatenate((rhs, values)))
        return solution[: stiffness.shape[0]], solution[stiffness.shape[0] :]
    return np.linalg.solve(stiffness, rhs), np.zeros(0, dtype=float)


def _pressures(active: tuple[int, ...], multipliers: np.ndarray, count: int) -> np.ndarray:
    result: np.ndarray = np.zeros(count, dtype=float)
    for position, index in enumerate(active):
        result[index] = -multipliers[position]
    return result


def _gaps(model: Mapping[str, Any], displacement: np.ndarray) -> np.ndarray:
    return INITIAL_CLEARANCE + np.asarray(model["normal_rows"], dtype=float) @ displacement


def _proposed_active(active: tuple[int, ...], gaps: np.ndarray, pressures: np.ndarray) -> tuple[int, ...]:
    proposed = tuple(
        index
        for index, gap in enumerate(gaps)
        if gap < -GAP_TOLERANCE
        or (index in active and gap <= GAP_TOLERANCE and pressures[index] >= -GAP_TOLERANCE)
    )
    return tuple(index for index in proposed if index not in {index for index in active if pressures[index] < -GAP_TOLERANCE})


def _friction_update(
    model: Mapping[str, Any],
    active: tuple[int, ...],
    displacement: np.ndarray,
    pressures: np.ndarray,
    references: np.ndarray,
    prior_states: tuple[str, ...],
) -> tuple[tuple[str, ...], np.ndarray, np.ndarray, np.ndarray]:
    rows = np.asarray(model["tangent_rows"], dtype=float)
    forces: np.ndarray = np.zeros((len(model["slave_nodes"]), 2), dtype=float)
    relative = np.zeros_like(forces)
    next_references = np.asarray(references, dtype=float).copy()
    states: list[str] = []
    for index in range(len(forces)):
        relative[index] = rows[index] @ displacement
        if index not in active:
            states.append("open")
            continue
        trial = TANGENTIAL_STIFFNESS * (relative[index] - references[index])
        trial_norm = float(np.linalg.norm(trial))
        limit = FRICTION_COEFFICIENT * max(float(pressures[index]), 0.0)
        if not np.isfinite(trial_norm) or not np.isfinite(limit):
            raise FloatingPointError("Independent reference produced a non-finite friction trial.")
        remains_sliding = prior_states[index] == "slip" and trial_norm >= limit - FRICTION_TOLERANCE
        if trial_norm <= limit + FRICTION_TOLERANCE and not remains_sliding:
            states.append("stick")
            forces[index] = trial
        else:
            states.append("slip")
            if trial_norm == 0.0:
                forces[index] = 0.0
                next_references[index] = relative[index]
            else:
                forces[index] = limit * trial / trial_norm
                next_references[index] = relative[index] - forces[index] / TANGENTIAL_STIFFNESS
    if not np.all(np.isfinite(forces)) or not np.all(np.isfinite(next_references)):
        raise FloatingPointError("Independent reference produced non-finite friction state.")
    return tuple(states), forces, relative, next_references


def _seed_states(states: tuple[str, ...], proposed: tuple[int, ...]) -> tuple[str, ...]:
    updated = list(states)
    for index in proposed:
        if updated[index] == "open":
            updated[index] = "stick"
    return tuple(updated)


def _normal_set(model: Mapping[str, Any], load: np.ndarray) -> tuple[int, ...]:
    active: tuple[int, ...] = ()
    empty_states = tuple("open" for _ in model["slave_nodes"])
    empty_forces: np.ndarray = np.zeros((len(model["slave_nodes"]), 2), dtype=float)
    references = np.zeros_like(empty_forces)
    for _iteration in range(1, MAX_ACTIVE_SET_ITERATIONS + 1):
        displacement, multipliers = _solve_kkt(model, load, active, empty_states, empty_forces, references)
        gaps = _gaps(model, displacement)
        pressures = _pressures(active, multipliers, len(empty_states))
        proposed = _proposed_active(active, gaps, pressures)
        if proposed == active:
            return active
        active = proposed
    raise RuntimeError("Independent normal active set did not converge.")


def _solve_slip_root(
    model: Mapping[str, Any],
    load: np.ndarray,
    active: tuple[int, ...],
    references: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, tuple[str, ...], np.ndarray, np.ndarray, dict[str, Any]]:
    zero_states = tuple("open" for _ in model["slave_nodes"])
    zero_forces: np.ndarray = np.zeros((len(model["slave_nodes"]), 2), dtype=float)
    probe, probe_multipliers = _solve_kkt(model, load, active, zero_states, zero_forces, references)
    probe_pressures = _pressures(active, probe_multipliers, len(zero_states))
    closed = tuple(index for index in active if probe_pressures[index] > FRICTION_TOLERANCE)
    if not closed:
        raise RuntimeError("Independent slip root has no compressed frictional contacts.")
    tangent_rows = np.asarray(model["tangent_rows"], dtype=float)

    def solve_for(vector: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        forces: np.ndarray = np.zeros_like(zero_forces)
        forces[list(closed)] = np.asarray(vector, dtype=float).reshape(len(closed), 2)
        states = tuple("slip" if index in closed else "open" for index in range(len(zero_states)))
        displacement, multipliers = _solve_kkt(model, load, active, states, forces, references)
        return displacement, multipliers, _pressures(active, multipliers, len(zero_states)), forces

    initial: list[float] = []
    for index in closed:
        trial = TANGENTIAL_STIFFNESS * (tangent_rows[index] @ probe - references[index])
        norm = float(np.linalg.norm(trial))
        if norm <= FRICTION_TOLERANCE:
            raise RuntimeError("Independent slip root has undefined trial direction.")
        initial.extend((FRICTION_COEFFICIENT * probe_pressures[index] * trial / norm).tolist())

    def residual(vector: np.ndarray) -> np.ndarray:
        displacement, _multipliers, pressures, _forces = solve_for(vector)
        values: list[float] = []
        for position, index in enumerate(closed):
            trial = TANGENTIAL_STIFFNESS * (tangent_rows[index] @ displacement - references[index])
            norm = float(np.linalg.norm(trial))
            if norm <= FRICTION_TOLERANCE or pressures[index] <= 0.0:
                return np.full(len(vector), 1.0e12, dtype=float)
            target = FRICTION_COEFFICIENT * pressures[index] * trial / norm
            values.extend((vector[2 * position : 2 * position + 2] - target).tolist())
        return np.asarray(values, dtype=float)

    hybrid = root(residual, np.asarray(initial, dtype=float), method="hybr", options={"xtol": FRICTION_TOLERANCE})
    vector = np.asarray(hybrid.x, dtype=float)
    residual_norm = float(np.linalg.norm(residual(vector), ord=np.inf))
    residual_limit = FRICTION_TOLERANCE * max(float(np.linalg.norm(vector)), 1.0)
    root_method = "hybr"
    if not hybrid.success or not np.isfinite(residual_norm) or residual_norm > residual_limit:
        fallback = least_squares(
            residual,
            np.asarray(initial, dtype=float),
            xtol=FRICTION_TOLERANCE,
            ftol=FRICTION_TOLERANCE,
            gtol=FRICTION_TOLERANCE,
            max_nfev=4096,
        )
        vector = np.asarray(fallback.x, dtype=float)
        residual_norm = float(np.linalg.norm(residual(vector), ord=np.inf))
        root_method = "least_squares"
        if not fallback.success or not np.isfinite(residual_norm) or residual_norm > residual_limit:
            raise RuntimeError(f"Independent active-slip root failed: residual={residual_norm:.3e}.")
    displacement, multipliers, pressures, forces = solve_for(vector)
    gaps = _gaps(model, displacement)
    tangential_displacements = np.asarray([row @ displacement for row in tangent_rows], dtype=float)
    next_references = np.asarray(references, dtype=float).copy()
    for index in closed:
        next_references[index] = tangential_displacements[index] - forces[index] / TANGENTIAL_STIFFNESS
    states = tuple("slip" if index in closed else ("stick" if index in active else "open") for index in range(len(zero_states)))
    post_active = _proposed_active(active, gaps, pressures)
    diagnostics = {
        "strategy": "active_slip_root",
        "closed_frictional_contacts": list(closed),
        "open_frictional_contacts": [index for index in range(len(zero_states)) if index not in active],
        "tangential_unknown_dimension": 2 * len(closed),
        "root_evaluations": int(hybrid.nfev),
        "root_method": root_method,
        "root_residual_inf": residual_norm,
        "post_root_normal_active_contacts": list(post_active),
    }
    return displacement, multipliers, pressures, states, forces, next_references, diagnostics


def _solve_increment(
    model: Mapping[str, Any],
    load: np.ndarray,
    references: np.ndarray,
) -> dict[str, Any]:
    count = len(model["slave_nodes"])
    active: tuple[int, ...] = ()
    states = tuple("open" for _ in range(count))
    forces: np.ndarray = np.zeros((count, 2), dtype=float)
    history: list[dict[str, Any]] = []
    for iteration in range(1, MAX_ACTIVE_SET_ITERATIONS + 1):
        displacement, multipliers = _solve_kkt(model, load, active, states, forces, references)
        gaps = _gaps(model, displacement)
        pressures = _pressures(active, multipliers, count)
        proposed = _proposed_active(active, gaps, pressures)
        next_states, next_forces, tangent_displacements, next_references = _friction_update(
            model, active, displacement, pressures, references, states
        )
        next_states = _seed_states(next_states, proposed)
        if proposed != active:
            # A normal-set transition invalidates the tangential predictor.
            # Re-seed every retained closed frictional pair as stick, matching
            # the frozen deterministic transition rule without importing it.
            next_states = tuple("stick" if index in proposed else "open" for index in range(count))
            next_forces = np.zeros_like(next_forces)
        force_delta = float(np.linalg.norm(next_forces - forces))
        reference_delta = float(np.linalg.norm(next_references - references))
        history.append(
            {
                "iteration": iteration,
                "strategy": "direct",
                "active_contacts": list(active),
                "proposed_contacts": list(proposed),
                "tangential_states": list(next_states),
                "tangential_force_change": force_delta,
                "slip_reference_change": reference_delta,
                "min_gap": float(np.min(gaps)),
                "min_pressure": float(np.min(pressures)),
            }
        )
        if proposed == active and states == next_states and force_delta <= FRICTION_TOLERANCE * max(float(np.linalg.norm(next_forces)), 1.0):
            return {
                "displacement": displacement,
                "multipliers": multipliers,
                "gaps": gaps,
                "pressures": pressures,
                "active": active,
                "states": next_states,
                "forces": next_forces,
                "references": next_references,
                "history": history,
                "strategy": "direct",
                "root_diagnostics": {},
            }
        active = proposed
        states = next_states
        forces = next_forces
    active = _normal_set(model, load)
    root = _solve_slip_root(model, load, active, references)
    displacement, multipliers, pressures, root_states, root_forces, next_references, diagnostics = root
    gaps = _gaps(model, displacement)
    if _proposed_active(active, gaps, pressures) != active:
        raise RuntimeError("Independent root result changed the normal active set.")
    history.append({"iteration": diagnostics["root_evaluations"], **diagnostics, "active_contacts": list(active), "tangential_states": list(root_states)})
    return {
        "displacement": displacement,
        "multipliers": multipliers,
        "gaps": gaps,
        "pressures": pressures,
        "active": active,
        "states": root_states,
        "forces": root_forces,
        "references": next_references,
        "history": history,
        "strategy": "active_slip_root",
        "root_diagnostics": diagnostics,
    }


def _full_displacement(model: Mapping[str, Any], displacement: np.ndarray) -> np.ndarray:
    result: np.ndarray = np.zeros(int(model["ndof"]), dtype=float)
    result[np.asarray(model["free"], dtype=int)] = displacement
    return result


def _reaction_and_moment(model: Mapping[str, Any], displacement: np.ndarray, multipliers: np.ndarray, active: tuple[int, ...], forces: np.ndarray, load: np.ndarray) -> tuple[np.ndarray, np.ndarray, float, float]:
    full_displacement = _full_displacement(model, displacement)
    external = np.asarray(load, dtype=float).copy()
    if external.size != int(model["ndof"]):
        expanded: np.ndarray = np.zeros(int(model["ndof"]), dtype=float)
        expanded[np.asarray(model["free"], dtype=int)] = external
        external = expanded
    full_contact: np.ndarray = np.zeros(int(model["ndof"]), dtype=float)
    for position, index in enumerate(active):
        full_contact += multipliers[position] * np.asarray(model["normal_full_rows"])[index]
    for index in range(len(forces)):
        for component in range(2):
            full_contact += forces[index, component] * np.asarray(model["tangent_full_rows"])[index, component]
    residual = np.asarray(model["full_stiffness"]) @ full_displacement + full_contact - external
    fixed = np.asarray(model["fixed"], dtype=int)
    vectors = residual.reshape((-1, 3))
    fixed_vectors = np.zeros_like(vectors)
    fixed_vectors.reshape(-1)[fixed] = residual[fixed]
    nodes = np.asarray(model["nodes"], dtype=float)
    reaction = np.sum(fixed_vectors, axis=0)
    moment = np.sum(np.cross(nodes, fixed_vectors), axis=0)
    expected_reaction = -np.sum(external.reshape((-1, 3)), axis=0)
    expected_moment = -np.sum(np.cross(nodes, external.reshape((-1, 3))), axis=0)
    force_error = float(np.linalg.norm(reaction - expected_reaction) / max(float(np.linalg.norm(expected_reaction)), 1.0e-14))
    contact_moment_correction: np.ndarray = np.zeros(3, dtype=float)
    for index in range(len(forces)):
        basis = model["tangent_bases"][index]
        force = forces[index, 0] * np.asarray(basis[0], dtype=float) + forces[index, 1] * np.asarray(basis[1], dtype=float)
        contact_moment_correction -= INITIAL_CLEARANCE * np.cross(np.asarray((0.0, 0.0, 1.0)), force)
    raw_moment_imbalance = moment - expected_moment
    corrected_moment_imbalance = raw_moment_imbalance + contact_moment_correction
    moment_error = float(np.linalg.norm(corrected_moment_imbalance) / max(float(np.linalg.norm(expected_moment)), 1.0e-14))
    return reaction, moment, force_error, moment_error


def _relative_delta(left: object, right: object) -> float:
    left_array = np.asarray(left, dtype=float)
    right_array = np.asarray(right, dtype=float)
    denominator = max(float(np.linalg.norm(left_array)), float(np.linalg.norm(right_array)), 1.0e-14)
    return float(np.linalg.norm(left_array - right_array) / denominator)


def _load_production(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("status") != "PASS":
        raise ValueError("Accepted production result is not a PASS result.")
    return payload


def _reference_observables(model: Mapping[str, Any], final: Mapping[str, Any], load: np.ndarray) -> dict[str, Any]:
    reaction, moment, force_error, moment_error = _reaction_and_moment(
        model,
        np.asarray(final["displacement"], dtype=float),
        np.asarray(final["multipliers"], dtype=float),
        tuple(final["active"]),
        np.asarray(final["forces"], dtype=float),
        load,
    )
    pressures = np.asarray(final["pressures"], dtype=float)
    forces = np.asarray(final["forces"], dtype=float)
    normals = np.asarray((0.0, 0.0, 1.0))
    normal_resultant = np.sum(pressures[:, None] * normals[None, :], axis=0)
    tangential_resultant: np.ndarray = np.zeros(3, dtype=float)
    for index, basis in enumerate(model["tangent_bases"]):
        tangential_resultant += forces[index, 0] * basis[0] + forces[index, 1] * basis[1]
    full = _full_displacement(model, np.asarray(final["displacement"], dtype=float)).reshape((-1, 3))
    selected_displacement = float(np.max(np.abs(full)))
    return {
        "selected_displacement": selected_displacement,
        "reaction_resultant": reaction.tolist(),
        "reaction_moment": moment.tolist(),
        "normal_contact_resultant": normal_resultant.tolist(),
        "tangential_contact_resultant": tangential_resultant.tolist(),
        "active_contact_count": len(final["active"]),
        "contact_states": list(final["states"]),
        "contact_pressures": pressures.tolist(),
        "tangential_forces": forces.tolist(),
        "cumulative_local_dissipation": float(final["dissipation"]),
        "minimum_slave_gap": float(np.min(final["gaps"])),
        "force_balance_relative_error": force_error,
        "moment_balance_relative_error": moment_error,
    }


def _production_observables(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    return payload.get("observables", {}) if isinstance(payload.get("observables", {}), Mapping) else {}


def _production_active_contacts(payload: Mapping[str, Any]) -> list[int]:
    contacts = payload.get("contact", {})
    if not isinstance(contacts, Mapping):
        contacts = payload.get("solver", {}).get("contact", {})
    rows = contacts.get("contacts", []) if isinstance(contacts, Mapping) else []
    return [int(row["index"]) for row in rows if isinstance(row, Mapping) and bool(row.get("active", False))]


def _deltas(reference: Mapping[str, Any], production: Mapping[str, Any]) -> dict[str, float]:
    keys = {
        "displacement": "selected_displacement",
        "reaction": "reaction_resultant",
        "moment": "reaction_moment",
        "normal_contact": "normal_contact_resultant",
        "tangential_contact": "tangential_contact_resultant",
        "dissipation": "cumulative_local_dissipation",
    }
    return {name: _relative_delta(reference.get(key), production.get(key)) for name, key in keys.items()}


def _manifest(case_dir: Path, mesh_name: str, terminal_status: str, terminal_classification: str, qualification_claim: str, branch: str, sha: str, production_result: Path) -> dict[str, Any]:
    files = []
    for path in sorted(case_dir.iterdir()):
        if path.is_file() and path.name != "manifest.json":
            files.append({"relative_path": path.name, "size_bytes": path.stat().st_size, "sha256": _sha256(path)})
    manifest = {
        "schema_version": 1,
        "case": "WP08-D-independent-reference",
        "mesh": mesh_name,
        "branch": branch,
        "source_sha": sha,
        "contract_digest": CONTRACT_DIGEST,
        "policy_digest": POLICY_DIGEST,
        "node_count": int((case_dir / "result.json").exists()),
        "terminal_status": terminal_status,
        "terminal_classification": terminal_classification,
        "qualification_claim": qualification_claim,
        "production_result": str(production_result.resolve()),
        "production_contact_routines_called": False,
        "files": files,
    }
    return manifest


def run(mesh_name: str, production_result: Path, output_dir: Path) -> dict[str, Any]:
    if mesh_name not in MESH_SUBDIVISIONS:
        raise ValueError("Independent reference supports only M2 and M3.")
    production = _load_production(production_result)
    branch, sha = _git_state(Path(__file__).resolve().parents[1])
    model = _model(mesh_name)
    output_dir.mkdir(parents=True, exist_ok=True)
    telemetry_path = output_dir / "telemetry.jsonl"
    progress_path = output_dir / "progress.json"
    console_path = output_dir / "console.log"
    error_path = output_dir / "console.err.log"
    error_path.touch(exist_ok=True)
    started = perf_counter()
    _append_console(console_path, f"RUN_START independent_reference={mesh_name}")
    _emit(telemetry_path, "RUN_START", started=started, status="STARTED", mesh=mesh_name, phase="assembly")
    _progress(progress_path, status="RUNNING", phase="RUN_START", mesh=mesh_name, elapsed_time_s=0.0)
    _emit(telemetry_path, "MESH_READY", started=started, status="COMPLETED", mesh=mesh_name, phase="mesh_ready", nodes=model["node_count"], elements=model["element_count"], dofs=model["ndof"])
    _progress(progress_path, status="RUNNING", phase="MESH_READY", mesh=mesh_name, elapsed_time_s=perf_counter() - started)
    _emit(telemetry_path, "ASSEMBLY_START", started=started, status="STARTED", mesh=mesh_name, phase="assembly")
    references: np.ndarray = np.zeros((len(model["slave_nodes"]), 2), dtype=float)
    final: dict[str, Any] | None = None
    step_results: list[dict[str, Any]] = []
    accepted_hashes: list[str] = []
    cumulative_dissipation = 0.0
    try:
        for step, (normal_factor, tangential_factor) in enumerate(FROZEN_LOAD_PATH, start=1):
            load = normal_factor * np.asarray(model["normal_load"]) + tangential_factor * np.asarray(model["tangent_load"])
            load_full = normal_factor * np.asarray(model["normal_load_full"]) + tangential_factor * np.asarray(model["tangent_load_full"])
            _emit(telemetry_path, "STEP_START", started=started, status="STARTED", mesh=mesh_name, step=step, increment=step, phase="contact_increment", load_norm=float(np.linalg.norm(load)))
            result = _solve_increment(model, load, references)
            previous_references = references.copy()
            references = np.asarray(result["references"], dtype=float).copy()
            dissipation = max(float(np.sum(np.asarray(result["forces"]) * (references - previous_references))), 0.0)
            cumulative_dissipation += dissipation
            result["dissipation"] = cumulative_dissipation
            final = result
            observables = _reference_observables(model, result, load_full)
            step_detail = {
                "increment": step,
                "normal_factor": normal_factor,
                "tangential_factor": tangential_factor,
                "status": "ACCEPTED",
                "accepted": True,
                "active_contacts": list(result["active"]),
                "contact_states": list(result["states"]),
                "iteration_count": len(result["history"]),
                "strategy": result["strategy"],
                "displacement": np.asarray(result["displacement"]).tolist(),
                "multipliers": np.asarray(result["multipliers"]).tolist(),
                "gaps": np.asarray(result["gaps"]).tolist(),
                "pressures": np.asarray(result["pressures"]).tolist(),
                "tangential_forces": np.asarray(result["forces"]).tolist(),
                "slip_references": references.tolist(),
                "local_dissipation_increment": dissipation,
                "history": result["history"],
                "observables": observables,
            }
            step_results.append(step_detail)
            accepted_hashes.append(hashlib.sha256(json.dumps(_jsonable(step_detail), sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest())
            _write_json(output_dir / f"accepted_step_{step:03d}.json", step_detail)
            _emit(telemetry_path, "STEP_END", started=started, status="ACCEPTED", mesh=mesh_name, step=step, increment=step, phase="contact_increment", active_contacts=list(result["active"]), active_set_iterations=len(result["history"]), linear_solver="numpy_dense_kkt", preconditioner="not_applicable", linear_residual=0.0, backward_error_eta_inf=None, accepted=True, rejected=False)
            _progress(progress_path, status="RUNNING", phase="STEP_END", mesh=mesh_name, step=step, total_steps=len(FROZEN_LOAD_PATH), latest_status="ACCEPTED", elapsed_time_s=perf_counter() - started)
        assert final is not None
        final_load = np.asarray(model["normal_load_full"]) + FROZEN_LOAD_PATH[-1][1] * np.asarray(model["tangent_load_full"])
        observables = _reference_observables(model, final, final_load)
        production_observables = _production_observables(production)
        deltas = _deltas(observables, production_observables)
        checks = {
            "finite": bool(np.isfinite(np.asarray(final["displacement"])).all() and np.isfinite(np.asarray(final["gaps"])).all() and np.isfinite(np.asarray(final["pressures"])).all() and np.isfinite(np.asarray(final["forces"])).all()),
            "seven_accepted_increments": len(step_results) == 7,
            "force_equilibrium": float(observables["force_balance_relative_error"]) <= 1.0e-8,
            "moment_equilibrium": float(observables["moment_balance_relative_error"]) <= 1.0e-8,
            "contact_states_finite": all(state in {"open", "stick", "slip"} for state in final["states"]),
            "open_contacts_zero_force": all(np.linalg.norm(final["forces"][index]) == 0.0 for index, state in enumerate(final["states"]) if state == "open"),
            "reference_deltas": all(value <= limit for value, limit in ((deltas["displacement"], 0.02), (deltas["reaction"], 0.02), (deltas["moment"], 0.02), (deltas["normal_contact"], 0.03), (deltas["tangential_contact"], 0.03), (deltas["dissipation"], 0.05))),
            "active_set_matches_production": list(final["active"]) == _production_active_contacts(production),
            "terminal_production_pass": production.get("status") == "PASS",
        }
        status = "PASS" if all(checks.values()) else "FAIL_CLOSED"
        payload = {
            "schema_version": 1,
            "status": status,
            "terminal_classification": "PASS_REFERENCE" if status == "PASS" else "REFERENCE_MISMATCH",
            "mesh": mesh_name,
            "subdivision": list(MESH_SUBDIVISIONS[mesh_name]),
            "node_count": int(model["node_count"]),
            "element_count": int(model["element_count"]),
            "ndof": int(model["ndof"]),
            "reference_implementation": "independent_numpy_dense_kkt_return_map",
            "production_contact_routines_called": False,
            "load_path": [{"increment": index, "normal_factor": normal, "tangential_factor": tangential} for index, (normal, tangential) in enumerate(FROZEN_LOAD_PATH, start=1)],
            "step_results": step_results,
            "observables": observables,
            "deltas_vs_production": deltas,
            "checks": checks,
            "fallback_count": 0,
            "active_set_history": [item["history"] for item in step_results],
            "provenance": {"branch": branch, "source_sha": sha, "contract_digest": CONTRACT_DIGEST, "policy_digest": POLICY_DIGEST, "production_result": str(production_result.resolve()), "source_package": "INDEPENDENT_NO_SOLVEUR_CONTACT_IMPORT"},
            "qualification_claim": "INDEPENDENT_REFERENCE_ONLY_NOT_FORMAL_WP08D_CLOSURE",
        }
        full_final = _full_displacement(model, np.asarray(final["displacement"]))
        np.savez_compressed(output_dir / "raw.npz", displacement=full_final.reshape((-1, 3)), contact_forces=np.asarray(final["forces"]), contact_pressures=np.asarray(final["pressures"]), contact_states=np.asarray(final["states"], dtype=str), load_factors=np.asarray(FROZEN_LOAD_PATH, dtype=float), accepted_state_digests=np.asarray(accepted_hashes, dtype=str))
        _write_json(output_dir / "result.json", payload)
        _emit(telemetry_path, "RUN_END", started=started, status="COMPLETED" if status == "PASS" else "FAILED", mesh=mesh_name, phase="RUN_END", terminal_status=status)
        _progress(progress_path, status="COMPLETED" if status == "PASS" else "FAILED", phase="RUN_END", mesh=mesh_name, terminal_classification=payload["terminal_classification"], elapsed_time_s=perf_counter() - started)
        _append_console(console_path, f"RUN_END status={status}")
        manifest = _manifest(output_dir, mesh_name, "COMPLETED", str(payload["terminal_classification"]), str(payload["qualification_claim"]), branch, sha, production_result)
        manifest.update({"node_count": int(model["node_count"]), "element_count": int(model["element_count"]), "ndof": int(model["ndof"]), "fallback_count": 0})
        _write_json(output_dir / "manifest.json", manifest)
        return payload
    except Exception as error:
        _append_console(error_path, f"REFERENCE_FAIL_CLOSED: {type(error).__name__}: {error}")
        _emit(telemetry_path, "RUN_FAILED", started=started, status="FAILED", mesh=mesh_name, phase="RUN_FAILED", error_type=type(error).__name__, error_message=str(error))
        _progress(progress_path, status="FAILED", phase="RUN_FAILED", mesh=mesh_name, error_type=type(error).__name__, error_message=str(error), elapsed_time_s=perf_counter() - started)
        _append_console(console_path, f"RUN_END status=FAIL_CLOSED error={type(error).__name__}")
        if final is None:
            failure_displacement: np.ndarray = np.zeros(int(model["ndof"]), dtype=float)
            failure_forces: np.ndarray = np.zeros((len(model["slave_nodes"]), 2), dtype=float)
            failure_pressures: np.ndarray = np.zeros(len(model["slave_nodes"]), dtype=float)
            failure_states = np.asarray(["open"] * len(model["slave_nodes"]), dtype=str)
        else:
            failure_displacement = np.asarray(final["displacement"], dtype=float)
            failure_forces = np.asarray(final["forces"], dtype=float)
            failure_pressures = np.asarray(final["pressures"], dtype=float)
            failure_states = np.asarray(final["states"], dtype=str)
        failure_payload = {
            "schema_version": 1,
            "status": "FAIL_CLOSED",
            "terminal_classification": "REFERENCE_FAILURE",
            "failure": {"type": type(error).__name__, "message": str(error)},
            "mesh": mesh_name,
            "subdivision": list(MESH_SUBDIVISIONS[mesh_name]),
            "node_count": int(model["node_count"]),
            "element_count": int(model["element_count"]),
            "ndof": int(model["ndof"]),
            "reference_implementation": "independent_numpy_dense_kkt_return_map",
            "production_contact_routines_called": False,
            "load_path": [{"increment": index, "normal_factor": normal, "tangential_factor": tangential} for index, (normal, tangential) in enumerate(FROZEN_LOAD_PATH, start=1)],
            "accepted_step_count": len(step_results),
            "accepted_steps": step_results,
            "fallback_count": 0,
            "provenance": {"branch": branch, "source_sha": sha, "contract_digest": CONTRACT_DIGEST, "policy_digest": POLICY_DIGEST, "production_result": str(production_result.resolve()), "source_package": "INDEPENDENT_NO_SOLVEUR_CONTACT_IMPORT"},
            "qualification_claim": "INDEPENDENT_REFERENCE_ONLY_NOT_FORMAL_WP08D_CLOSURE",
        }
        np.savez_compressed(
            output_dir / "raw.npz",
            displacement=_full_displacement(model, failure_displacement).reshape((-1, 3)),
            contact_forces=failure_forces,
            contact_pressures=failure_pressures,
            contact_states=failure_states,
            load_factors=np.asarray(FROZEN_LOAD_PATH, dtype=float),
            accepted_state_digests=np.asarray(accepted_hashes, dtype=str),
        )
        _write_json(output_dir / "result.json", failure_payload)
        failure_manifest = _manifest(output_dir, mesh_name, "FAILED", "REFERENCE_FAILURE", str(failure_payload["qualification_claim"]), branch, sha, production_result)
        failure_manifest.update({"node_count": int(model["node_count"]), "element_count": int(model["element_count"]), "ndof": int(model["ndof"]), "fallback_count": 0, "accepted_step_count": len(step_results)})
        _write_json(output_dir / "manifest.json", failure_manifest)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", choices=("M2", "M3"), required=True)
    parser.add_argument("--production-result", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        payload = run(args.mesh, args.production_result, args.output_dir)
    except Exception as error:
        print(f"WP08D_INDEPENDENT_REFERENCE_FAIL_CLOSED: {error}", file=sys.stderr)
        return 3
    print(f"WP08D_INDEPENDENT_REFERENCE_{payload['status']} mesh={args.mesh}")
    return 0 if payload["status"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
