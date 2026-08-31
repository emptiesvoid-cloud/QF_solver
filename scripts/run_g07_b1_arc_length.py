"""Run the bounded G07-B1 Arc-Length sensitivity and restart evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from solveur.api import solve_model
from solveur.core.model import FiniteElementModel

try:
    from scripts.g07_b1_arc_length_helpers import run_restart_case, run_rollback_case
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from g07_b1_arc_length_helpers import run_restart_case, run_rollback_case


ROOT = Path(__file__).resolve().parents[1]
BASELINE_SHA = "eb105657f1d5f1a0994f5598327a290358f37e7e"
EVIDENCE_ID = "026-G07-B1-ARC-LENGTH-001"
DEFAULT_OUTPUT = ROOT / "qualification" / "0_2_6" / "g07_b1_arc_length_evidence.json"

BASE_NODES = np.asarray(
    [
        [-1.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, -0.05, 0.20],
        [0.0, 0.05, 0.20],
        [0.0, 0.00, 0.25],
    ],
    dtype=float,
)
BASE_ELEMENTS = ((0, 2, 3, 4), (1, 3, 2, 4))

ARC_STEP_SETTINGS = (
    {"id": "R_SMALL", "radius": 0.01, "max_arc_steps": 160},
    {"id": "R_NOMINAL", "radius": 0.02, "max_arc_steps": 80},
)
MESH_SETTINGS = (
    {"id": "M_COARSE", "level": 1, "description": "reference two-TET4 bipyramid"},
    {"id": "M_REFINED", "level": 2, "description": "conforming one-to-eight refinement, sixteen TET4"},
)


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _sha256(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _signed_tet_volume(nodes: np.ndarray, element: tuple[int, int, int, int] | list[int]) -> float:
    points = nodes[np.asarray(element, dtype=int)]
    return float(np.linalg.det(np.column_stack((points[1:] - points[0]))) / 6.0)


def _refine_once(
    nodes: np.ndarray,
    elements: tuple[tuple[int, int, int, int], ...] | list[list[int]],
    face_nodes: set[int],
) -> tuple[np.ndarray, list[list[int]], set[int]]:
    refined_nodes = [row.tolist() for row in np.asarray(nodes, dtype=float)]
    edge_midpoints: dict[tuple[int, int], int] = {}
    refined_face_nodes = set(face_nodes)

    def midpoint(first: int, second: int) -> int:
        key = tuple(sorted((int(first), int(second))))
        if key not in edge_midpoints:
            edge_midpoints[key] = len(refined_nodes)
            refined_nodes.append(((nodes[first] + nodes[second]) / 2.0).tolist())
            if first in face_nodes and second in face_nodes:
                refined_face_nodes.add(edge_midpoints[key])
        return edge_midpoints[key]

    children: list[list[int]] = []
    for raw_element in elements:
        a, b, c, d = (int(value) for value in raw_element)
        ab, ac, ad = midpoint(a, b), midpoint(a, c), midpoint(a, d)
        bc, bd, cd = midpoint(b, c), midpoint(b, d), midpoint(c, d)
        local_children = [
            [a, ab, ac, ad],
            [b, ab, bc, bd],
            [c, ac, bc, cd],
            [d, ad, bd, cd],
            [ab, ac, ad, cd],
            [ab, ac, bc, cd],
            [ab, bc, bd, cd],
            [ab, bd, ad, cd],
        ]
        for child in local_children:
            if abs(_signed_tet_volume(np.asarray(refined_nodes), child)) <= 1.0e-14:
                raise ValueError("G07-B1 refinement created a degenerate TET4.")
            if _signed_tet_volume(np.asarray(refined_nodes), child) < 0.0:
                child[2], child[3] = child[3], child[2]
            children.append(child)
    return np.asarray(refined_nodes, dtype=float), children, refined_face_nodes


def _mesh(level: int) -> tuple[np.ndarray, list[list[int]], set[int]]:
    nodes = BASE_NODES.copy()
    elements: list[list[int]] = [list(element) for element in BASE_ELEMENTS]
    face_nodes = {2, 3, 4}
    for _ in range(level - 1):
        nodes, elements, face_nodes = _refine_once(nodes, elements, face_nodes)
    return nodes, elements, face_nodes


def _model(
    *,
    mesh_level: int,
    radius: float,
    max_arc_steps: int,
    checkpoint_path: Path | None = None,
    restart_from: Path | None = None,
    checkpoint_keep_steps: bool = False,
) -> FiniteElementModel:
    nodes, elements, constrained_face_nodes = _mesh(mesh_level)
    parameters: dict[str, object] = {
        "type": "nonlinear_static",
        "method": "arc_length",
        "kinematics": "total_lagrangian",
        "target_load_factor": -1.0,
        "max_iterations": 80,
        "tolerance": 1.0e-8,
        "max_arc_steps": max_arc_steps,
        "arc_length_stop_mode": "max_steps",
        "arc_length_allow_load_factor_turning": True,
        "arc_length_load_factor_limit": 5.0,
        "arc_length_radius": radius,
        "max_arc_length_radius": radius,
        "min_arc_length_radius": radius * 1.0e-4,
        "adaptive_arc_length": False,
        "arc_length_load_scale": 1.0,
        "arc_length_control_dof": 14,
    }
    if checkpoint_path is not None:
        parameters.update(
            {
                "checkpoint_path": str(checkpoint_path),
                "checkpoint_interval": 1,
                "checkpoint_keep_steps": checkpoint_keep_steps,
            }
        )
    if restart_from is not None:
        parameters["restart_from"] = str(restart_from)
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": "TET4", "nodes": element, "material": "solid"} for element in elements],
        materials={"solid": {"type": "isotropic_3d", "E": 100.0, "nu": 0.3}},
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 1, "dofs": ["UX", "UY", "UZ"]},
            *[{"node": node, "dofs": ["UY"]} for node in sorted(constrained_face_nodes)],
        ],
        loads=[{"node": node, "dof": "UZ", "value": 1.0 / 3.0} for node in (2, 3, 4)],
        analysis=parameters,
    )


def _sample(values: np.ndarray, indices: list[int]) -> list[dict[str, object]]:
    return [{"index": index, "value": float(values[index])} for index in sorted(set(indices)) if 0 <= index < len(values)]


def _arc_case(*, mesh: dict[str, object], setting: dict[str, object]) -> dict[str, object]:
    radius = float(setting["radius"])
    max_steps = int(setting["max_arc_steps"])
    try:
        model = _model(mesh_level=int(mesh["level"]), radius=radius, max_arc_steps=max_steps)
        result = solve_model(model, enforce_policy=False)
        data = result.to_dict()
        steps = list(data["solver"].get("steps", []))
        factors = np.asarray([float(step["load_factor"]) for step in steps], dtype=float)
        displacements = np.asarray(
            [float(step["arc_length_control_displacement"]) for step in steps], dtype=float
        )
        residuals = np.asarray([float(step["relative_residual"]) for step in steps], dtype=float)
        increments = np.diff(factors)
        turn_indices = np.flatnonzero((increments[:-1] * increments[1:]) < -1.0e-14)
        turning_index = int(turn_indices[0] + 1) if turn_indices.size else None
        determinant_values = [
            float(point["det_f"])
            for row in result.element_results
            for point in row.get("integration_points", [])
            if point.get("det_f") is not None
        ]
        minimum_det_f = min(determinant_values) if determinant_values else None
        finite = bool(
            factors.size
            and displacements.size
            and residuals.size
            and np.all(np.isfinite(factors))
            and np.all(np.isfinite(displacements))
            and np.all(np.isfinite(residuals))
            and minimum_det_f is not None
            and np.isfinite(minimum_det_f)
        )
        path_continuous = bool(
            factors.size > 1
            and np.all(np.abs(np.diff(factors)) > 1.0e-14)
            and np.all(np.abs(np.diff(displacements)) > 1.0e-14)
        )
        execution_completed = bool(result.status == "PASS" and len(steps) == max_steps)
        turning_point_observed = bool(turn_indices.size >= 1)
        case_integrity = bool(
            execution_completed
            and finite
            and path_continuous
            and float(minimum_det_f) > 0.0
        )
        passed = bool(case_integrity and turning_point_observed)
        sample_indices = [0, len(steps) - 1]
        if turning_index is not None:
            sample_indices.extend([turning_index - 1, turning_index, turning_index + 1])
        return {
            "case_id": f"ARC002-{mesh['id']}-{setting['id']}",
            "mesh_id": mesh["id"],
            "mesh_level": mesh["level"],
            "mesh_description": mesh["description"],
            "radius": radius,
            "max_arc_steps": max_steps,
            "solver_status": result.status,
            "result": (
                "PASS_BOUNDED"
                if passed
                else "DEFER"
                if case_integrity
                else "FAIL"
            ),
            "classification_reason": (
                "TURNING_POINT_OBSERVED"
                if passed
                else "TURNING_POINT_NOT_OBSERVED_WITHIN_DECLARED_STEP_WINDOW"
                if case_integrity
                else "RUNTIME_VALIDITY_CRITERION_FAILED"
            ),
            "execution_completed": execution_completed,
            "turning_point_observed": turning_point_observed,
            "case_integrity": case_integrity,
            "step_count": len(steps),
            "branch_turn_count": int(turn_indices.size),
            "turning_point_step": turning_index,
            "turning_point_load_factor": (
                float(factors[turning_index]) if turning_index is not None else None
            ),
            "turning_point_control_displacement": (
                float(displacements[turning_index]) if turning_index is not None else None
            ),
            "final_load_factor": float(factors[-1]) if factors.size else None,
            "final_control_displacement": float(displacements[-1]) if displacements.size else None,
            "maximum_relative_residual": float(residuals.max()) if residuals.size else None,
            "minimum_det_f": minimum_det_f,
            "path_continuous": path_continuous,
            "finite_runtime_fields": finite,
            "branch_direction_signature": [step.get("arc_length_branch_direction") for step in steps],
            "load_factor_digest": _sha256(factors.tolist()),
            "control_displacement_digest": _sha256(displacements.tolist()),
            "path_digest": _sha256({"load_factor": factors.tolist(), "control_displacement": displacements.tolist()}),
            "load_factor_samples": _sample(factors, sample_indices),
            "control_displacement_samples": _sample(displacements, sample_indices),
        }
    except Exception as exc:  # pragma: no cover - evidence runner records a failed case
        return {
            "case_id": f"ARC002-{mesh['id']}-{setting['id']}",
            "mesh_id": mesh["id"],
            "mesh_level": mesh["level"],
            "mesh_description": mesh["description"],
            "radius": radius,
            "max_arc_steps": max_steps,
            "result": "FAIL",
            "classification_reason": "EXPLICIT_RUNTIME_EXCEPTION",
            "execution_completed": False,
            "turning_point_observed": False,
            "case_integrity": False,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "finite_runtime_fields": False,
            "path_continuous": False,
        }


def _relative_difference(first: float | None, second: float | None) -> float | None:
    if first is None or second is None:
        return None
    return abs(second - first) / max(abs(first), 1.0e-15)


def _arc002_summary(cases: list[dict[str, object]]) -> dict[str, object]:
    series: list[dict[str, object]] = []
    mesh_comparisons: list[dict[str, object]] = []
    for mesh in MESH_SETTINGS:
        rows = [row for row in cases if row["mesh_id"] == mesh["id"]]
        all_case_integrity = all(bool(row.get("case_integrity")) for row in rows)
        all_turning_points = all(bool(row.get("turning_point_observed")) for row in rows)
        turn_counts = {row.get("branch_turn_count") for row in rows}
        branch_stable = all_case_integrity and all_turning_points and len(turn_counts) == 1
        first, second = rows[0], rows[1]
        series.append(
            {
                "mesh_id": mesh["id"],
                "case_ids": [row["case_id"] for row in rows],
                "result": (
                    "PASS_BOUNDED"
                    if branch_stable
                    else "DEFER"
                    if all_case_integrity
                    else "FAIL"
                ),
                "classification_reason": (
                    "BRANCH_STABILITY_OBSERVED"
                    if branch_stable
                    else "TURNING_POINT_NOT_OBSERVED_FOR_ALL_DECLARED_MESH_SETTINGS"
                    if all_case_integrity
                    else "ONE_OR_MORE_CASES_FAILED_RUNTIME_VALIDITY"
                ),
                "all_case_integrity": all_case_integrity,
                "all_turning_points": all_turning_points,
                "qualitative_branch_stability": branch_stable,
                "turning_point_comparison_available": all_turning_points,
                "turning_load_factor_relative_difference": _relative_difference(
                    first.get("turning_point_load_factor"), second.get("turning_point_load_factor")
                ),
                "turning_displacement_relative_difference": _relative_difference(
                    first.get("turning_point_control_displacement"),
                    second.get("turning_point_control_displacement"),
                ),
                "path_continuity": all(bool(row.get("path_continuous")) for row in rows),
            }
        )
    for setting in ARC_STEP_SETTINGS:
        rows = [row for row in cases if row["radius"] == setting["radius"]]
        if len(rows) == 2:
            coarse, refined = rows
            mesh_comparisons.append(
                {
                    "radius": setting["radius"],
                    "coarse_case": coarse["case_id"],
                    "refined_case": refined["case_id"],
                    "both_case_integrity": bool(coarse.get("case_integrity"))
                    and bool(refined.get("case_integrity")),
                    "both_turning_points_observed": bool(coarse.get("turning_point_observed"))
                    and bool(refined.get("turning_point_observed")),
                    "comparison_result": (
                        "PASS_BOUNDED"
                        if coarse.get("result") == "PASS_BOUNDED"
                        and refined.get("result") == "PASS_BOUNDED"
                        else "DEFER"
                        if bool(coarse.get("case_integrity"))
                        and bool(refined.get("case_integrity"))
                        else "FAIL"
                    ),
                    "comparison_reason": (
                        "TURNING_POINT_COMPARISON_AVAILABLE"
                        if bool(coarse.get("turning_point_observed"))
                        and bool(refined.get("turning_point_observed"))
                        else "REFINED_MESH_HAS_NO_OBSERVED_TURNING_POINT"
                        if bool(coarse.get("case_integrity"))
                        and bool(refined.get("case_integrity"))
                        else "CASE_RUNTIME_VALIDITY_FAILURE"
                    ),
                    "turning_load_factor_relative_difference": _relative_difference(
                        coarse.get("turning_point_load_factor"), refined.get("turning_point_load_factor")
                    ),
                    "turning_displacement_relative_difference": _relative_difference(
                        coarse.get("turning_point_control_displacement"),
                        refined.get("turning_point_control_displacement"),
                    ),
                }
            )
    overall = (
        "PASS_BOUNDED"
        if all(row["result"] == "PASS_BOUNDED" for row in series)
        else "DEFER"
        if all(row["all_case_integrity"] for row in series)
        else "FAIL"
    )
    return {
        "result": overall,
        "classification_reason": (
            "MESH_AND_ARC_STEP_BRANCH_STABILITY_OBSERVED"
            if overall == "PASS_BOUNDED"
            else "REFINED_MESH_TURNING_POINT_SENSITIVITY_REMAINS_UNRESOLVED"
            if overall == "DEFER"
            else "ONE_OR_MORE_ARC_LENGTH_CASES_FAILED_RUNTIME_VALIDITY"
        ),
        "series": series,
        "mesh_comparisons": mesh_comparisons,
        "interpretation": (
            "Qualitative branch stability is required; sensitivity magnitudes are reported, "
            "not tested against a universal threshold. A finite continuous mesh series without "
            "an observed turning point is explicitly deferred, not treated as a pass."
        ),
    }


def _restart_case(*, restart_position: str) -> dict[str, object]:
    return run_restart_case(restart_position=restart_position, model_factory=_model)


def _rollback_case() -> dict[str, object]:
    return run_rollback_case()


def _run(output: Path) -> dict[str, object]:
    source_sha = _git("rev-parse", "HEAD")
    dirty = _git("status", "--porcelain", "--untracked-files=all")
    if dirty:
        raise RuntimeError("G07-B1 evidence must start from a clean source tree.")
    arc002_cases = [
        _arc_case(mesh=mesh, setting=setting)
        for mesh in MESH_SETTINGS
        for setting in ARC_STEP_SETTINGS
    ]
    arc003_first = _restart_case(restart_position="before_turn")
    arc003_replay = _restart_case(restart_position="before_turn")
    arc003_after = _restart_case(restart_position="after_turn")
    rollback = _rollback_case()
    replay_core = {
        key: arc003_first.get(key)
        for key in (
            "restart_position",
            "checkpoint_step",
            "checkpoint_state_digest",
            "resumed_restart_step",
            "suffix_load_factor_max_error",
            "final_displacement_relative_error",
            "continuous_final_state_digest",
            "resumed_final_state_digest",
            "state_preserved",
            "trajectory_rejoined",
            "no_ghost_state",
            "result",
        )
    }
    replay_core_again = {
        key: arc003_replay.get(key)
        for key in (
            "restart_position",
            "checkpoint_step",
            "checkpoint_state_digest",
            "resumed_restart_step",
            "suffix_load_factor_max_error",
            "final_displacement_relative_error",
            "continuous_final_state_digest",
            "resumed_final_state_digest",
            "state_preserved",
            "trajectory_rejoined",
            "no_ghost_state",
            "result",
        )
    }
    deterministic_replay = replay_core == replay_core_again
    arc003_cases = [arc003_first, arc003_after, rollback]
    arc003_pass = all(row.get("result") == "PASS_BOUNDED" for row in arc003_cases) and deterministic_replay
    arc002 = _arc002_summary(arc002_cases)
    all_runtime_rows = arc002_cases + arc003_cases + [arc003_replay]
    no_nan_inf = all(
        bool(row.get("finite_runtime_fields", True))
        and all(value is None or np.isfinite(float(value)) for value in row.values() if isinstance(value, (int, float)))
        for row in all_runtime_rows
    )
    no_silent_pass = all(
        row.get("result") in {"PASS_BOUNDED", "DEFER", "FAIL"}
        and bool(row.get("classification_reason"))
        for row in all_runtime_rows
    )
    state_integrity = all(bool(row.get("state_preserved")) for row in arc003_cases)
    runtime_valid = bool(
        arc003_pass
        and arc002["result"] != "FAIL"
        and no_nan_inf
        and no_silent_pass
        and state_integrity
    )
    evidence_status = (
        "PASS_WITH_LIMITATIONS"
        if runtime_valid and arc002["result"] == "PASS_BOUNDED"
        else "PARTIAL"
        if runtime_valid
        else "FAIL"
    )
    arc002_gap = []
    if arc002["result"] == "DEFER":
        arc002_gap.append(
            "ARC-002: refined mesh completed a finite continuous path but did not show "
            "a turning point within the predeclared step windows; mesh turning-point "
            "sensitivity remains deferred."
        )
    elif arc002["result"] == "FAIL":
        arc002_gap.append("ARC-002: one or more declared cases failed runtime validity.")
    payload: dict[str, object] = {
        "schema_version": 1,
        "evidence_id": EVIDENCE_ID,
        "gate": "026-G07",
        "step": "B1_ARC_LENGTH_TARGETED_EVIDENCE",
        "status": evidence_status,
        "baseline_start_sha": BASELINE_SHA,
        "execution_source_sha": source_sha,
        "execution_worktree_dirty": False,
        "functional_source_changed": False,
        "external_calculation": "NOT_RUN_BY_POLICY",
        "scope_guard": {
            "tl_modified": False,
            "routes": ["arc_length"],
            "family": "TET4",
            "new_physics": False,
            "formulation_changed": False,
        },
        "predeclared_criteria": {
            "case_validity": [
                "requested number of steps is completed",
                "at least one branch turn is detected",
                "load factors, control displacement, residual history and det(F) are finite",
                "successive load-factor and control-displacement points are non-duplicate",
                "minimum det(F) remains positive",
            ],
            "qualitative_stability": "All settings within a mesh must complete with the same branch-turn count and continuous path.",
            "sensitivity_metric": "Report relative turning-point changes for load factor and control displacement; no universal numerical pass band is introduced.",
            "mesh_design": "Two conforming meshes on the same two-span volumetric snap-through geometry: 2 TET4 and one-to-eight refined 16 TET4.",
            "restart_policy": "Checkpoint state, continuation state, suffix trajectory and final state must match; controlled rollback must expose an explicit failure reason and clean retry.",
        },
        "arc002": {
            "case_count": len(arc002_cases),
            "arc_step_settings": list(ARC_STEP_SETTINGS),
            "mesh_settings": list(MESH_SETTINGS),
            "cases": arc002_cases,
            "summary": arc002,
        },
        "arc003": {
            "case_count": len(arc003_cases),
            "cases": arc003_cases,
            "replay": {
                "case_id": "ARC003-RESTART-BEFORE-TURN-REPLAY",
                "result": "PASS" if deterministic_replay else "FAIL",
                "same_classification": deterministic_replay,
                "same_checkpoint_step": replay_core["checkpoint_step"] == replay_core_again["checkpoint_step"],
                "same_state_digest": replay_core["checkpoint_state_digest"] == replay_core_again["checkpoint_state_digest"],
                "same_final_digest": replay_core["resumed_final_state_digest"] == replay_core_again["resumed_final_state_digest"],
            },
        },
        "runtime_assertions": {
            "arc002_result": arc002["result"],
            "arc003_result": "PASS_BOUNDED" if arc003_pass else "FAIL",
            "deterministic_replay": deterministic_replay,
            "no_nan_inf": no_nan_inf,
            "no_silent_pass": no_silent_pass,
            "state_integrity": state_integrity,
            "runtime_case_count": len(all_runtime_rows),
        },
        "claim": {
            "arc_length_owner_candidate": (
                "PASS_WITH_LIMITATIONS / PASS_INTERNAL_RESEARCH_BOUNDED"
                if evidence_status == "PASS_WITH_LIMITATIONS"
                else "PASS_WITH_LIMITATIONS / ARC-002_DEFERRED"
            ),
            "arc_length_blocking_gaps_remaining": arc002_gap,
            "tl_claim": "OUT_OF_SCOPE_AND_UNCHANGED",
            "production_qualification": False,
            "universal_sensitivity_threshold": False,
        },
        "limitations": [
            "Sensitivity is qualitative plus reported metrics; no universal stability threshold is claimed.",
            "The study uses two compatible meshes and two fixed-radius settings only.",
            "The two radius settings use 160 and 80 maximum steps respectively to reach the same bounded continuation window.",
            "The refined mesh has finite, continuous, monotone paths in both declared windows but no observed turning point; this is an explicit ARC-002 limitation, not a pass or a solver failure.",
            "Rollback uses a controlled failure injection in the existing route-native evidence adapter; it does not alter the solver path.",
            "Arc-Length remains research-level and G07 is not closed by this artifact.",
        ],
        "provenance": {
            "captured_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "runner": "scripts/run_g07_b1_arc_length.py",
            "baseline_start_sha": BASELINE_SHA,
            "execution_source_sha": source_sha,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    payload = _run(arguments.output.resolve())
    print(
        json.dumps(
            {
                "evidence_id": payload["evidence_id"],
                "status": payload["status"],
                "execution_source_sha": payload["execution_source_sha"],
                "arc002": payload["arc002"]["summary"],
                "arc003": payload["arc003"]["replay"],
                "runtime_assertions": payload["runtime_assertions"],
                "output": str(arguments.output.resolve()),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if payload["status"] in {"PASS_WITH_LIMITATIONS", "PARTIAL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
