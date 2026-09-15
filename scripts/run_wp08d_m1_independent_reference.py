"""Run the independent WP08-D M1 KKT reference once.

The reference assembles the small linear-elastic TET4 system locally and uses
the pure NumPy KKT/regularized-Coulomb module.  It does not import or call
production contact routines.  M1 is intentionally reported as an open-contact
case when the frozen load path leaves every slave gap non-negative.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter
from typing import Any

import numpy as np

if __package__ in {None, ""}:
    _repository_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(_repository_root))

from scripts.wp08d_independent_kkt_reference import KktReferenceProblem, solve_kkt_return_map
from scripts.wp08d_phase1_common import (
    CONTRACT_DIGEST,
    POLICY_DIGEST,
    REQUIRED_GOVERNING_SHA,
    Phase1Telemetry,
    write_json,
    write_manifest,
)


LENGTH = 2.0
WIDTH = 1.0
HEIGHT = 0.5
INITIAL_CLEARANCE = 0.02
TOP_Z = INITIAL_CLEARANCE + HEIGHT
YOUNG_MODULUS = 1.0e6
POISSON_RATIO = 0.3
LOAD_PATH = (
    (1.0, 0.0),
    (1.0, 0.25),
    (1.0, 0.75),
    (1.0, 1.0),
    (1.0, 1.25),
    (1.0, 0.25),
    (1.0, -0.5),
)


def _node_index(i: int, j: int, k: int) -> int:
    return (k * 2 + j) * 3 + i


def _m1_mesh() -> tuple[np.ndarray, tuple[tuple[int, int, int, int], ...], tuple[tuple[int, int, int], ...]]:
    body = np.asarray(
        [
            [LENGTH * i / 2.0, WIDTH * j, INITIAL_CLEARANCE + HEIGHT * k]
            for k in range(2)
            for j in range(2)
            for i in range(3)
        ],
        dtype=float,
    )
    master = np.asarray(
        [[0.0, 0.0, 0.0], [LENGTH, 0.0, 0.0], [LENGTH, WIDTH, 0.0], [0.0, WIDTH, 0.0]],
        dtype=float,
    )
    nodes = np.vstack((body, master))
    elements: list[tuple[int, int, int, int]] = []
    for k in range(1):
        for j in range(1):
            for i in range(2):
                v000 = _node_index(i, j, k)
                v100 = _node_index(i + 1, j, k)
                v110 = _node_index(i + 1, j + 1, k)
                v010 = _node_index(i, j + 1, k)
                v001 = _node_index(i, j, k + 1)
                v101 = _node_index(i + 1, j, k + 1)
                v111 = _node_index(i + 1, j + 1, k + 1)
                v011 = _node_index(i, j + 1, k + 1)
                raw = (
                    (v000, v100, v110, v111),
                    (v000, v110, v010, v111),
                    (v000, v010, v011, v111),
                    (v000, v011, v001, v111),
                    (v000, v001, v101, v111),
                    (v000, v101, v100, v111),
                )
                for tet in raw:
                    signed = _tet_volume(nodes[list(tet)])
                    if signed < 0.0:
                        tet = (tet[0], tet[1], tet[3], tet[2])
                        signed = _tet_volume(nodes[list(tet)])
                    if signed <= 0.0 or not np.isfinite(signed):
                        raise ValueError("Independent M1 mesh contains a non-positive TET4 volume.")
                    elements.append(tet)

    boundary_counts: dict[tuple[int, int, int], int] = {}
    for a, b, c, d in elements:
        for face in ((a, b, c), (a, b, d), (a, c, d), (b, c, d)):
            ordered = sorted(face)
            key = (int(ordered[0]), int(ordered[1]), int(ordered[2]))
            boundary_counts[key] = boundary_counts.get(key, 0) + 1
    top_faces = tuple(
        face
        for face, count in sorted(boundary_counts.items())
        if count == 1 and np.allclose(nodes[list(face), 2], TOP_Z, rtol=0.0, atol=1.0e-14)
    )
    return nodes, tuple(elements), top_faces


def _tet_volume(coords: np.ndarray) -> float:
    matrix = np.column_stack((coords[1] - coords[0], coords[2] - coords[0], coords[3] - coords[0]))
    return float(np.linalg.det(matrix) / 6.0)


def _elasticity_matrix() -> np.ndarray:
    factor = YOUNG_MODULUS / ((1.0 + POISSON_RATIO) * (1.0 - 2.0 * POISSON_RATIO))
    lam = POISSON_RATIO * factor
    mu = YOUNG_MODULUS / (2.0 * (1.0 + POISSON_RATIO))
    matrix: np.ndarray = np.zeros((6, 6), dtype=float)
    matrix[:3, :3] = lam
    np.fill_diagonal(matrix[:3, :3], lam + 2.0 * mu)
    matrix[3, 3] = mu
    matrix[4, 4] = mu
    matrix[5, 5] = mu
    return matrix


def _strain_displacement(coords: np.ndarray) -> np.ndarray:
    interpolation = np.column_stack((np.ones(4), coords))
    gradients = np.linalg.inv(interpolation)[1:, :].T
    matrix: np.ndarray = np.zeros((6, 12), dtype=float)
    for index, (gx, gy, gz) in enumerate(gradients):
        column = 3 * index
        matrix[0, column] = gx
        matrix[1, column + 1] = gy
        matrix[2, column + 2] = gz
        matrix[3, column] = gy
        matrix[3, column + 1] = gx
        matrix[4, column + 1] = gz
        matrix[4, column + 2] = gy
        matrix[5, column] = gz
        matrix[5, column + 2] = gx
    return matrix


def _assemble_stiffness(nodes: np.ndarray, elements: tuple[tuple[int, int, int, int], ...]) -> np.ndarray:
    stiffness: np.ndarray = np.zeros((48, 48), dtype=float)
    elasticity = _elasticity_matrix()
    for element in elements:
        coords = nodes[list(element)]
        volume = _tet_volume(coords)
        local = volume * (_strain_displacement(coords).T @ elasticity @ _strain_displacement(coords))
        indices = np.asarray([3 * node + component for node in element for component in range(3)], dtype=int)
        stiffness[np.ix_(indices, indices)] += local
    return 0.5 * (stiffness + stiffness.T)


def _surface_load(nodes: np.ndarray, faces: tuple[tuple[int, int, int], ...], resultant: np.ndarray) -> np.ndarray:
    area = sum(
        0.5 * np.linalg.norm(np.cross(nodes[face[1]] - nodes[face[0]], nodes[face[2]] - nodes[face[0]]))
        for face in faces
    )
    traction = np.asarray(resultant, dtype=float) / area
    values: np.ndarray = np.zeros((16, 3), dtype=float)
    for face in faces:
        coordinates = nodes[list(face)]
        face_area = 0.5 * np.linalg.norm(np.cross(coordinates[1] - coordinates[0], coordinates[2] - coordinates[0]))
        contribution = traction * face_area / 3.0
        for node in face:
            values[node] += contribution
    return values.reshape(-1)


def _reaction_and_moment(nodes: np.ndarray, fixed: np.ndarray, stiffness: np.ndarray, displacement: np.ndarray, force: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    residual = stiffness @ displacement - force
    reaction = np.zeros_like(residual)
    reaction[fixed] = residual[fixed]
    vectors = reaction.reshape((-1, 3))
    return np.sum(vectors, axis=0), np.sum(np.cross(nodes, vectors), axis=0)


def _production_displacement_vector(payload: dict[str, Any]) -> np.ndarray:
    """Decode the production result's explicit node/DOF displacement records."""

    vector: np.ndarray = np.zeros(48, dtype=float)
    rows = payload.get("displacements", [])
    if not isinstance(rows, list):
        raise ValueError("Production displacement evidence is not a list.")
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Production displacement evidence contains a non-object row.")
        node = int(row["node"])
        dofs = row.get("dofs")
        if not isinstance(dofs, dict):
            raise ValueError("Production displacement row has no DOF mapping.")
        for offset, name in enumerate(("UX", "UY", "UZ")):
            vector[3 * node + offset] = float(dofs[name])
    if not np.all(np.isfinite(vector)):
        raise ValueError("Production displacement evidence is non-finite.")
    return vector


def _relative_delta(left: np.ndarray | float, right: np.ndarray | float) -> float:
    left_array = np.asarray(left, dtype=float)
    right_array = np.asarray(right, dtype=float)
    denominator = max(float(np.linalg.norm(left_array)), float(np.linalg.norm(right_array)), 1.0e-14)
    return float(np.linalg.norm(left_array - right_array) / denominator)


def _console(path: Path, message: str) -> None:
    with path.open("a", encoding="utf-8", newline="") as stream:
        stream.write(message + "\n")
        stream.flush()


def run(production_result: Path, output_dir: Path) -> dict[str, Any]:
    started = perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = production_result.resolve()
    production = json.loads(result_path.read_text(encoding="utf-8"))
    nodes, elements, top_faces = _m1_mesh()
    stiffness = _assemble_stiffness(nodes, elements)
    fixed_nodes = tuple(sorted({_node_index(0, 0, 0), _node_index(0, 1, 0), _node_index(0, 0, 1), _node_index(0, 1, 1), 12, 13, 14, 15}))
    fixed = np.asarray([3 * node + component for node in fixed_nodes for component in range(3)], dtype=int)
    constraints = np.eye(48, dtype=float)[fixed]
    normal_load = _surface_load(nodes, top_faces, np.array([0.0, 0.0, -1000.0], dtype=float))
    tangential_load = _surface_load(nodes, top_faces, np.array([300.0, 0.0, 0.0], dtype=float))
    step_results: list[dict[str, Any]] = []
    final_reference = None
    for step_number, (normal_factor, tangential_factor) in enumerate(LOAD_PATH, start=1):
        force = normal_factor * normal_load + tangential_factor * tangential_load
        problem = KktReferenceProblem(
            stiffness=stiffness,
            force=force,
            constraints=constraints,
            constraint_values=np.zeros(fixed.size, dtype=float),
            contacts=(),
        )
        reference = solve_kkt_return_map(problem)
        final_reference = reference
        step_result = reference.to_dict()
        step_result.update({
            "increment": step_number,
            "normal_factor": normal_factor,
            "tangential_factor": tangential_factor,
            "force_norm": float(np.linalg.norm(force)),
        })
        step_results.append(step_result)

    if final_reference is None:
        raise RuntimeError("Independent M1 reference produced no load increments.")
    final_force = normal_load + (-0.5) * tangential_load
    final_displacement = np.asarray(final_reference.displacement, dtype=float)
    reaction_resultant, reaction_moment = _reaction_and_moment(
        nodes, fixed, stiffness, final_displacement, final_force
    )
    slave_nodes = (1, 2, 4, 5)
    gaps = np.asarray([INITIAL_CLEARANCE + final_displacement[3 * node + 2] for node in slave_nodes], dtype=float)
    production_displacement = _production_displacement_vector(production)
    production_observables = production.get("observables", {})
    reference_observables = {
        "selected_displacement": float(np.max(np.linalg.norm(final_displacement.reshape((-1, 3)), axis=1))),
        "reaction_resultant": reaction_resultant.tolist(),
        "reaction_moment": reaction_moment.tolist(),
        "normal_contact_resultant": [0.0, 0.0, 0.0],
        "tangential_contact_resultant": [0.0, 0.0, 0.0],
        "active_contact_count": 0,
        "contact_states": ["open"] * len(slave_nodes),
        "contact_pressures": [0.0] * len(slave_nodes),
        "cumulative_local_dissipation": 0.0,
        "minimum_slave_gap": float(np.min(gaps)),
    }
    deltas = {
        "displacement": _relative_delta(reference_observables["selected_displacement"], production_observables["selected_displacement"]),
        "reaction": _relative_delta(reference_observables["reaction_resultant"], production_observables["reaction_resultant"]),
        "moment": _relative_delta(reference_observables["reaction_moment"], production_observables["reaction_moment"]),
        "normal_contact": _relative_delta(reference_observables["normal_contact_resultant"], production_observables["normal_contact_resultant"]),
        "tangential_contact": _relative_delta(reference_observables["tangential_contact_resultant"], production_observables["tangential_contact_resultant"]),
        "dissipation": _relative_delta(reference_observables["cumulative_local_dissipation"], production_observables["cumulative_local_dissipation"]),
        "full_displacement": _relative_delta(final_displacement, production_displacement),
    }
    external_resultant = np.sum(final_force.reshape((-1, 3)), axis=0)
    external_moment = np.sum(np.cross(nodes, final_force.reshape((-1, 3))), axis=0)
    force_equilibrium = _relative_delta(reaction_resultant, -external_resultant)
    moment_equilibrium = _relative_delta(reaction_moment, -external_moment)
    checks = {
        "finite": bool(np.isfinite(final_displacement).all() and np.isfinite(gaps).all()),
        "open_contact": bool(np.all(gaps >= -1.0e-10)),
        "force_equilibrium": force_equilibrium <= 1.0e-8,
        "moment_equilibrium": moment_equilibrium <= 1.0e-8,
        "reference_deltas": all(
            value <= limit
            for value, limit in (
                (deltas["displacement"], 0.02),
                (deltas["reaction"], 0.02),
                (deltas["moment"], 0.02),
                (deltas["normal_contact"], 0.03),
                (deltas["tangential_contact"], 0.03),
                (deltas["dissipation"], 0.05),
            )
        ),
    }
    status = "PASS" if all(checks.values()) and production.get("status") == "PASS" else "FAIL_CLOSED"
    telemetry = Phase1Telemetry(output_dir / "telemetry.jsonl", analysis_id="WP08D-REFERENCE-M1", mesh="M1")
    telemetry.emit("RUN_START", "ANALYSIS_START", status="STARTED", elapsed=0.0)
    telemetry.emit("MESH_READY", "MESH_READY", status="COMPLETED", elapsed=perf_counter() - started)
    telemetry.emit("ASSEMBLY_START", "ASSEMBLY_START", status="STARTED", elapsed=perf_counter() - started)
    for step_detail in step_results:
        telemetry.emit(
            "KRYLOV_PROGRESS",
            "KRYLOV_PROGRESS",
            status="COMPLETED",
            increment=int(step_detail["increment"]),
            linear_solver="numpy_kkt_direct",
            preconditioner="not_applicable",
            linear_iteration=int(step_detail["iterations"]),
            linear_residual=0.0,
            backward_error_eta_inf={"value": None, "reason": "NOT_COMPUTABLE"},
            elapsed=perf_counter() - started,
        )
        telemetry.emit("STEP_END", "STEP_END", status="ACCEPTED", increment=int(step_detail["increment"]), elapsed=perf_counter() - started)
    telemetry.emit("RUN_END", "ANALYSIS_END", status="COMPLETED" if status == "PASS" else "FAILED", elapsed=perf_counter() - started)
    telemetry.close()
    _console(output_dir / "console.log", "RUN_START independent_reference=M1")
    _console(output_dir / "console.log", "RUN_END status=%s" % status)
    write_json(output_dir / "progress.json", {"schema_version": 1, "status": "COMPLETED" if status == "PASS" else "FAILED", "phase": "RUN_END", "mesh": "M1", "elapsed_time_s": perf_counter() - started})
    raw_steps = np.asarray(
        [hashlib.sha256(json.dumps(step, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest() for step in step_results],
        dtype=str,
    )
    np.savez_compressed(
        output_dir / "raw.npz",
        displacements=final_displacement.reshape((-1, 3)),
        contact_forces=np.zeros((len(slave_nodes), 3), dtype=float),
        contact_pressures=np.zeros(len(slave_nodes), dtype=float),
        contact_states=np.asarray(reference_observables["contact_states"], dtype=str),
        load_factors=np.asarray(LOAD_PATH, dtype=float),
        accepted_state_digests=raw_steps,
    )
    payload = {
        "schema_version": 1,
        "status": status,
        "mesh": "M1",
        "node_count": 16,
        "element_count": 12,
        "ndof": 48,
        "reference_implementation": "independent_numpy_kkt_return_map",
        "production_contact_routines_called": False,
        "open_contact_reference": True,
        "load_path": [
            {"increment": index, "normal_factor": normal, "tangential_factor": tangential}
            for index, (normal, tangential) in enumerate(LOAD_PATH, start=1)
        ],
        "step_results": step_results,
        "observables": reference_observables,
        "deltas_vs_production": deltas,
        "equilibrium": {"force_relative_error": force_equilibrium, "moment_relative_error": moment_equilibrium},
        "checks": checks,
        "terminal_classification": "PASS_REFERENCE" if status == "PASS" else "REFERENCE_MISMATCH",
        "qualification_claim": "INDEPENDENT_M1_REFERENCE_ONLY_NOT_FORMAL_WP08_CLOSURE",
        "provenance": {
            "governing_sha": REQUIRED_GOVERNING_SHA,
            "contract_digest": CONTRACT_DIGEST,
            "policy_digest": POLICY_DIGEST,
            "production_result": str(result_path),
        },
    }
    terminal_classification = str(payload["terminal_classification"])
    qualification_claim = str(payload["qualification_claim"])
    write_json(output_dir / "result.json", payload)
    manifest = write_manifest(
        output_dir,
        mesh_name="M1",
        terminal_status="COMPLETED" if status == "PASS" else "FAILED",
        terminal_classification=terminal_classification,
        qualification_claim=qualification_claim,
        frozen_parameters={
            "reference": "independent_numpy_kkt_return_map",
            "production_contact_routines_called": False,
            "load_increments": 7,
            "backend": "numpy_dense_kkt",
        },
    )
    manifest.update({"reference_implementation": "independent_numpy_kkt_return_map", "production_contact_routines_called": False})
    write_json(output_dir / "manifest.json", manifest)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--production-result", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        payload = run(args.production_result, args.output_dir)
    except Exception as error:
        print(f"WP08D_REFERENCE_FAIL_CLOSED: {error}", file=sys.stderr)
        return 3
    print(f"WP08D_REFERENCE_{payload['status']}")
    return 0 if payload["status"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
