"""Run the controlled 026-G09 robustness extension campaign.

This runner composes the already-qualified bounded contact paths.  It adds no
contact formulation or solver behavior; all observations are diagnostic
extension evidence and do not change the official G09 closeout.
"""

from __future__ import annotations

# Compatibility drivers intentionally re-export selected imported helpers.
# ruff: noqa: F401

import argparse
import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

UTC = timezone.utc

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
# ruff: noqa: E402

try:
    from scripts.canonical_artifact_digest import canonical_artifact_sha256
except ModuleNotFoundError:  # Direct execution from the runners directory.
    from canonical_artifact_digest import canonical_artifact_sha256

from solveur.api import solve_model
from solveur.contact.entities import FrictionlessContact
from solveur.contact.solver import assemble_penalty_contact
from solveur.core.assembly.nonlinear import build_nonlinear_assembly_plan
from solveur.core.errors import NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear.controls import NonlinearSolverOptions
from solveur.core.nonlinear.material_state import MaterialStateSession, initial_material_states, state_digest
from solveur.core.nonlinear.solver import NonlinearStaticSolver

try:
    from scripts.run_g09_lot2 import (
        _bare_contact_model,
        _canonical,
        _finite,
        _mesh_contact_model,
        _run_adversarial,
        _run_contact_cutback,
        _run_cycle as _run_cycle_base,
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
        _run_cycle as _run_cycle_base,
        _solve_contact_case,
    )

GATE = "026-G09"
LOT = "ROBUSTNESS_EXTENSION"
SOURCE_SHA_DEFAULT = "1468eb051093b7be54940da69c4a3d2270967da9"
MESH_LEVELS = (1, 2, 4)
PENALTIES = (1.0e2, 1.0e3, 1.0e4, 1.0e5, 1.0e6)
EQUILIBRIUM_LIMIT = 1.0e-8
DETERMINISM_LIMIT = 1.0e-12
COMPARISON_TOLERANCE = 1.0e-8


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
    return canonical_artifact_sha256(path)


def _artifact_paths(output: Path) -> tuple[Path, Path, Path, Path, Path]:
    """Resolve canonical evidence paths for either a stem or ``*.json`` input."""
    evidence_path = output if output.suffix.lower() == ".json" else output.with_suffix(".json")
    stem = evidence_path.stem.removesuffix("_evidence")
    registry_path = evidence_path.with_name(f"{stem}_case_registry.json")
    requirements_path = evidence_path.with_name(f"{stem}_requirements.json")
    report_path = ROOT / "docs" / "verification" / "0_2_6" / "0_2_6_g09_robustness_extension_evidence.md"
    manifest_path = evidence_path.with_name(f"{stem}_manifest.json")
    return evidence_path, registry_path, requirements_path, report_path, manifest_path


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
def _solve_contact_case_with_equilibrium(model: FiniteElementModel, penalty: float) -> dict[str, Any]:
    """Retain the existing case metrics and archive global force/moment audits."""
    row = _solve_contact_case(model, penalty)
    audit = solve_model(model, enforce_policy=False).to_dict().get("audit", {}).get("equilibrium", {})
    force_error = float(audit.get("force_balance_relative_error", math.inf))
    moment_error = float(audit.get("moment_balance_relative_error", math.inf))
    row.update(
        {
            "force_balance_relative_error": force_error,
            "moment_balance_relative_error": moment_error,
            "external_moment_about_origin": audit.get("external_moment_about_origin", []),
            "reaction_moment_about_origin": audit.get("reaction_moment_about_origin", []),
            "force_moment_equilibrium_pass": force_error <= EQUILIBRIUM_LIMIT
            and moment_error <= EQUILIBRIUM_LIMIT,
        }
    )
    return row


def _run_penalty_mesh_matrix() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for mesh_level in MESH_LEVELS:
        for penalty in PENALTIES:
            row = _solve_contact_case_with_equilibrium(
                _mesh_contact_model(mesh_level, penalty=penalty), penalty
            )
            rows.append(
                {
                    "mesh_level": mesh_level,
                    "penalty": penalty,
                    "normalized_penalty_E10_L1": penalty / 10.0,
                    **row,
                    "penalty_energy": 0.5 * penalty * row["penetration"] ** 2,
                    "equilibrium_pass": row["finite"]
                    and row["residual"] <= EQUILIBRIUM_LIMIT
                    and row["force_moment_equilibrium_pass"],
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
    replay = _solve_contact_case_with_equilibrium(_mesh_contact_model(4, penalty=1.0e5), 1.0e5)
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


def _distorted_spring_model() -> FiniteElementModel:
    """Build a valid skew planar triangle without changing contact physics."""
    master = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.15, 1.0, 0.0]])
    weights = np.array([0.20, 0.35, 0.45])
    slave = weights @ master + np.array([0.0, 0.0, 0.1])
    normal = np.cross(master[1] - master[0], master[2] - master[0])
    normal /= np.linalg.norm(normal)
    model = FiniteElementModel.from_raw(
        nodes=np.vstack((master, slave)).tolist(),
        elements=[],
        materials={},
        fixed_dofs=[{"node": index, "dofs": ["UX", "UY", "UZ"]} for index in range(3)],
        springs=[{"node_a": 3, "dofs": ["UX", "UY", "UZ"], "stiffness": [1000.0] * 3}],
        loads=[
            {"node": 3, "dof": dof, "value": float(-200.0 * normal[index])}
            for index, dof in enumerate(("UX", "UY", "UZ"))
        ],
        analysis={"type": "linear_static", "method": "direct", "contact_max_iterations": 12},
    )
    model.contacts.append(FrictionlessContact(name="distorted", slave_node=3, master_nodes=(0, 1, 2)))
    return model


def _multi_face_patch_model() -> FiniteElementModel:
    """Build two coplanar master triangles and two slave patch nodes."""
    master = np.array(
        [[0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 1.0, 1.0], [0.0, 0.0, 1.0]]
    )
    slaves = np.array([[0.1, 0.25, 0.25], [0.1, 0.75, 0.75]])
    nodes = np.vstack((master, slaves))
    model = FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[],
        materials={},
        fixed_dofs=[{"node": index, "dofs": ["UX", "UY", "UZ"]} for index in range(4)],
        springs=[
            {"node_a": index, "dofs": ["UX", "UY", "UZ"], "stiffness": [1000.0] * 3}
            for index in (4, 5)
        ],
        loads=[
            {"node": index, "dof": "UX", "value": -200.0}
            for index in (4, 5)
        ],
        analysis={"type": "linear_static", "method": "direct", "contact_max_iterations": 12},
    )
    model.contacts.append(
        FrictionlessContact(
            name="coplanar_patch",
            slave_node=4,
            master_nodes=(0, 1, 2),
            master_faces=((0, 1, 2), (0, 2, 3)),
            slave_patch_nodes=(4, 5),
        )
    )
    return model


def _geometry_solver_row(model: FiniteElementModel, name: str) -> dict[str, Any]:
    result = solve_model(model, enforce_policy=False)
    data = result.to_dict()
    solver = data["solver"]
    details = solver.get("contact", {})
    contact_convergence = details.get("convergence", {})
    return {
        "case": name,
        "status": "PASS" if result.status == "PASS" else "FAIL",
        "active_contact_count": int(details.get("active_contact_count", 0)),
        "gaps": details.get("gaps", []),
        "normals": details.get("normals", []),
        "master_face_indices": details.get("master_face_indices", []),
        "slave_node_count": details.get("slave_node_count", 0),
        "residual": float(
            contact_convergence.get("relative_residual", solver.get("residual_norm", math.inf))
        ),
        "finite": _finite(data),
    }


def _run_geometry_matrix() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for index, angle in enumerate((0.0, 0.2, 0.5, 1.0)):
        positions = ((0.25, 0.25), (0.60, 0.20))
        if index == 0:
            positions += ((0.50, 0.50), (0.0, 0.0), (0.999, 0.0005))
        for position in positions:
            model = _rotated_spring_model(angle, position)
            row = _geometry_solver_row(
                model, f"orientation_{index}_bary_{position[0]:.3f}_{position[1]:.3f}"
            )
            row.update({"angle": angle, "barycentric": list(position)})
            rows.append(row)
    rows.append(_geometry_solver_row(_distorted_spring_model(), "valid_distorted_triangle"))
    surface_row = _geometry_solver_row(_multi_face_patch_model(), "coplanar_faces_multi_slave_patch")
    surface_row["geometry_features"] = ["multiple_coplanar_triangles", "multiple_active_slave_nodes"]
    rows.append(surface_row)
    return {
        "rows": rows,
        "all_pass": all(row["status"] == "PASS" for row in rows),
        "normal_finite": all(_finite(row["normals"]) for row in rows),
        "coverage": {
            "orientations": True,
            "center_edge_vertex": True,
            "multiple_coplanar_triangles": True,
            "multiple_active_slave_nodes": True,
            "regular_and_valid_distorted_triangles": True,
        },
        "limitation": "Geometry cases remain bounded to valid node-to-faceted-surface projections; no self-contact or general surface claim is made.",
    }
