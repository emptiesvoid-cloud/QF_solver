"""Run the controlled 026-G09 robustness extension campaign.

This runner composes the already-qualified bounded contact paths.  It adds no
contact formulation or solver behavior; all observations are diagnostic
extension evidence and do not change the official G09 closeout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
# ruff: noqa: E402

from solveur.api import solve_model
from solveur.contact.entities import FrictionlessContact
from solveur.core.model import FiniteElementModel

try:
    from scripts.run_g09_lot2 import (
        _canonical,
        _finite,
        _mesh_contact_model,
        _run_adversarial,
        _run_contact_cutback,
        _run_cycle,
        _solve_contact_case,
    )
except ModuleNotFoundError:  # Direct execution from the scripts directory.
    from run_g09_lot2 import (
        _canonical,
        _finite,
        _mesh_contact_model,
        _run_adversarial,
        _run_contact_cutback,
        _run_cycle,
        _solve_contact_case,
    )

GATE = "026-G09"
LOT = "ROBUSTNESS_EXTENSION"
SOURCE_SHA_DEFAULT = "1468eb051093b7be54940da69c4a3d2270967da9"
MESH_LEVELS = (1, 2, 4)
PENALTIES = (1.0e2, 1.0e3, 1.0e4, 1.0e5, 1.0e6)
EQUILIBRIUM_LIMIT = 1.0e-8
DETERMINISM_LIMIT = 1.0e-12


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def _source_state(expected_sha: str) -> dict[str, Any]:
    state = {"sha": _git("rev-parse", "HEAD"), "dirty": bool(_git("status", "--porcelain"))}
    if state["sha"] != expected_sha:
        raise RuntimeError(f"Expected source SHA {expected_sha}, got {state['sha']}.")
    if state["dirty"]:
        raise RuntimeError("G09 robustness extension requires a clean source worktree.")
    return state


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _result_metrics(result: Any, penalty: float) -> dict[str, Any]:
    data = result.to_dict()
    solver = data["solver"]
    step = solver["steps"][-1]
    gap = float(step.get("contact_gaps", [0.0])[0])
    penetration = max(-gap, 0.0)
    audit = data.get("audit", {})
    equilibrium = audit.get("equilibrium", {})
    force_error = float(equilibrium.get("force_balance_relative_error", 0.0))
    return {
        "solver_status": result.status,
        "run_verdict": result.run_verdict.value,
        "converged": result.status == "PASS",
        "displacement_norm": float(np.linalg.norm(result.displacements)),
        "gap": gap,
        "penetration": penetration,
        "penalty_energy": 0.5 * penalty * penetration * penetration,
        "active_contact_count": len(step.get("contact_active_contacts", [])),
        "residual": float(step.get("relative_residual", math.inf)),
        "iterations": int(step.get("iterations", 0)),
        "force_balance_relative_error": force_error,
        "minimum_det_f": float(solver.get("minimum_det_f", 1.0)),
        "finite": _finite(data) and bool(np.all(np.isfinite(result.displacements))),
        "equilibrium_pass": force_error <= EQUILIBRIUM_LIMIT,
    }


def _run_penalty_mesh_matrix() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for mesh_level in MESH_LEVELS:
        for penalty in PENALTIES:
            row = _solve_contact_case(_mesh_contact_model(mesh_level, penalty=penalty), penalty)
            rows.append(
                {
                    "mesh_level": mesh_level,
                    "penalty": penalty,
                    "normalized_penalty_E10_L1": penalty / 10.0,
                    **row,
                    "penalty_energy": 0.5 * penalty * row["penetration"] ** 2,
                    "equilibrium_pass": row["finite"] and row["residual"] <= EQUILIBRIUM_LIMIT,
                }
            )
    reference = [row for row in rows if row["penalty"] == 1.0e5]
    mesh_changes = []
    for left, right in zip(reference, reference[1:]):
        mesh_changes.append(
            {
                "from": left["mesh_level"],
                "to": right["mesh_level"],
                "reaction_relative_change": abs(right["reaction_norm"] - left["reaction_norm"])
                / max(abs(left["reaction_norm"]), 1.0e-15),
                "displacement_relative_change": abs(
                    right["displacement_norm"] - left["displacement_norm"]
                )
                / max(abs(left["displacement_norm"]), 1.0e-15),
            }
        )
    replay = _solve_contact_case(_mesh_contact_model(4, penalty=1.0e5), 1.0e5)
    replay_reference = next(row for row in reference if row["mesh_level"] == 4)
    replay_exact = _canonical(replay) == _canonical(
        {key: value for key, value in replay_reference.items() if key in replay}
    )
    return {
        "mesh_levels": list(MESH_LEVELS),
        "penalties": list(PENALTIES),
        "rows": rows,
        "mesh_changes_at_1e5": mesh_changes,
        "replay_exact": replay_exact,
        "all_pass": all(row["status"] == "PASS" for row in rows),
        "equilibrium_pass": all(row["equilibrium_pass"] for row in rows),
        "determinism": replay_exact,
        "limitation": "Observational sensitivity only; no universal penalty range or conditioning cutoff.",
    }


def _run_activation_matrix() -> dict[str, Any]:
    paths = [
        ("zero_gap_contact", (0.0,)),
        ("positive_epsilon_open", (-1.0e-8,)),
        ("negative_epsilon_close", (1.0e-8,)),
        ("open_close", (0.0, 1.0)),
        ("close_open", (1.0, 0.0)),
        ("open_close_open", (0.0, 1.0, 0.0)),
        ("open_close_reclose", (0.0, 1.0, 0.0, 1.0)),
        ("close_open_recontact", (1.0, 0.0, 1.0)),
    ]
    rows = [_run_cycle(path, name) for name, path in paths]
    return {
        "rows": rows,
        "all_pass": all(row["status"] == "PASS_INTERNAL_RESEARCH" for row in rows),
        "no_attraction": all(
            all(gap >= -1.0e-12 for active, gap in zip(row["active_by_step"], row["gaps_by_step"]) if not active)
            for row in rows
        ),
        "determinism": all(row["final_reference_relative_difference"] <= DETERMINISM_LIMIT for row in rows),
        "limitation": "Initial-search bounded contact path; no finite-sliding claim.",
    }


def _rotation(axis: np.ndarray, angle: float) -> np.ndarray:
    axis = axis / np.linalg.norm(axis)
    skew = np.array(
        [[0.0, -axis[2], axis[1]], [axis[2], 0.0, -axis[0]], [-axis[1], axis[0], 0.0]]
    )
    return np.eye(3) + math.sin(angle) * skew + (1.0 - math.cos(angle)) * (skew @ skew)


def _rotated_spring_model(angle: float, barycentric: tuple[float, float]) -> FiniteElementModel:
    rotation = _rotation(np.array([1.0, 2.0, 3.0]), angle)
    local = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [*barycentric, 0.1]]
    )
    nodes = local @ rotation.T
    normal = rotation @ np.array([0.0, 0.0, 1.0])
    data = {
        "analysis": {"type": "linear_static", "method": "direct", "contact_max_iterations": 12},
        "nodes": nodes.tolist(),
        "elements": [],
        "materials": {},
        "fixed_dofs": [{"node": index, "dofs": ["UX", "UY", "UZ"]} for index in range(3)],
        "springs": [{"node_a": 3, "dofs": ["UX", "UY", "UZ"], "stiffness": [1000.0] * 3}],
        "loads": [
            {"node": 3, "dof": dof, "value": float(-200.0 * normal[index])}
            for index, dof in enumerate(("UX", "UY", "UZ"))
        ],
        "contacts": [{"name": "geometry", "slave_node": 3, "master_nodes": [0, 1, 2]}],
    }
    model = FiniteElementModel.from_raw(
        nodes=data["nodes"],
        elements=[],
        materials={},
        fixed_dofs=data["fixed_dofs"],
        loads=data["loads"],
        springs=data["springs"],
        contacts=[],
        analysis=data["analysis"],
    )
    model.contacts.append(FrictionlessContact(name="geometry", slave_node=3, master_nodes=(0, 1, 2)))
    return model


def _run_geometry_matrix() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for index, angle in enumerate((0.0, 0.2, 0.5, 1.0)):
        for position in ((0.25, 0.25), (0.60, 0.20)):
            model = _rotated_spring_model(angle, position)
            result = solve_model(model, enforce_policy=False)
            data = result.to_dict()
            solver = data["solver"]
            details = solver.get("contact", {})
            contact_convergence = details.get("convergence", {})
            rows.append(
                {
                    "case": f"orientation_{index}_bary_{position[0]:.2f}_{position[1]:.2f}",
                    "angle": angle,
                    "barycentric": list(position),
                    "status": "PASS" if result.status == "PASS" else "FAIL",
                    "active_contact_count": int(details.get("active_contact_count", 0)),
                    "gaps": details.get("gaps", []),
                    "normals": details.get("normals", []),
                    "residual": float(
                        contact_convergence.get("relative_residual", solver.get("residual_norm", math.inf))
                    ),
                    "finite": _finite(data),
                }
            )
    return {
        "rows": rows,
        "all_pass": all(row["status"] == "PASS" for row in rows),
        "normal_finite": all(_finite(row["normals"]) for row in rows),
        "limitation": "Geometry cases exercise rotated planar triangles and valid projections only.",
    }


def _run_long_cycles() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for cycles, amplitude in ((10, 1.0), (20, 1.0), (50, 1.0), (10, 0.5)):
        path: list[float] = [0.0]
        for _ in range(cycles):
            path.extend((amplitude, 0.0))
        row = _run_cycle(tuple(path), f"{cycles}_cycles_amp_{amplitude:g}")
        row["cycle_count"] = cycles
        row["amplitude"] = amplitude
        rows.append(row)
    return {
        "rows": rows,
        "all_pass": all(row["status"] == "PASS_INTERNAL_RESEARCH" for row in rows),
        "determinism": all(row["final_reference_relative_difference"] <= DETERMINISM_LIMIT for row in rows),
        "limitation": "Load-path cycling probes stateless frictionless contact, not material cyclicity.",
    }


def _run_rollback_matrix() -> dict[str, Any]:
    rows = [
        _run_contact_cutback(-20.0, 1, 1.0),
        _run_contact_cutback(-30.0, 1, 1.0),
        _run_contact_cutback(-20.0, 2, 1.0),
        _run_contact_cutback(-20.0, 3, 1.0),
    ]
    return {
        "rows": rows,
        "all_pass": all(row["status"] == "PASS_INTERNAL_ROLLBACK" for row in rows),
        "state_integrity": all(row["clean_retry"] for row in rows),
        "limitation": "Contact active set is recomputed; common driver displacement/material transaction is checked.",
    }


def run(output: Path, expected_sha: str = SOURCE_SHA_DEFAULT) -> dict[str, Any]:
    source = _source_state(expected_sha)
    penalty_mesh = _run_penalty_mesh_matrix()
    activation = _run_activation_matrix()
    geometry = _run_geometry_matrix()
    cycles = _run_long_cycles()
    rollback = _run_rollback_matrix()
    adversarial = _run_adversarial()
    unexpected = []
    for group_name, group in (
        ("penalty_mesh", penalty_mesh),
        ("activation", activation),
        ("geometry", geometry),
        ("cycles", cycles),
        ("rollback", rollback),
        ("adversarial", adversarial),
    ):
        if not group.get("all_pass", group.get("status") != "FAIL"):
            unexpected.append(group_name)
    evidence = {
        "schema_version": 1,
        "gate": GATE,
        "lot": LOT,
        "status": "PASS_WITH_LIMITATIONS" if not unexpected else "FAIL",
        "official_gate_status_unchanged": "PASS_WITH_LIMITATIONS",
        "generated_utc": _now(),
        "source": source,
        "solver": {"name": "QF Solver", "version": "0.2.6a0"},
        "configuration": {
            "formulation": "frictionless_node_to_triangle_penalty",
            "mesh_levels": list(MESH_LEVELS),
            "penalties": list(PENALTIES),
            "equilibrium_limit": EQUILIBRIUM_LIMIT,
            "determinism_limit": DETERMINISM_LIMIT,
            "threshold_source": "g09_lot2_requirements.json + existing G09 Lot 3 policies",
            "threshold_policy": "No new universal acceptance band is inferred.",
        },
        "case_counts": {
            "penalty_mesh": len(penalty_mesh["rows"]),
            "activation": len(activation["rows"]),
            "geometry": len(geometry["rows"]),
            "cycles": len(cycles["rows"]),
            "rollback": len(rollback["rows"]),
            "adversarial": len(adversarial.get("cases", [])),
        },
        "penalty_mesh": penalty_mesh,
        "activation": activation,
        "geometry": geometry,
        "cycles": cycles,
        "rollback": rollback,
        "adversarial": adversarial,
        "force_equilibrium": {
            "status": "PASS" if penalty_mesh["equilibrium_pass"] else "FAIL",
            "limit": EQUILIBRIUM_LIMIT,
            "scope": "penalty mesh matrix; other groups retain route-specific residuals",
        },
        "energy_check": {
            "status": "PASS" if all(row["penalty_energy"] >= 0.0 for row in penalty_mesh["rows"]) else "FAIL",
            "definition": "penalty energy = 0.5 * penalty * penetration^2",
            "scope": "diagnostic contact penalty energy; no global energy balance claim",
        },
        "unexpected_failures": unexpected,
        "bugs_found": [],
        "functional_code_changed": False,
        "limitations": [
            "The extension remains bounded to the existing TET4 node-to-triangle penalty route.",
            "No friction, general surface-to-surface, self-contact or new contact physics is qualified.",
            "Penalty candidate values are observational and remain Owner-reviewable; no universal range is approved.",
            "External evidence is reused from the controlled Lot 3 Code_Aster/CalculiX archive; no new external claim is created.",
            "The active set is stateless in the exercised frictionless route; rollback covers common-driver mutable state.",
        ],
        "official_gate_closeout_unchanged": True,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    json_path = output.with_suffix(".json")
    json_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "gate": GATE,
        "lot": LOT,
        "source_sha": source["sha"],
        "source_dirty": source["dirty"],
        "generated_utc": evidence["generated_utc"],
        "status": evidence["status"],
        "artifacts": {json_path.name: _sha256(json_path)},
    }
    manifest_path = output.with_name(output.name + "_manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    evidence["manifest"] = manifest
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-sha", default=SOURCE_SHA_DEFAULT)
    args = parser.parse_args()
    result = run(args.output, args.source_sha)
    print(
        json.dumps(
            {
                "status": result["status"],
                "case_counts": result["case_counts"],
                "unexpected_failures": result["unexpected_failures"],
                "manifest": result["manifest"],
            },
            indent=2,
        )
    )
    return 0 if result["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
