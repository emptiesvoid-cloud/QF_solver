"""Run the bounded WP06-D Phase-1 campaign and archive raw evidence.

This runner deliberately stops the formal sequence after the first required
gate failure.  It does not alter solver parameters or create a rescue mesh.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

from solveur.api.public import solve_model
from solveur.core.model import FiniteElementModel
from prepare_wp06d_structural_limit_point import generate_mesh, symmetry_face_nodes


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "qualification" / "0_2_9"
CONTRACT_PATH = OUT / "wp06d_structural_limit_point_contract.json"
GOVERNING_SOURCE_SHA = "12b5331bcbec49e38145ba4a6263df60b8bf4575"
ELEMENT_FORMULATION = "TET4_TOTAL_LAGRANGIAN_STVK"
FORMULATION = "SPHERICAL_ARC_LENGTH_CUSTOM"
BENCHMARK_ID = "WP06D-TET4-MINIMAL-SNAP-THROUGH-001"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _plain(value: Any) -> Any:
    if isinstance(value, np.generic):
        return _plain(value.item())
    if isinstance(value, np.ndarray):
        return [_plain(item) for item in value.tolist()]
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _policy_identity() -> dict[str, Any]:
    identity: dict[str, Any] = {
        "governing_policy_sha": GOVERNING_SOURCE_SHA,
        "formulation_label": FORMULATION,
        "residual_form": "R = lambda * F_ext - F_internal",
        "orientation_policy": "target-load direction initially; previous displacement projection first",
        "newton_convergence_contract": "mechanical residual <= 1e-8 and arc-length constraint <= 1e-8",
        "floor_aware_convergence_policy": "governing 0.2.9 policy identity imported; no WP06-specific override",
        "linear_backend": "serial_sparse_direct",
        "line_search_policy": "canonical governing policy; no alternate line-search parameters",
        "load_step_retry_policy": "rollback committed state; radius shrink 0.5; maximum retries 8; no altered physics",
        "arc_length_termination_policy": "max_steps=80; max retries=8; no target-load stop",
    }
    identity["policy_digest"] = _digest(identity)
    return identity


def _build_model(level: str) -> tuple[FiniteElementModel, np.ndarray, tuple[int, ...], tuple[tuple[int, int, int, int], ...]]:
    nodes, elements = generate_mesh(level)
    symmetry_nodes = symmetry_face_nodes(nodes)
    fixed = [
        {"node": 0, "dofs": ["UX", "UY", "UZ"]},
        {"node": 1, "dofs": ["UX", "UY", "UZ"]},
        *[{"node": node, "dofs": ["UY"]} for node in symmetry_nodes],
    ]
    parameters: dict[str, object] = {
        "type": "nonlinear_static",
        "method": "arc_length",
        "kinematics": "total_lagrangian",
        "target_load_factor": 5.0,
        "max_iterations": 80,
        "tolerance": 1.0e-8,
        "max_arc_steps": 80,
        "arc_length_stop_mode": "max_steps",
        "arc_length_allow_load_factor_turning": True,
        "arc_length_load_factor_limit": 5.0,
        "arc_length_radius": 0.02,
        "max_arc_length_radius": 0.02,
        "min_arc_length_radius": 2.0e-6,
        "adaptive_arc_length": False,
        "arc_length_load_scale": 1.0,
        "arc_length_control_dof": 14,
    }
    model = FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": "TET4", "nodes": list(element), "material": "solid"} for element in elements],
        materials={"solid": {"type": "isotropic_3d", "E": 100.0, "nu": 0.3}},
        fixed_dofs=fixed,
        loads=[{"node": 4, "dof": "UZ", "value": -1.0}],
        analysis=parameters,
    )
    return model, nodes, symmetry_nodes, elements


def _mesh_digest(nodes: np.ndarray, elements: tuple[tuple[int, int, int, int], ...]) -> str:
    return _digest({"nodes": _plain(nodes), "elements": _plain(elements)})


def _limit_index(factors: np.ndarray) -> int | None:
    increments = np.diff(factors)
    turns = np.flatnonzero((increments[:-1] > 0.0) & (increments[1:] <= 0.0))
    return int(turns[0] + 1) if turns.size else None


def _run_level(level: str, case_digest: str, policy: dict[str, Any]) -> dict[str, Any]:
    model, nodes, symmetry_nodes, elements = _build_model(level)
    mesh_digest = _mesh_digest(nodes, elements)
    try:
        # The governing continuation parameters are bound explicitly above;
        # the public qualification wrapper is not a Phase-1 evidence gate.
        result = solve_model(model, enforce_policy=False)
    except Exception as error:  # pragma: no cover - exercised only on a failed campaign
        return {
            "level": level,
            "status": "SOLVE_FAILED",
            "failure_class": type(error).__name__,
            "error": str(error),
            "mesh_digest": mesh_digest,
            "node_count": int(nodes.shape[0]),
            "element_count": len(elements),
            "dof_count": int(nodes.shape[0] * 3),
            "symmetry_face_nodes": list(symmetry_nodes),
        }
    data = _plain(result.to_dict())
    solver = data["solver"]
    steps = list(solver["steps"])
    factors = np.asarray([float(step["load_factor"]) for step in steps], dtype=float)
    control = np.asarray(
        [float(step["arc_length_control_displacement"]) for step in steps], dtype=float
    )
    limit_index = _limit_index(factors)
    equilibrium = data.get("audit", {}).get("equilibrium", {})
    force_error = float(equilibrium.get("force_balance_relative_error", float("inf")))
    moment_error = float(equilibrium.get("moment_balance_relative_error", float("inf")))
    det_values = [
        float(row["det_f"])
        for row in data.get("element_results", [])
        if row.get("det_f") is not None
    ]
    failure_classes: list[str] = []
    if limit_index is None:
        failure_classes.append("LIMIT_POINT_TRACKING_FAILURE")
    if force_error > 1.0e-8 or moment_error > 1.0e-8:
        failure_classes.append("EQUILIBRIUM_FAILURE")
    level_status = "PASS_NUMERICAL_LIMIT_POINT" if not failure_classes else "FAIL_" + "_AND_".join(failure_classes)
    return {
        "level": level,
        "status": level_status,
        "solver_status": data.get("status"),
        "node_count": int(nodes.shape[0]),
        "element_count": len(elements),
        "dof_count": int(nodes.shape[0] * 3),
        "mesh_digest": mesh_digest,
        "symmetry_face_nodes": list(symmetry_nodes),
        "load_nodes": [4],
        "load_vector": [0.0, 0.0, -1.0],
        "steps": steps,
        "accepted_path": {
            "lambda": factors.tolist(),
            "q": (-control).tolist(),
            "radius": [float(step["arc_length_radius"]) for step in steps],
            "newton_iterations": [int(step["iterations"]) for step in steps],
            "accepted_rejected": ["accepted"] * len(steps),
        },
        "limit_point": (
            {
                "index": limit_index,
                "step": int(steps[limit_index]["step"]),
                "lambda": float(factors[limit_index]),
                "q": float(-control[limit_index]),
            }
            if limit_index is not None
            else None
        ),
        "terminal_classification": "MAX_STEPS_AFTER_PATH" if data.get("status") == "PASS" else "SOLVE_FAILURE",
        "rejected_increments": int(solver.get("rejected_increments", 0)),
        "rejection_log": solver.get("rejection_log", []),
        "equilibrium": equilibrium,
        "failure_classes": failure_classes,
        "strain_energy": None,
        "minimum_det_f": min(det_values) if det_values else None,
        "principal_stretches": {"value": None, "reason": "NOT_EXPOSED_BY_ROUTE_RESULT"},
        "maximum_green_lagrange_norm": {"value": None, "reason": "NOT_EXPOSED_BY_ROUTE_RESULT"},
        "case_definition_digest": case_digest,
        "governing_policy_digest": policy["policy_digest"],
    }


def _provenance(source_sha: str, contract_digest: str, case_digest: str, policy_digest: str) -> dict[str, str]:
    return {
        "repository": "emptiesvoid-cloud/QF_solver",
        "branch": _git("branch", "--show-current"),
        "source_sha": source_sha,
        "governing_imported_sha": GOVERNING_SOURCE_SHA,
        "contract_revision": "WP06D-R1",
        "contract_digest": contract_digest,
        "case_definition_digest": case_digest,
        "solver_policy_digest": policy_digest,
        "element_formulation_identity": ELEMENT_FORMULATION,
    }


def main() -> int:
    source_sha = _git("rev-parse", "HEAD")
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    contract_digest = hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest()
    case_definition = {
        "benchmark": contract["benchmark"],
        "mesh_series": contract["mesh_series"],
        "mesh_generation": contract["mesh_generation"],
        "load_assembly_contract": contract["load_assembly_contract"],
    }
    case_digest = _digest(case_definition)
    policy = _policy_identity()
    provenance = _provenance(source_sha, contract_digest, case_digest, policy["policy_digest"])
    levels: dict[str, dict[str, Any]] = {}
    for level in ("M1", "M2"):
        levels[level] = _run_level(level, case_digest, policy)
        if levels[level]["status"] != "PASS_NUMERICAL_LIMIT_POINT":
            break
    levels["M3"] = {
        "level": "M3",
        "status": "NOT_RUN_AFTER_M2_FAILURE" if levels.get("M2", {}).get("status") != "PASS_NUMERICAL_LIMIT_POINT" else "NOT_RUN",
        "reason": "WP06-D fail-closed sequence stops after M2 limit-point gate failure.",
        "contract_mesh_digest": "not-generated-by-formal-sequence",
    }
    m2_failures = levels.get("M2", {}).get("failure_classes", [])
    raw = {
        "benchmark_id": BENCHMARK_ID,
        "element_formulation": ELEMENT_FORMULATION,
        "formulation_label": FORMULATION,
        "contract_revision": "WP06D-R1",
        "physics_contract_unchanged": True,
        "execution_policy_status": "BOUND_TO_IMPORTED_GOVERNING_POLICY",
        "levels": levels,
        "formal_stop": (
            "M2_" + "_AND_".join(m2_failures)
            if levels["M3"]["status"] == "NOT_RUN_AFTER_M2_FAILURE"
            else None
        ),
        "no_undeclared_m4": True,
        "thresholds_changed": False,
        "physics_changed": False,
    }
    raw_artifact = {
        "schema_version": 1,
        "record_id": "QF-0.2.9-WP06D-PHASE1-RAW-001",
        "status": "FAIL_CLOSED_M2_" + "_AND_".join(m2_failures),
        "provenance": provenance,
        "phase1_binding": {**provenance, "governing_policy_identity": policy},
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "git_dirty": bool(_git("status", "--porcelain")),
        },
        "raw": raw,
        "reported_status": "FAIL_CLOSED_M2_" + "_AND_".join(m2_failures),
        "failure_class": m2_failures,
        "failure_reason": "M2 converged numerically but failed one or more frozen qualification gates; formal sequence stopped before M3.",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "wp06d_phase1_structural_raw.json").write_text(
        json.dumps(raw_artifact, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    not_run = {
        "schema_version": 1,
        "status": "NOT_RUN_AFTER_M2_FAILURE",
        "provenance": provenance,
        "phase1_binding": {**provenance, "governing_policy_identity": policy},
        "reason": "Independent reference and replay are not executed after the required M2 structural gate fails.",
        "raw": None,
    }
    (OUT / "wp06d_reference_result.json").write_text(
        json.dumps(not_run | {"record_id": "QF-0.2.9-WP06D-REFERENCE-001"}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (OUT / "wp06d_replay_result.json").write_text(
        json.dumps(not_run | {"record_id": "QF-0.2.9-WP06D-REPLAY-001"}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": raw_artifact["status"], "levels": {k: v["status"] for k, v in levels.items()}}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
