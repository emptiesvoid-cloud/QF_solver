"""Independent diagnostic enumeration of WP08-D M2 step-3 stick/slip modes.

This module is deliberately self-contained: it creates the frozen M2 TET4
mesh, assembles linear elasticity, applies the exact fixed normal constraints,
and evaluates the Coulomb return map with NumPy/SciPy only.  It must never
import or call a production contact solver.  Its result is forensic evidence,
not a qualification decision or a production-mechanics patch.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
from scipy.optimize import least_squares


M2_SUBDIVISION = (4, 2, 2)
LENGTH = 2.0
WIDTH = 1.0
HEIGHT = 0.5
INITIAL_CLEARANCE = 0.02
YOUNG_MODULUS = 1.0e6
POISSON_RATIO = 0.3
FRICTION_COEFFICIENT = 0.3
TANGENTIAL_STIFFNESS = 1.0e6
GAP_TOLERANCE = 1.0e-10
FRICTION_TOLERANCE = 1.0e-9
ACTIVE_CONTACTS = (3, 7, 11)


@dataclass(frozen=True)
class IndependentM2Problem:
    """Frozen free-DOF system and explicit contact rows for one diagnostic."""

    stiffness: np.ndarray
    load_step3: np.ndarray
    normal_rows: np.ndarray
    tangent_rows: np.ndarray
    slave_z_rows: np.ndarray
    free_indices: np.ndarray
    prior_references: np.ndarray
    prior_forces: np.ndarray


def canonical_json_digest(payload: object) -> str:
    """Return the byte digest used for checkpoint provenance checks."""

    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()


def mode_labels() -> tuple[str, ...]:
    """Return all eight deterministic stick/slip masks for the three contacts."""

    return tuple("".join(mask) for mask in itertools.product(("S", "K"), repeat=len(ACTIVE_CONTACTS)))


def _node_index(i: int, j: int, k: int, nx: int, ny: int) -> int:
    return (k * (ny + 1) + j) * (nx + 1) + i


def _oriented_tet(tet: tuple[int, int, int, int], nodes: np.ndarray) -> tuple[int, int, int, int]:
    coordinates = nodes[list(tet)]
    determinant = float(np.linalg.det(np.column_stack((coordinates[1] - coordinates[0], coordinates[2] - coordinates[0], coordinates[3] - coordinates[0]))))
    if determinant < 0.0:
        return (tet[0], tet[1], tet[3], tet[2])
    if determinant == 0.0 or not np.isfinite(determinant):
        raise ValueError("Frozen M2 mesh contains a degenerate TET4.")
    return tet


def _m2_mesh() -> tuple[np.ndarray, tuple[tuple[int, int, int, int], ...], tuple[tuple[int, int, int], ...], tuple[int, ...], tuple[int, ...]]:
    """Build the exact frozen M2 body and fixed master-plane metadata."""

    nx, ny, nz = M2_SUBDIVISION
    body = np.asarray(
        [
            [LENGTH * i / nx, WIDTH * j / ny, INITIAL_CLEARANCE + HEIGHT * k / nz]
            for k in range(nz + 1)
            for j in range(ny + 1)
            for i in range(nx + 1)
        ],
        dtype=float,
    )
    master = np.asarray([[0.0, 0.0, 0.0], [LENGTH, 0.0, 0.0], [LENGTH, WIDTH, 0.0], [0.0, WIDTH, 0.0]], dtype=float)
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
                    (v000, v100, v110, v111), (v000, v110, v010, v111),
                    (v000, v010, v011, v111), (v000, v011, v001, v111),
                    (v000, v001, v101, v111), (v000, v101, v100, v111),
                )
                elements.extend(_oriented_tet(tet, nodes) for tet in raw)
    top_faces: list[tuple[int, int, int]] = []
    faces: dict[tuple[int, int, int], int] = {}
    for tet in elements:
        for face in ((tet[0], tet[1], tet[2]), (tet[0], tet[1], tet[3]), (tet[0], tet[2], tet[3]), (tet[1], tet[2], tet[3])):
            ordered = sorted(face)
            key = (ordered[0], ordered[1], ordered[2])
            faces[key] = faces.get(key, 0) + 1
    for face, count in faces.items():
        if count == 1 and np.allclose(nodes[list(face), 2], INITIAL_CLEARANCE + HEIGHT, rtol=0.0, atol=1.0e-14):
            top_faces.append(face)
    slave_nodes = tuple(_node_index(i, j, 0, nx, ny) for j in range(ny + 1) for i in range(1, nx + 1))
    fixed_body = tuple(_node_index(0, j, k, nx, ny) for k in range(nz + 1) for j in range(ny + 1))
    return nodes, tuple(elements), tuple(top_faces), slave_nodes, fixed_body


def _elasticity_matrix() -> np.ndarray:
    coefficient = YOUNG_MODULUS / ((1.0 + POISSON_RATIO) * (1.0 - 2.0 * POISSON_RATIO))
    matrix: np.ndarray = np.zeros((6, 6), dtype=float)
    matrix[:3, :3] = POISSON_RATIO
    np.fill_diagonal(matrix[:3, :3], 1.0 - POISSON_RATIO)
    matrix[3:, 3:] = np.eye(3) * (1.0 - 2.0 * POISSON_RATIO) / 2.0
    return coefficient * matrix


def _tet4_stiffness(coordinates: np.ndarray) -> np.ndarray:
    interpolation = np.column_stack((np.ones(4), coordinates))
    inverse = np.linalg.inv(interpolation)
    gradients = inverse[1:, :].T
    b_matrix: np.ndarray = np.zeros((6, 12), dtype=float)
    for index, (dx, dy, dz) in enumerate(gradients):
        offset = 3 * index
        b_matrix[:, offset : offset + 3] = np.asarray(
            ((dx, 0.0, 0.0), (0.0, dy, 0.0), (0.0, 0.0, dz), (dy, dx, 0.0), (0.0, dz, dy), (dz, 0.0, dx)),
            dtype=float,
        )
    edge_matrix = np.column_stack(
        (coordinates[1] - coordinates[0], coordinates[2] - coordinates[0], coordinates[3] - coordinates[0])
    )
    volume = abs(float(np.linalg.det(edge_matrix))) / 6.0
    return volume * (b_matrix.T @ _elasticity_matrix() @ b_matrix)


def _surface_load(nodes: np.ndarray, top_faces: Iterable[tuple[int, int, int]], resultant: np.ndarray) -> np.ndarray:
    vector: np.ndarray = np.zeros(3 * len(nodes), dtype=float)
    faces = tuple(top_faces)
    area = sum(0.5 * np.linalg.norm(np.cross(nodes[face[1]] - nodes[face[0]], nodes[face[2]] - nodes[face[0]])) for face in faces)
    traction = np.asarray(resultant, dtype=float) / area
    for face in faces:
        coordinates = nodes[list(face)]
        face_area = 0.5 * np.linalg.norm(np.cross(coordinates[1] - coordinates[0], coordinates[2] - coordinates[0]))
        for node in face:
            vector[3 * node : 3 * node + 3] += traction * face_area / 3.0
    return vector


def _checkpoint_state(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    state = payload.get("committed_contact_state") if isinstance(payload, Mapping) else None
    required = {"step", "displacement", "multipliers", "gaps", "pressures", "active_contacts", "tangential_states", "tangential_forces", "slip_references"}
    if not isinstance(state, Mapping) or not required.issubset(state) or state.get("step") != 2:
        raise ValueError("The input is not a complete committed WP08-D M2 step-2 checkpoint.")
    return state


def build_problem(checkpoint: Path) -> IndependentM2Problem:
    """Assemble the frozen independent M2 step-3 KKT data from checkpoint evidence."""

    state = _checkpoint_state(checkpoint)
    nodes, elements, top_faces, slave_nodes, fixed_body = _m2_mesh()
    ndof = 3 * len(nodes)
    stiffness: np.ndarray = np.zeros((ndof, ndof), dtype=float)
    for tet in elements:
        local = _tet4_stiffness(nodes[list(tet)])
        dofs = np.asarray([3 * node + component for node in tet for component in range(3)], dtype=int)
        stiffness[np.ix_(dofs, dofs)] += local
    fixed = np.asarray([3 * node + component for node in (*fixed_body, 45, 46, 47, 48) for component in range(3)], dtype=int)
    free = np.setdiff1d(np.arange(ndof, dtype=int), fixed)
    normal = _surface_load(nodes, top_faces, np.asarray((0.0, 0.0, -1000.0)))
    tangent = _surface_load(nodes, top_faces, np.asarray((300.0, 0.0, 0.0)))
    step3_load = (normal + 0.75 * tangent)[free]
    normal_rows = np.zeros((len(ACTIVE_CONTACTS), free.size), dtype=float)
    tangent_rows = np.zeros((len(ACTIVE_CONTACTS), 2, free.size), dtype=float)
    slave_z_rows = np.zeros((len(slave_nodes), free.size), dtype=float)
    free_lookup = {int(value): index for index, value in enumerate(free)}
    for contact, node in enumerate(slave_nodes):
        z_dof = 3 * node + 2
        slave_z_rows[contact, free_lookup[z_dof]] = 1.0
    for position, contact in enumerate(ACTIVE_CONTACTS):
        node = slave_nodes[contact]
        normal_rows[position] = slave_z_rows[contact]
        tangent_rows[position, 0, free_lookup[3 * node]] = 1.0
        tangent_rows[position, 1, free_lookup[3 * node + 1]] = 1.0
    return IndependentM2Problem(
        stiffness=stiffness[np.ix_(free, free)],
        load_step3=step3_load,
        normal_rows=normal_rows,
        tangent_rows=tangent_rows,
        slave_z_rows=slave_z_rows,
        free_indices=free,
        prior_references=np.asarray(state["slip_references"], dtype=float),
        prior_forces=np.asarray(state["tangential_forces"], dtype=float),
    )


def post_normal_active_set(gaps: np.ndarray, pressures: np.ndarray, active: tuple[int, ...]) -> tuple[int, ...]:
    """Apply the frozen normal Kuhn-Tucker update without production helpers."""

    proposed = tuple(
        index for index, gap in enumerate(gaps)
        if gap < -GAP_TOLERANCE or (index in active and gap <= GAP_TOLERANCE and pressures[index] >= -GAP_TOLERANCE)
    )
    tensile = {index for index in active if pressures[index] < -GAP_TOLERANCE}
    return tuple(index for index in proposed if index not in tensile)


def _solve_fixed_mode(problem: IndependentM2Problem, label: str) -> dict[str, Any]:
    """Solve one fixed stick/slip mask using its explicit independent KKT system."""

    if label not in mode_labels():
        raise ValueError("Unknown stick/slip mask.")
    stick_positions = tuple(index for index, state in enumerate(label) if state == "S")
    slip_positions = tuple(index for index, state in enumerate(label) if state == "K")
    stiffness = problem.stiffness.copy()
    rhs_base = problem.load_step3.copy()
    for position in stick_positions:
        contact = ACTIVE_CONTACTS[position]
        rows = problem.tangent_rows[position]
        reference = problem.prior_references[contact]
        stiffness += TANGENTIAL_STIFFNESS * (rows.T @ rows)
        rhs_base += TANGENTIAL_STIFFNESS * rows.T @ reference
    constraints = problem.normal_rows
    values: np.ndarray = np.full(len(ACTIVE_CONTACTS), -INITIAL_CLEARANCE, dtype=float)

    def equilibrium(force_vector: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        rhs = rhs_base.copy()
        for local, position in enumerate(slip_positions):
            rhs -= problem.tangent_rows[position].T @ force_vector[2 * local : 2 * local + 2]
        saddle = np.block(
            [[stiffness, constraints.T], [constraints, np.zeros((constraints.shape[0], constraints.shape[0]), dtype=float)]]
        )
        solution = np.linalg.solve(saddle, np.concatenate((rhs, values)))
        displacement = solution[: stiffness.shape[0]]
        multipliers = solution[stiffness.shape[0] :]
        pressures = -multipliers
        return displacement, multipliers, pressures, rhs

    initial = np.concatenate(tuple(problem.prior_forces[ACTIVE_CONTACTS[position]] for position in slip_positions)) if slip_positions else np.zeros(0, dtype=float)

    def residual(force_vector: np.ndarray) -> np.ndarray:
        displacement, _multipliers, pressures, _rhs = equilibrium(force_vector)
        result: list[float] = []
        for local, position in enumerate(slip_positions):
            contact = ACTIVE_CONTACTS[position]
            trial = TANGENTIAL_STIFFNESS * (problem.tangent_rows[position] @ displacement - problem.prior_references[contact])
            norm = float(np.linalg.norm(trial))
            if norm == 0.0:
                target: np.ndarray = np.zeros(2, dtype=float)
            else:
                target = FRICTION_COEFFICIENT * max(float(pressures[position]), 0.0) * trial / norm
            result.extend(force_vector[2 * local : 2 * local + 2] - target)
        return np.asarray(result, dtype=float)

    if slip_positions:
        root = least_squares(residual, initial, xtol=FRICTION_TOLERANCE, ftol=FRICTION_TOLERANCE, gtol=FRICTION_TOLERANCE, max_nfev=4096)
        force_vector = np.asarray(root.x, dtype=float)
        root_status = {"attempted": True, "success": bool(root.success), "status": int(root.status), "message": str(root.message), "evaluations": int(root.nfev)}
    else:
        force_vector = np.zeros(0, dtype=float)
        root_status = {"attempted": False, "success": True, "status": 0, "message": "linear stick KKT", "evaluations": 0}
    displacement, multipliers, active_pressures, _rhs = equilibrium(force_vector)
    forces: np.ndarray = np.zeros((12, 2), dtype=float)
    references = problem.prior_references.copy()
    states = ["open"] * 12
    for position, contact in enumerate(ACTIVE_CONTACTS):
        relative = problem.tangent_rows[position] @ displacement
        trial = TANGENTIAL_STIFFNESS * (relative - problem.prior_references[contact])
        if position in stick_positions:
            forces[contact] = trial
            states[contact] = "stick"
        else:
            local = slip_positions.index(position)
            forces[contact] = force_vector[2 * local : 2 * local + 2]
            references[contact] = relative - forces[contact] / TANGENTIAL_STIFFNESS
            states[contact] = "slip"
    residual_vector = residual(force_vector)
    residual_norm = float(np.linalg.norm(residual_vector, ord=np.inf)) if residual_vector.size else 0.0
    gaps = INITIAL_CLEARANCE + problem.slave_z_rows @ displacement
    pressures: np.ndarray = np.zeros(12, dtype=float)
    pressures[list(ACTIVE_CONTACTS)] = active_pressures
    post_active = post_normal_active_set(gaps, pressures, ACTIVE_CONTACTS)
    admissibility: dict[str, bool] = {
        "finite": bool(np.isfinite(displacement).all() and np.isfinite(forces).all() and np.isfinite(references).all()),
        "root_residual": residual_norm <= FRICTION_TOLERANCE,
        "normal_set": post_active == ACTIVE_CONTACTS,
        "active_gaps": bool(np.all(np.abs(gaps[list(ACTIVE_CONTACTS)]) <= GAP_TOLERANCE)),
        "open_gaps": bool(np.all(gaps[[index for index in range(12) if index not in ACTIVE_CONTACTS]] >= -GAP_TOLERANCE)),
        "compressive_pressures": bool(np.all(active_pressures >= -GAP_TOLERANCE)),
    }
    mode_checks: list[dict[str, object]] = []
    for position, contact in enumerate(ACTIVE_CONTACTS):
        trial = TANGENTIAL_STIFFNESS * (problem.tangent_rows[position] @ displacement - problem.prior_references[contact])
        force_norm = float(np.linalg.norm(forces[contact]))
        trial_norm = float(np.linalg.norm(trial))
        limit = FRICTION_COEFFICIENT * max(float(active_pressures[position]), 0.0)
        if label[position] == "S":
            valid = force_norm <= limit + FRICTION_TOLERANCE
            condition = "STICK_INSIDE_CONE"
        else:
            aligned = float(forces[contact] @ trial) >= -FRICTION_TOLERANCE
            valid = abs(force_norm - limit) <= FRICTION_TOLERANCE and trial_norm >= limit - FRICTION_TOLERANCE and aligned
            condition = "SLIP_ON_CONE_ALIGNED"
        mode_checks.append({"contact": contact, "state": states[contact], "condition": condition, "valid": bool(valid), "trial_norm": trial_norm, "force_norm": force_norm, "limit": limit})
    admissibility["tangential_modes"] = all(bool(item["valid"]) for item in mode_checks)
    admissible = all(admissibility.values())
    return {
        "mode": label,
        "status": "ADMISSIBLE" if admissible else "REJECTED",
        "root": root_status,
        "root_residual_inf": residual_norm,
        "post_root_normal_active_contacts": list(post_active),
        "admissibility": admissibility,
        "mode_checks": mode_checks,
        "active_pressures": active_pressures.tolist(),
        "gaps": gaps.tolist(),
        "tangential_forces": forces.tolist(),
        "tangential_states": states,
        "slip_references": references.tolist(),
    }


def enumerate_modes(checkpoint: Path, *, input_provenance: str = "UNSPECIFIED") -> dict[str, Any]:
    """Enumerate and independently test all fixed step-3 stick/slip masks."""

    state = _checkpoint_state(checkpoint)
    problem = build_problem(checkpoint)
    candidates = [_solve_fixed_mode(problem, label) for label in mode_labels()]
    admissible = [candidate["mode"] for candidate in candidates if candidate["status"] == "ADMISSIBLE"]
    return {
        "schema_version": 1,
        "kind": "WP08D_M2_STEP3_INDEPENDENT_STICK_SLIP_MODE_ENUMERATION",
        "qualification_claim": "DIAGNOSTIC_ONLY_NO_FORMAL_WP08D_CREDIT",
        "production_contact_implementation_called": False,
        "checkpoint": {
            "path": str(checkpoint.as_posix()),
            "sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
            "step": state["step"],
            "input_provenance": input_provenance,
        },
        "frozen_parameters": {"mesh": "M2", "step": 3, "active_contacts": list(ACTIVE_CONTACTS), "gap_tolerance": GAP_TOLERANCE, "friction_tolerance": FRICTION_TOLERANCE, "friction_coefficient": FRICTION_COEFFICIENT, "tangential_stiffness": TANGENTIAL_STIFFNESS},
        "candidate_modes": candidates,
        "admissible_modes": admissible,
        "admissible_mode_count": len(admissible),
        "final_classification": "ADMISSIBLE_MODE_FOUND" if admissible else "NO_ADMISSIBLE_FIXED_MODE",
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--input-provenance", default="UNSPECIFIED")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    result = enumerate_modes(args.checkpoint, input_provenance=args.input_provenance)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True))
        stream.write("\n")
    print("MODE_ENUMERATION_COMPLETED classification=%s admissible=%d" % (result["final_classification"], result["admissible_mode_count"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
