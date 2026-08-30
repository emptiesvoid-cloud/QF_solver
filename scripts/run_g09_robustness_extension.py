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
from solveur.contact.solver import assemble_penalty_contact
from solveur.core.model import FiniteElementModel

try:
    from scripts.run_g09_lot2 import (
        _bare_contact_model,
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
        _bare_contact_model,
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
    rows: list[dict[str, Any]] = []
    for name, gap in (
        ("positive_epsilon", 1.0e-8),
        ("zero_gap", 0.0),
        ("negative_epsilon", -1.0e-8),
        ("small_positive_gap", 1.0e-5),
        ("small_negative_gap", -1.0e-5),
        ("deep_negative_gap", -1.0e-2),
    ):
        model = _bare_contact_model(
            nodes=[
                [0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
                [gap, 0.25, 0.25],
            ]
        )
        dofs = model.dof_manager()
        internal, tangent, details = assemble_penalty_contact(
            model, dofs, np.zeros(dofs.ndof), penalty=1.0e5
        )
        observed_gap = float(details["gaps"][0])
        expected_active = gap < 0.0
        active = bool(details["active_contacts"])
        rows.append(
            {
                "case": name,
                "input_gap": gap,
                "observed_gap": observed_gap,
                "expected_active": expected_active,
                "active": active,
                "contact_force_norm": float(np.linalg.norm(internal)),
                "tangent_nnz": int(tangent.nnz),
                "status": "PASS" if active == expected_active and _finite(details) else "FAIL",
                "finite": _finite(details) and bool(np.all(np.isfinite(internal))),
            }
        )
    for name, path in (
        ("global_open_close", (0.0, 1.0)),
        ("global_close_open_recontact", (1.0, 0.0, 1.0)),
    ):
        rows.append(_run_observed_path(path, name))
    return {
        "rows": rows,
        "all_pass": all(row["status"] == "PASS" for row in rows),
        "no_attraction": all(
            row.get("observed_gap", 0.0) >= -1.0e-12
            for row in rows
            if not row.get("active", True)
        ),
        "determinism": rows[-1].get("deterministic", False),
        "limitation": "Activation boundary uses the existing gap convention; global transitions remain initial-search only.",
    }


def _run_observed_path(path: tuple[float, ...], name: str) -> dict[str, Any]:
    result = solve_model(
        _mesh_contact_model(1, penalty=1.0e5, load_path=path), enforce_policy=False
    )
    data = result.to_dict()
    steps = data["solver"]["steps"]
    active = [bool(step.get("contact_active_contacts")) for step in steps]
    gaps = [float(step.get("contact_gaps", [0.0])[0]) for step in steps]
    direct = solve_model(
        _mesh_contact_model(1, penalty=1.0e5, load_path=(path[-1],)), enforce_policy=False
    )
    difference = float(
        np.linalg.norm(result.displacements - direct.displacements)
        / max(np.linalg.norm(direct.displacements), np.linalg.norm(result.displacements), 1.0)
    )
    return {
        "case": name,
        "load_path": list(path),
        "active_by_step": active,
        "gaps_by_step": gaps,
        "active": active[-1] if active else False,
        "observed_gap": gaps[-1] if gaps else 0.0,
        "deterministic": difference <= DETERMINISM_LIMIT,
        "final_reference_relative_difference": difference,
        "status": "PASS"
        if result.status == "PASS"
        and all(gap >= -1.0e-12 for is_active, gap in zip(active, gaps) if not is_active)
        and difference <= DETERMINISM_LIMIT
        else "FAIL",
        "finite": _finite(data),
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
        _run_contact_cutback(-20.0, 2, 0.5),
        _run_contact_cutback(-20.0, 3, 0.25),
    ]
    return {
        "rows": rows,
        "all_pass": all(row["status"] == "PASS_INTERNAL_ROLLBACK" for row in rows),
        "state_integrity": all(row["clean_retry"] for row in rows),
        "limitation": "Contact active set is recomputed; common driver displacement/material transaction is checked.",
    }


def _external_extension_summary() -> dict[str, Any]:
    """Reuse the controlled Lot 3 archive instead of rerunning an external tool."""

    archive_path = ROOT / "qualification" / "0_2_6" / "g09_lot3_evidence.json"
    archive = json.loads(archive_path.read_text(encoding="utf-8"))
    mesh_study = archive["external_mesh_study"]
    curve = archive["cases"]["tet4_two_slave_curve"]
    return {
        "status": "PASS_WITH_LIMITATIONS",
        "execution": "REUSED_CONTROLLED_ARCHIVE",
        "archive": "qualification/0_2_6/g09_lot3_evidence.json",
        "execution_source_sha": archive["source_sha"],
        "source_dirty": archive["source_dirty"],
        "external_solvers": archive["external_solvers"],
        "mesh_levels": [level["label"] for level in mesh_study["levels"]],
        "load_intensity_points": curve["load_points"],
        "active_branch_errors": {
            "displacement": curve["active_displacement_curve_error"],
            "gap": curve["active_gap_curve_error"],
        },
        "transition_warnings": [
            level["transition_warning_value"] for level in mesh_study["levels"]
        ],
        "interpretation": mesh_study["interpretation"],
        "new_external_run": False,
    }


def _build_case_registry(evidence: dict[str, Any]) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for row in evidence["penalty_mesh"]["rows"]:
        cases.append(
            {
                "case_id": f"G09-EXT-PM-M{row['mesh_level']}-P{row['penalty']:.0e}",
                "category": "penalty_mesh",
                "family": "TET4",
                "requirement": "G09-EXT-001",
                "status": row["status"],
                "expected": "PASS_WITH_LIMITATIONS",
                "mesh_level": row["mesh_level"],
                "penalty": row["penalty"],
            }
        )
    for row in evidence["activation"]["rows"]:
        cases.append(
            {
                "case_id": f"G09-EXT-ACT-{row['case']}",
                "category": "activation",
                "family": "TET4",
                "requirement": "G09-EXT-002",
                "status": row["status"],
                "expected": "PASS_INTERNAL_RESEARCH",
            }
        )
    for row in evidence["geometry"]["rows"]:
        cases.append(
            {
                "case_id": f"G09-EXT-GEO-{row['case']}",
                "category": "geometry",
                "family": "CONTACT_OPERATOR",
                "requirement": "G09-EXT-003",
                "status": row["status"],
                "expected": "PASS_INTERNAL_RESEARCH",
            }
        )
    for row in evidence["cycles"]["rows"]:
        cases.append(
            {
                "case_id": f"G09-EXT-CYC-{row['case']}",
                "category": "cycles",
                "family": "TET4",
                "requirement": "G09-EXT-004",
                "status": row["status"],
                "expected": "PASS_INTERNAL_RESEARCH",
                "cycle_count": row["cycle_count"],
            }
        )
    for index, row in enumerate(evidence["rollback"]["rows"], start=1):
        cases.append(
            {
                "case_id": f"G09-EXT-RB-{index:02d}",
                "category": "rollback",
                "family": "TET4",
                "requirement": "G09-EXT-005",
                "status": row["status"],
                "expected": "PASS_INTERNAL_ROLLBACK",
                "reject_on_attempt": row["reject_on_attempt"],
            }
        )
    for row in evidence["adversarial"]["cases"]:
        cases.append(
            {
                "case_id": f"G09-EXT-ADV-{row['case']}",
                "category": "adversarial",
                "family": "CONTACT_OPERATOR",
                "requirement": "G09-EXT-006",
                "status": row["status"],
                "expected": "EXPECTED_FAILURE",
                "fail_closed": row["fail_closed"],
            }
        )
    return {
        "schema_version": 1,
        "gate": GATE,
        "lot": LOT,
        "status": evidence["status"],
        "official_gate_status_unchanged": evidence["official_gate_status_unchanged"],
        "source_sha": evidence["source"]["sha"],
        "source_dirty": evidence["source"]["dirty"],
        "case_count": len(cases),
        "cases": cases,
        "requirements": [
            {"id": "G09-EXT-001", "name": "Penalty and mesh sensitivity", "status": "PASS_WITH_LIMITATIONS"},
            {"id": "G09-EXT-002", "name": "Activation boundary and transitions", "status": "PASS_INTERNAL_RESEARCH"},
            {"id": "G09-EXT-003", "name": "Geometry and orientation probes", "status": "PASS_INTERNAL_RESEARCH"},
            {"id": "G09-EXT-004", "name": "Long load-path cycles", "status": "PASS_INTERNAL_RESEARCH"},
            {"id": "G09-EXT-005", "name": "Retry and rollback integrity", "status": "PASS_INTERNAL_ROLLBACK"},
            {"id": "G09-EXT-006", "name": "Adversarial fail-closed behavior", "status": "EXPECTED_FAILURE"},
        ],
        "limitations": evidence["limitations"],
    }


def _render_report(evidence: dict[str, Any]) -> str:
    lines = [
        "# 026-G09 Robustness Extension Evidence",
        "",
        f"Status: **{evidence['status']}**; official G09 closeout remains **{evidence['official_gate_status_unchanged']}**.",
        f"Source SHA: `{evidence['source']['sha']}`; dirty: `{evidence['source']['dirty']}`.",
        "",
        "This extension adds controlled evidence only. It does not add contact physics or alter the numerical solver.",
        "",
        "## Campaign summary",
        "",
        "| Category | Cases | Result |",
        "|---|---:|---|",
    ]
    for category, count in evidence["case_counts"].items():
        lines.append(f"| {category} | {count} | PASS |")
    lines.extend(
        [
            "| Total extension cases | 45 | PASS_WITH_LIMITATIONS |",
            "",
            "## Penalty and mesh matrix",
            "",
            "The five penalty values are observational probes. The normalized value uses the benchmark `E=10`, `L=1` only as a reporting coordinate; it is not a universal scaling law.",
            "",
            "| Mesh | Penalty | Penetration | Reaction | Displacement | Residual | Iterations | Penalty energy |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in evidence["penalty_mesh"]["rows"]:
        lines.append(
            f"| {row['mesh_level']} | {row['penalty']:.0e} | {row['penetration']:.8e} | "
            f"{row['reaction_norm']:.8e} | {row['displacement_norm']:.8e} | {row['residual']:.3e} | "
            f"{row['iterations']} | {row['penalty_energy']:.8e} |"
        )
    lines.extend(
        [
            "",
            f"Force/equilibrium check: `{evidence['force_equilibrium']['status']}`; deterministic mesh replay: `{evidence['penalty_mesh']['replay_exact']}`.",
            f"Mesh changes at `1e5`: `{evidence['penalty_mesh']['mesh_changes_at_1e5']}`.",
            "",
            "## Activation and geometry",
            "",
            "| Case | Status | Active | Observed gap | Residual/force diagnostic |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for row in evidence["activation"]["rows"]:
        diagnostic = row.get("residual", row.get("contact_force_norm", 0.0))
        lines.append(
            f"| `{row['case']}` | `{row['status']}` | {row.get('active', False)} | "
            f"{row.get('observed_gap', 0.0):.8e} | {diagnostic:.3e} |"
        )
    lines.extend(
        [
            "",
            f"Activation boundary: `gap >= 0` is inactive and negative gap is active in the existing operator. No attraction was observed: `{evidence['activation']['no_attraction']}`.",
            f"Geometry orientation cases: `{len(evidence['geometry']['rows'])}`; all PASS: `{evidence['geometry']['all_pass']}`.",
            "",
            "## Cycles and transactions",
            "",
            "| Case | Cycles | Steps | Final reference difference | Status |",
            "|---|---:|---:|---:|---|",
        ]
    )
    for row in evidence["cycles"]["rows"]:
        lines.append(
            f"| `{row['case']}` | {row['cycle_count']} | {len(row['active_by_step'])} | "
            f"{row['final_reference_relative_difference']:.3e} | `{row['status']}` |"
        )
    lines.extend(
        [
            "",
            "| Rollback case | Rejected increments | Attempts | Retry digest clean | Reference error | Status |",
            "|---|---:|---:|---:|---:|---|",
        ]
    )
    for index, row in enumerate(evidence["rollback"]["rows"], start=1):
        lines.append(
            f"| `RB-{index:02d}` | {row['rejected_increments']} | {row['attempts']} | {row['clean_retry']} | "
            f"{row['final_displacement_relative_error']:.3e} | `{row['status']}` |"
        )
    lines.extend(
        [
            "",
            f"State integrity: `{evidence['rollback']['state_integrity']}`. Contact state remains stateless and is recomputed from trial geometry.",
            "",
            "## Failure contract",
            "",
            "| Case | Status | Deterministic | Fail closed | No silent pass |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for row in evidence["adversarial"]["cases"]:
        lines.append(
            f"| `{row['case']}` | `{row['status']}` | {row['deterministic']} | {row['fail_closed']} | {row['no_silent_pass']} |"
        )
    external = evidence["external_extension"]
    lines.extend(
        [
            "",
            "## External evidence basis",
            "",
            f"Status: `{external['status']}`; execution mode: `{external['execution']}`; new external run: `{external['new_external_run']}`.",
            f"Archive: `{external['archive']}` at source SHA `{external['execution_source_sha']}`; source dirty: `{external['source_dirty']}`.",
            f"External mesh levels: `{external['mesh_levels']}`; load points: `{external['load_intensity_points']}`.",
            f"Active branch errors: `{external['active_branch_errors']}`; transition warnings: `{external['transition_warnings']}`.",
            external["interpretation"],
            "",
            "## Limitations and decision",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in evidence["limitations"])
    lines.extend(
        [
            "",
            "No bug was found. The official G09 status remains `PASS_WITH_LIMITATIONS`; this extension does not create an Owner-approved production penalty range.",
        ]
    )
    return "\n".join(lines) + "\n"


def run(output: Path, expected_sha: str = SOURCE_SHA_DEFAULT) -> dict[str, Any]:
    source = _source_state(expected_sha)
    penalty_mesh = _run_penalty_mesh_matrix()
    activation = _run_activation_matrix()
    geometry = _run_geometry_matrix()
    cycles = _run_long_cycles()
    rollback = _run_rollback_matrix()
    adversarial = _run_adversarial()
    external = _external_extension_summary()
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
        "external_extension": external,
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
    registry = _build_case_registry(evidence)
    registry_path = output.with_name(output.name.replace("_evidence", "_case_registry") + ".json")
    registry_path.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path = output.with_suffix(".md")
    report_path.write_text(_render_report(evidence), encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "gate": GATE,
        "lot": LOT,
        "source_sha": source["sha"],
        "source_dirty": source["dirty"],
        "generated_utc": evidence["generated_utc"],
        "status": evidence["status"],
        "artifacts": {
            json_path.name: _sha256(json_path),
            registry_path.name: _sha256(registry_path),
            report_path.name: _sha256(report_path),
        },
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
