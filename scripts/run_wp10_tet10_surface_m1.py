"""WP10 TET10 M1 requalification with consistent quadratic surface traction.

This runner is evidence tooling for a new, bounded TET10 contract.  It does
not alter production mechanics, solver thresholds, fallback policy, or the
historical TET10 failure.  The load is integrated on every x=1 quadratic
boundary face through the public distributed-load path instead of being
split equally between loaded nodes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, cast

import numpy as np

from solveur.api import solve_model
from solveur.core.model import FiniteElementModel
from solveur.loads.integration import DistributedLoadIntegrator
from solveur.mesh.topology import TET10_FACES
from solveur.verification.robustness_mesh import mesh_refinement_mesh


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "qualification" / "0_2_9" / "wp10_tet10_surface_r1_contract.json"
POLICY_DIGEST = "93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac"
ELEMENT_TYPE = "TET10"
REFERENCE_RESULTANT = 0.25
LEVEL_CELLS = {"H1": 1, "H2": 2, "H3": 4}
LOAD_PATH = (0.2, 0.4, 0.6, 0.8, 1.0)
TRACTION_DIRECTION = np.asarray((1.0, 0.0, 0.0), dtype=float)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_sha() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _boundary_surface_loads(
    nodes: np.ndarray,
    elements: list[list[int]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Return one consistent quadratic traction per unique x=1 TET10 face."""
    candidates: list[tuple[int, int, tuple[int, ...], float]] = []
    seen: set[frozenset[int]] = set()
    for element_index, element in enumerate(elements):
        for face_index, local_face in enumerate(TET10_FACES):
            global_face = tuple(int(element[position]) for position in local_face)
            key = frozenset(global_face)
            face_coords = nodes[list(global_face)]
            if key in seen or not np.allclose(face_coords[:, 0], 1.0):
                continue
            corners = face_coords[:3]
            area = 0.5 * float(np.linalg.norm(np.cross(corners[1] - corners[0], corners[2] - corners[0])))
            if area <= 0.0:
                raise ValueError(f"Degenerate x=1 TET10 face on element {element_index}.")
            seen.add(key)
            candidates.append((element_index, face_index, global_face, area))
    if not candidates:
        raise ValueError("No TET10 x=1 boundary faces were found.")
    total_area = sum(item[3] for item in candidates)
    traction = REFERENCE_RESULTANT / total_area
    loads = [
        {
            "type": "surface_traction",
            "element": element_index,
            "face": face_index,
            "value": (TRACTION_DIRECTION * traction).tolist(),
            "coordinate_system": "global",
            "follower": False,
        }
        for element_index, face_index, _, _ in candidates
    ]
    metadata = {
        "face_count": len(candidates),
        "face_area": [float(item[3]) for item in candidates],
        "total_area": float(total_area),
        "traction_magnitude": float(traction),
        "traction_direction": TRACTION_DIRECTION.tolist(),
        "reference_resultant": [REFERENCE_RESULTANT, 0.0, 0.0],
        "face_ids": [[int(item[0]), int(item[1])] for item in candidates],
    }
    return loads, metadata


def _model(cells: int) -> tuple[FiniteElementModel, dict[str, object]]:
    nodes, elements = mesh_refinement_mesh(ELEMENT_TYPE, cells)
    fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    distributed_loads, surface_metadata = _boundary_surface_loads(nodes, elements)
    model = FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[
            {"type": ELEMENT_TYPE, "nodes": item, "material": "j2"}
            for item in elements
        ],
        materials={
            "j2": {
                "type": "von_mises_elastoplastic_3d",
                "E": 1000.0,
                "nu": 0.3,
                "yield_stress": 0.02,
                "hardening_modulus": 10.0,
            }
        },
        fixed_dofs=[
            {"node": int(node), "dofs": ["UX", "UY", "UZ"]}
            for node in fixed_nodes
        ],
        distributed_loads=distributed_loads,
        analysis={
            "type": "nonlinear_static",
            "method": "newton_raphson",
            "load_path": list(LOAD_PATH),
            "max_iterations": 60,
            "tolerance": 1.0e-7,
            "kinematics": "corotational_j2",
            "corotational_max_local_strain": 0.05,
            "contact_mode": "none",
            "contact_finite_sliding": False,
            "contact_max_penetration": 0.05,
        },
    )
    return model, surface_metadata


def _load_metadata(model: FiniteElementModel) -> dict[str, object]:
    dofs = model.dof_manager()
    integrator = DistributedLoadIntegrator()
    resultant: np.ndarray = np.zeros(3, dtype=float)
    moment: np.ndarray = np.zeros(3, dtype=float)
    contributions: list[dict[str, object]] = []
    for index, load in enumerate(model.distributed_loads):
        integrated = integrator.integrate_sparse(model, dofs, load, index)
        details = dict(integrated.details)
        resultant += np.asarray(details["resultant"], dtype=float)
        moment += np.asarray(details["moment_about_origin"], dtype=float)
        contributions.append(details)
    expected = np.asarray((REFERENCE_RESULTANT, 0.0, 0.0), dtype=float)
    return {
        "resultant": resultant.tolist(),
        "moment_about_origin": moment.tolist(),
        "expected_resultant": expected.tolist(),
        "resultant_error_norm": float(np.linalg.norm(resultant - expected)),
        "contributions": contributions,
    }


def _compact_result(result: Any, model: FiniteElementModel) -> dict[str, object]:
    payload = result.to_dict()
    steps = payload["solver"]["steps"]
    compact_steps = [
        {
            "step": int(step.get("step", index + 1)),
            "load_factor": float(step.get("load_factor", 0.0)),
            "relative_residual": float(step.get("relative_residual", 0.0)),
            "iterations": int(step.get("iterations", 0)),
            "accepted": bool(step.get("accepted", True)),
            "rejected": bool(step.get("rejected", False)),
            "fallback_used": bool(step.get("fallback_used", False)),
            "equivalent_plastic_strain_max": float(
                step.get("equivalent_plastic_strain_max", 0.0)
            ),
        }
        for index, step in enumerate(steps)
    ]
    audit = payload.get("audit", {})
    equilibrium_raw = audit.get("equilibrium", {}) if isinstance(audit, dict) else {}
    equilibrium_keys = (
        "free_relative_residual",
        "force_balance_relative_error",
        "moment_balance_relative_error",
        "external_resultant",
        "reaction_resultant",
        "external_moment_about_origin",
        "reaction_moment_about_origin",
        "force_imbalance",
        "moment_imbalance_about_origin",
    )
    equilibrium = {
        key: equilibrium_raw[key]
        for key in equilibrium_keys
        if isinstance(equilibrium_raw, dict) and key in equilibrium_raw
    }
    det_f_values: list[float] = []
    principal_stretches: list[float] = []
    local_strain_norms: list[float] = []
    for element_result in payload.get("element_results", []):
        if not isinstance(element_result, dict):
            continue
        for point in element_result.get("integration_points", []):
            if not isinstance(point, dict):
                continue
            if "det_f" in point:
                det_f_values.append(float(point["det_f"]))
            if "right_stretch" in point:
                stretch = np.asarray(point["right_stretch"], dtype=float)
                principal_stretches.extend(float(value) for value in np.linalg.eigvalsh(stretch))
            if "corotational_strain_norm" in point:
                local_strain_norms.append(float(point["corotational_strain_norm"]))
    envelope = {
        "min_det_f": min(det_f_values) if det_f_values else None,
        "min_principal_stretch": min(principal_stretches) if principal_stretches else None,
        "max_principal_stretch": max(principal_stretches) if principal_stretches else None,
        "max_corotational_strain_norm": max(local_strain_norms) if local_strain_norms else None,
        "integration_point_count": len(det_f_values),
    }
    return {
        "status": str(result.status),
        "element_type": ELEMENT_TYPE,
        "node_count": int(model.node_count),
        "element_count": int(len(model.elements)),
        "dof_count": int(result.dofs.ndof),
        "displacements": np.asarray(result.displacements, dtype=float).tolist(),
        "steps": compact_steps,
        "final_displacement_norm": float(np.linalg.norm(result.displacements)),
        "max_relative_residual": max(
            (row["relative_residual"] for row in compact_steps), default=0.0
        ),
        "max_peeq": max(
            (row["equivalent_plastic_strain_max"] for row in compact_steps),
            default=0.0,
        ),
        "equilibrium": equilibrium,
        "envelope": envelope,
        "fallback_count": sum(1 for row in compact_steps if row["fallback_used"]),
        "accepted_step_count": sum(1 for row in compact_steps if row["accepted"]),
    }


def _failure_record(level: str, cells: int, exc: Exception) -> dict[str, object]:
    return {
        "case": f"M1-{level}",
        "status": "FAIL_CLOSED",
        "level": level,
        "cells_x": cells,
        "execution_sha": _git_sha(),
        "contract_sha256": _sha256(CONTRACT),
        "policy_digest": POLICY_DIGEST,
        "element_type": ELEMENT_TYPE,
        "error_type": type(exc).__name__,
        "error": str(exc),
        "m2_allowed": False,
        "m3_allowed": False,
    }


def run_level(level: str, output: Path) -> dict[str, object]:
    level = level.upper()
    if level not in LEVEL_CELLS:
        raise ValueError(f"Unsupported TET10 level {level!r}.")
    cells = LEVEL_CELLS[level]
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("status") != "M1_REQUALIFICATION_AUTHORIZED":
        raise RuntimeError("TET10 surface contract is not frozen for M1 execution.")
    try:
        model, surface_metadata = _model(cells)
        load_metadata = _load_metadata(model)
        result = solve_model(model, enforce_policy=False)
        compact = _compact_result(result, model)
        record: dict[str, object] = {
            "case": f"M1-{level}",
            "status": "PASS_CANDIDATE" if compact["status"] == "PASS" else "FAIL_CLOSED",
            "level": level,
            "cells_x": cells,
            "execution_sha": _git_sha(),
            "runner_sha": contract["runner_sha"],
            "contract_sha256": _sha256(CONTRACT),
            "policy_digest": POLICY_DIGEST,
            "element_type": ELEMENT_TYPE,
            "kinematics": "corotational_j2",
            "contact": "disabled",
            "frozen_inputs": {
                "load_path": list(LOAD_PATH),
                "reference_resultant": REFERENCE_RESULTANT,
                "surface_traction": "consistent_quadratic_TET10_x1_boundary_faces",
                "corotational_max_local_strain": 0.05,
            },
            "surface_load": surface_metadata,
            "load_balance": load_metadata,
            "result": compact,
            "fallback_count": int(cast(int, compact["fallback_count"])),
            "fallback_evidence": "per-step fallback_used field",
        }
    except Exception as exc:  # evidence must remain fail-closed
        record = _failure_record(level, cells, exc)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def independent_reference(primary: Path, output: Path) -> dict[str, object]:
    record = json.loads(primary.read_text(encoding="utf-8"))
    balance = record.get("load_balance", {})
    displacement = np.asarray(record.get("result", {}).get("displacements", []), dtype=float)
    passed = (
        record.get("status") == "PASS_CANDIDATE"
        and bool(displacement.size)
        and bool(np.all(np.isfinite(displacement)))
        and float(balance.get("resultant_error_norm", float("inf"))) <= 1.0e-12
    )
    reference = {
        "status": "PASS_INDEPENDENT_OBSERVABLE_RECOMPUTATION" if passed else "FAIL_CLOSED",
        "source_sha": record.get("execution_sha"),
        "contract_sha256": record.get("contract_sha256"),
        "element_type": ELEMENT_TYPE,
        "independence": "surface-load resultant and finite-displacement recomputation; not an independent global FEM solve",
        "resultant_error_norm": balance.get("resultant_error_norm"),
        "finite_displacements": bool(displacement.size and np.all(np.isfinite(displacement))),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(reference, indent=2), encoding="utf-8")
    return reference


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", choices=tuple(LEVEL_CELLS), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reference", type=Path)
    args = parser.parse_args()
    record = run_level(args.level, args.output)
    if args.reference is not None:
        reference = independent_reference(args.output, args.reference)
        if reference["status"] != "PASS_INDEPENDENT_OBSERVABLE_RECOMPUTATION":
            return 2
    return 0 if record["status"] == "PASS_CANDIDATE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
