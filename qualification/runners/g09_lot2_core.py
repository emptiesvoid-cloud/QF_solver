"""Run the controlled 026-G09 contact Lot 2 evidence campaign.

Lot 2 exercises the existing frictionless node-to-triangle penalty path.  It
adds no contact physics and deliberately leaves the official G09 gate open.
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
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

UTC = timezone.utc

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
# ruff: noqa: E402

from solveur.api import solve_model
from solveur.contact.entities import FrictionlessContact
from solveur.contact.solver import assemble_penalty_contact
from solveur.core.errors import NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear.material_state import state_digest
from solveur.core.nonlinear.solver import NonlinearStaticSolver
from solveur.verification.robustness_mesh import _refinement_model

try:
    from scripts.run_g09_lot1 import _expected_penetration_failure
except ModuleNotFoundError:  # Direct ``python scripts/run_g09_lot2.py`` execution.
    from run_g09_lot1 import _expected_penetration_failure

GATE = "026-G09"
SOURCE_CONTRACT = ROOT / "qualification" / "0_2_6" / "g09_lot2_requirements.json"
CASE_CONTRACT = ROOT / "qualification" / "0_2_6" / "g09_lot2_case_registry.json"
DEFAULT_OUTPUT = ROOT / "qualification" / "0_2_6"
MESH_LEVELS = (1, 2, 4)
PENALTIES = (1.0e4, 1.0e5, 1.0e6)
SOLVER_TOLERANCE = 1.0e-8
COMPARISON_TOLERANCE = 1.0e-8


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def _source_state() -> dict[str, Any]:
    return {"sha": _git("rev-parse", "HEAD"), "dirty": bool(_git("status", "--porcelain"))}


def _finite(value: Any) -> bool:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return True
    if isinstance(value, (int, float)):
        return math.isfinite(float(value))
    if isinstance(value, dict):
        return all(_finite(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(_finite(item) for item in value)
    return True


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mesh_contact_model(
    cells: int,
    *,
    penalty: float,
    load: float = -20.0,
    load_path: tuple[float, ...] | None = (1.0,),
    max_iterations: int = 80,
    path_dependent: bool = False,
) -> FiniteElementModel:
    """Build one reproducible physical problem at a mesh level.

    The unit block, fixed x=0 face, contact plane and total nodal load are
    unchanged with refinement.  Only the existing TET4 mesh subdivision varies.
    """

    model = _refinement_model("TET4", cells)
    model.materials["j2"] = (
        {
            "type": "von_mises_elastoplastic_3d",
            "E": 10.0,
            "nu": 0.3,
            "yield_stress": 0.02,
            "hardening_modulus": 10.0,
        }
        if path_dependent
        else {"type": "isotropic_3d", "E": 10.0, "nu": 0.3}
    )
    nodes = model.nodes
    slave = int(np.flatnonzero(np.all(np.isclose(nodes, [1.0, 0.0, 0.0]), axis=1))[0])
    master_nodes = tuple(
        int(np.flatnonzero(np.all(np.isclose(nodes, point), axis=1))[0])
        for point in ([0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0])
    )
    model.loads = [replace(model.loads[0], node=slave, value=load)]
    model.contacts.append(
        FrictionlessContact(name="lot2_mesh_plane", slave_node=slave, master_nodes=master_nodes)
    )
    parameters = dict(model.analysis.parameters)
    if load_path is None:
        parameters.pop("load_path", None)
    else:
        parameters["load_path"] = list(load_path)
    parameters.update(
        {
            "contact_mode": "penalty",
            "contact_penalty": penalty,
            "contact_search_mode": "initial",
            "max_iterations": max_iterations,
            "tolerance": SOLVER_TOLERANCE,
        }
    )
    model.analysis = replace(model.analysis, parameters=parameters)
    return model


def _reaction_norm(result: Any) -> float:
    audit = result.to_dict().get("audit", {})
    for vector in audit.get("vectors", []):
        if vector.get("name") == "reactions":
            return float(vector["norm"])
    return 0.0


def _solve_contact_case(model: FiniteElementModel, penalty: float) -> dict[str, Any]:
    result = solve_model(model, enforce_policy=False)
    data = result.to_dict()
    steps = data["solver"]["steps"]
    final = steps[-1]
    _, _, contact = assemble_penalty_contact(
        model, model.dof_manager(), result.displacements, penalty=penalty
    )
    return {
        "status": "PASS" if result.status == "PASS" else "FAIL",
        "solver_status": result.status,
        "run_verdict": result.run_verdict.value,
        "node_count": int(result.node_count),
        "element_count": int(result.element_count),
        "dof_count": int(result.ndof),
        "displacement_norm": float(np.linalg.norm(result.displacements)),
        "reaction_norm": _reaction_norm(result),
        "active_contacts": list(final.get("contact_active_contacts", [])),
        "gap": float(final.get("contact_gaps", [0.0])[0]),
        "penetration": max(-float(final.get("contact_gaps", [0.0])[0]), 0.0),
        "contact_force_norm": float(contact["contact_force_norm"]),
        "residual": float(final["relative_residual"]),
        "residual_history": [float(value) for value in final["residual_history"]],
        "iterations": int(final["iterations"]),
        "minimum_det_f": float(data["solver"].get("minimum_det_f", 1.0)),
        "finite": all(np.isfinite(result.displacements)) and _finite(final),
    }
def _run_mesh_sensitivity() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for cells in MESH_LEVELS:
        for penalty in PENALTIES:
            row = _solve_contact_case(
                _mesh_contact_model(cells, penalty=penalty), penalty
            )
            rows.append({"mesh_level": cells, "penalty": penalty, **row})

    reference = [row for row in rows if row["penalty"] == 1.0e5]
    levels = [
        {
            "mesh_level": int(row["mesh_level"]),
            "node_count": row["node_count"],
            "element_count": row["element_count"],
            "dof_count": row["dof_count"],
            "gap": row["gap"],
            "penetration": row["penetration"],
            "displacement_norm": row["displacement_norm"],
            "reaction_norm": row["reaction_norm"],
            "active_contacts": row["active_contacts"],
            "residual": row["residual"],
            "iterations": row["iterations"],
            "finite": row["finite"],
        }
        for row in reference
    ]
    displacement_changes: list[dict[str, float]] = []
    for left, right in zip(levels, levels[1:]):
        displacement_changes.append(
            {
                "from_mesh": float(left["mesh_level"]),
                "to_mesh": float(right["mesh_level"]),
                "relative_displacement_change": abs(
                    right["displacement_norm"] - left["displacement_norm"]
                )
                / max(abs(left["displacement_norm"]), 1.0e-15),
                "relative_reaction_change": abs(
                    right["reaction_norm"] - left["reaction_norm"]
                )
                / max(abs(left["reaction_norm"]), 1.0e-15),
            }
        )
    replay = _solve_contact_case(_mesh_contact_model(4, penalty=1.0e5), 1.0e5)
    replay_reference = next(row for row in reference if row["mesh_level"] == 4)
    replay_keys = (
        "status",
        "solver_status",
        "node_count",
        "element_count",
        "dof_count",
        "displacement_norm",
        "reaction_norm",
        "active_contacts",
        "gap",
        "penetration",
        "contact_force_norm",
        "residual",
        "iterations",
    )
    replay_exact = _canonical({key: replay[key] for key in replay_keys}) == _canonical(
        {key: replay_reference[key] for key in replay_keys}
    )
    penalty_rows = [
        {
            "mesh_level": int(row["mesh_level"]),
            "penalty": row["penalty"],
            "penetration": row["penetration"],
            "reaction_norm": row["reaction_norm"],
            "residual": row["residual"],
            "iterations": row["iterations"],
            "status": row["status"],
        }
        for row in rows
    ]
    penetration_monotone = all(
        left["penetration"] >= right["penetration"]
        for mesh in MESH_LEVELS
        for left, right in zip(
            [row for row in rows if row["mesh_level"] == mesh],
            [row for row in rows if row["mesh_level"] == mesh][1:],
        )
    )
    return {
        "status": "PASS_WITH_LIMITATIONS"
        if all(row["status"] == "PASS" and row["finite"] for row in rows)
        and replay_exact
        and penetration_monotone
        else "FAIL",
        "mesh_levels": levels,
        "penalty_rows": penalty_rows,
        "mesh_step_changes": displacement_changes,
        "replay_exact": replay_exact,
        "penetration_monotone_by_mesh": penetration_monotone,
        "same_physical_problem": True,
        "total_load_preserved": True,
        "penalty_values": list(PENALTIES),
        "raw_rows": rows,
        "limitations": [
            "Three x-direction subdivisions of the bounded TET4 benchmark; this is not a universal mesh-convergence claim.",
            "Penalty results are a sensitivity study; no production interval or conditioning cutoff is approved.",
        ],
    }

def _run_cycle(path: tuple[float, ...], name: str) -> dict[str, Any]:
    result = solve_model(
        _mesh_contact_model(1, penalty=1.0e5, load_path=path), enforce_policy=False
    )
    data = result.to_dict()
    steps = data["solver"]["steps"]
    active = [bool(step.get("contact_active_contacts")) for step in steps]
    gaps = [float(step.get("contact_gaps", [0.0])[0]) for step in steps]
    expected = [factor > 0.0 for factor in path]
    inactive_gaps_nonnegative = all(
        gap >= -1.0e-12 for is_active, gap in zip(active, gaps) if not is_active
    )
    active_pressure_nonnegative = all(
        -1.0e5 * gap >= 0.0 for is_active, gap in zip(active, gaps) if is_active
    )
    direct = solve_model(
        _mesh_contact_model(1, penalty=1.0e5, load_path=(path[-1],)),
        enforce_policy=False,
    )
    final_difference = float(
        np.linalg.norm(result.displacements - direct.displacements)
        / max(np.linalg.norm(direct.displacements), np.linalg.norm(result.displacements), 1.0)
    )
    return {
        "case": name,
        "load_path": list(path),
        "status": "PASS_INTERNAL_RESEARCH"
        if result.status == "PASS"
        and active == expected
        and inactive_gaps_nonnegative
        and active_pressure_nonnegative
        and final_difference <= COMPARISON_TOLERANCE
        else "FAIL",
        "solver_status": result.status,
        "active_by_step": active,
        "expected_active_by_step": expected,
        "gaps_by_step": gaps,
        "iterations_by_step": [int(step["iterations"]) for step in steps],
        "residuals_by_step": [float(step["relative_residual"]) for step in steps],
        "inactive_gaps_nonnegative": inactive_gaps_nonnegative,
        "active_penalty_pressure_nonnegative": active_pressure_nonnegative,
        "final_reference_relative_difference": final_difference,
        "contact_state_transaction": "N/A - active set recomputed from each trial displacement",
    }


def _run_cycles() -> dict[str, Any]:
    paths = (
        ("open_to_close", (0.0, 1.0)),
        ("close_to_open", (1.0, 0.0)),
        ("open_close_open", (0.0, 1.0, 0.0)),
        ("open_close_open_reclose", (0.0, 1.0, 0.0, 1.0)),
        ("load_up_down", (0.0, 0.25, 0.5, 0.75, 1.0, 0.75, 0.5, 0.25, 0.0)),
    )
    rows = [_run_cycle(path, name) for name, path in paths]
    replay = _run_cycle(paths[3][1], "recontact_replay")
    original = rows[3]
    original_comparison = {key: value for key, value in original.items() if key != "case"}
    replay_comparison = {key: value for key, value in replay.items() if key != "case"}
    return {
        "status": "PASS_INTERNAL_RESEARCH"
        if all(row["status"] == "PASS_INTERNAL_RESEARCH" for row in rows)
        and _canonical(original_comparison) == _canonical(replay_comparison)
        else "FAIL",
        "cases": rows,
        "recontact_replay_exact": _canonical(original_comparison) == _canonical(replay_comparison),
        "recontact": True,
        "limitations": [
            "Initial-configuration node-to-triangle contact only; no finite-sliding claim.",
            "The cycle oracle is a controlled load-path transition check, not a cyclic material qualification.",
        ],
    }


def _run_contact_cutback(load: float, reject_on_attempt: int, initial_increment: float) -> dict[str, Any]:
    model = _mesh_contact_model(
        1,
        penalty=1.0e5,
        load=load,
        load_path=None,
        max_iterations=80,
        path_dependent=True,
    )
    parameters = dict(model.analysis.parameters)
    parameters.update(
        {
            "adaptive_load_steps": True,
            "initial_load_increment": initial_increment,
            "min_load_increment": 0.125,
            "max_load_increment": initial_increment,
            "cutback_factor": 0.5,
            "growth_factor": 1.0,
            "max_cutbacks": 4,
        }
    )
    model.analysis = replace(model.analysis, parameters=parameters)

    class RejectingSolver(NonlinearStaticSolver):
        def __init__(self) -> None:
            super().__init__()
            self.attempts = 0
            self.committed_digest_before_failure = ""
            self.retry_state_digest = ""
            self.committed_displacement = np.array([], dtype=float)
            self.retry_displacement = np.array([], dtype=float)
            self.clean_retry = False

        def _solve_load_step(
            self,
            model: FiniteElementModel,
            dofs: Any,
            displacement: np.ndarray,
            free: np.ndarray,
            target_load: np.ndarray,
            material_states: Any,
            step: int,
            load_factor: float,
            load_increment: float,
            cached_tangent: Any,
            max_iterations: int,
            tolerance: float,
            linear_method: str,
            min_alpha: float,
            max_reductions: int,
            armijo: float,
            previous_load: np.ndarray | None = None,
            reference_force_norm: float | None = None,
        ) -> Any:
            self.attempts += 1
            if self.attempts == reject_on_attempt:
                self.committed_digest_before_failure = state_digest(material_states)
                self.committed_displacement = displacement.copy()
                displacement[:] = 123.0
                first_element = min(material_states)
                material_states[first_element][0]["equivalent_plastic_strain"] = 999.0
                raise NumericalConvergenceError("controlled contact increment rejection")
            if self.attempts == reject_on_attempt + 1:
                self.retry_state_digest = state_digest(material_states)
                self.retry_displacement = displacement.copy()
                self.clean_retry = bool(
                    np.array_equal(self.retry_displacement, self.committed_displacement)
                    and self.retry_state_digest == self.committed_digest_before_failure
                )
            return super()._solve_load_step(
                model,
                dofs,
                displacement,
                free,
                target_load,
                material_states,
                step,
                load_factor,
                load_increment,
                cached_tangent,
                max_iterations,
                tolerance,
                linear_method,
                min_alpha,
                max_reductions,
                armijo,
                previous_load,
                reference_force_norm,
            )

    solver = RejectingSolver()
    result = solver.solve(model)
    reference_model = _mesh_contact_model(
        1,
        penalty=1.0e5,
        load=load,
        load_path=(0.25, 0.5, 0.75, 1.0),
        max_iterations=80,
        path_dependent=True,
    )
    reference = solve_model(reference_model, enforce_policy=False)
    data = result.to_dict()["solver"]
    reference_data = reference.to_dict()["solver"]
    displacement_error = float(
        np.linalg.norm(result.displacements - reference.displacements)
        / max(np.linalg.norm(reference.displacements), 1.0e-15)
    )
    final_step = data["steps"][-1]
    return {
        "status": "PASS_INTERNAL_ROLLBACK"
        if result.status == "PASS"
        and solver.clean_retry
        and data["rejected_increments"] == 1
        and displacement_error <= COMPARISON_TOLERANCE
        else "FAIL",
        "load": load,
        "reject_on_attempt": reject_on_attempt,
        "attempts": solver.attempts,
        "solver_status": result.status,
        "rejected_increments": data["rejected_increments"],
        "rejection_log": data["rejection_log"],
        "adaptive_load_path": data["load_path"],
        "reference_load_path": reference_data["load_path"],
        "committed_digest_before_failure": solver.committed_digest_before_failure,
        "retry_state_digest": solver.retry_state_digest,
        "committed_displacement_norm": float(np.linalg.norm(solver.committed_displacement)),
        "retry_displacement_norm": float(np.linalg.norm(solver.retry_displacement)),
        "clean_retry": solver.clean_retry,
        "final_displacement_relative_error": displacement_error,
        "final_contact_active": list(final_step.get("contact_active_contacts", [])),
        "final_contact_gap": float(final_step.get("contact_gaps", [0.0])[0]),
        "contact_state_transaction": "N/A - frictionless active set has no persistent state; common material/displacement transaction checked",
        "reference_comparison_tolerance": COMPARISON_TOLERANCE,
    }


def _bare_contact_model(
    *,
    master_nodes: tuple[int, int, int] = (0, 1, 2),
    slave_node: int = 3,
    nodes: list[list[float]] | None = None,
) -> FiniteElementModel:
    model = FiniteElementModel.from_raw(
        nodes=nodes
        or [[0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [0.1, 0.25, 0.25]],
        elements=[],
        materials={},
        fixed_dofs=[],
        loads=[],
        analysis={"type": "nonlinear_static", "method": "newton_raphson", "parameters": {}},
    )
    model.contacts.append(
        FrictionlessContact(name="adversarial", slave_node=slave_node, master_nodes=master_nodes)
    )
    return model


def _failure_observation(callback: Callable[[], Any]) -> dict[str, Any]:
    try:
        value = callback()
    except Exception as exc:  # expected failure contract observation
        reason = getattr(exc, "reason", None)
        return {
            "status": "EXPECTED_FAILURE",
            "converged": False,
            "exception": type(exc).__name__,
            "reason": reason.value if reason is not None else None,
            "message": str(exc),
            "fail_closed": True,
        }
    if isinstance(value, dict) and value.get("status") == "EXPECTED_FAILURE":
        return dict(value)
    return {
        "status": "FAIL",
        "converged": bool(getattr(value, "status", "PASS") == "PASS"),
        "fail_closed": False,
        "message": "Adversarial input did not produce the expected failure.",
    }


def _failure_case(name: str, callback: Callable[[], Any]) -> dict[str, Any]:
    first = _failure_observation(callback)
    second = _failure_observation(callback)
    deterministic = _canonical(first) == _canonical(second)
    expected = first["status"] == second["status"] == "EXPECTED_FAILURE"
    return {
        "case": name,
        "status": "EXPECTED_FAILURE" if expected and deterministic else "FAIL",
        "first": first,
        "second": second,
        "deterministic": deterministic,
        "fail_closed": expected and bool(first.get("fail_closed")) and bool(second.get("fail_closed")),
        "no_silent_pass": not bool(first.get("converged")) and not bool(second.get("converged")),
        "finite": _finite(first) and _finite(second),
        "state_preservation": "N/A - direct validation/assembly failure has no persistent contact state",
    }


def _invalid_penalty() -> dict[str, Any]:
    variants: list[dict[str, Any]] = []
    for penalty in (0.0, -1.0, float("nan")):
        model = _bare_contact_model()
        dofs = model.dof_manager()
        try:
            assemble_penalty_contact(model, dofs, np.zeros(dofs.ndof), penalty=penalty)
        except Exception as exc:
            variants.append(
                {
                    "penalty": repr(penalty),
                    "exception": type(exc).__name__,
                    "message": str(exc),
                    "fail_closed": True,
                }
            )
        else:
            variants.append({"penalty": repr(penalty), "fail_closed": False})
    if all(row["fail_closed"] for row in variants):
        return {"status": "EXPECTED_FAILURE", "converged": False, "fail_closed": True, "variants": variants}
    return {"status": "FAIL", "converged": True, "fail_closed": False, "variants": variants}


def _invalid_geometry() -> Any:
    model = _bare_contact_model(
        nodes=[[0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 2.0, 0.0], [0.1, 0.5, 0.2]]
    )
    dofs = model.dof_manager()
    assemble_penalty_contact(model, dofs, np.zeros(dofs.ndof), penalty=1.0e5)


def _unsupported_route() -> Any:
    model = _mesh_contact_model(1, penalty=1.0e5)
    parameters = {**model.analysis.parameters, "contact_mode": "unsupported_mode"}
    model.analysis = replace(model.analysis, parameters=parameters)
    return solve_model(model, enforce_policy=False)


def _invalid_target() -> Any:
    model = _mesh_contact_model(1, penalty=1.0e5)
    model.contacts[0] = FrictionlessContact(
        name="invalid_target", slave_node=999, master_nodes=(0, 3, 4)
    )
    return solve_model(model, enforce_policy=False)


def _excessive_penetration() -> Any:
    return _expected_penetration_failure()


def _newton_nonconvergence() -> Any:
    model = _mesh_contact_model(1, penalty=1.0e5, max_iterations=1)
    return solve_model(model, enforce_policy=False)


def _run_adversarial() -> dict[str, Any]:
    rows = [
        _failure_case("invalid_penalty", _invalid_penalty),
        _failure_case("invalid_target", _invalid_target),
        _failure_case("invalid_master_geometry", _invalid_geometry),
        _failure_case("unsupported_contact_route", _unsupported_route),
        _failure_case("excessive_penetration", _excessive_penetration),
        _failure_case("newton_max_iterations", _newton_nonconvergence),
    ]
    return {
        "status": "PASS"
        if all(row["status"] == "EXPECTED_FAILURE" for row in rows)
        and all(row["fail_closed"] and row["no_silent_pass"] and row["finite"] for row in rows)
        else "FAIL",
        "cases": rows,
        "no_nan_inf": all(row["finite"] for row in rows),
        "no_silent_pass": all(row["no_silent_pass"] for row in rows),
        "deterministic": all(row["deterministic"] for row in rows),
        "limitations": [
            "Adversarial cases cover the currently accessible bounded penalty path; no external contact failure oracle is claimed.",
            "State preservation is N/A for direct validation failures; common-driver state integrity is covered by the cutback cases.",
        ],
    }
