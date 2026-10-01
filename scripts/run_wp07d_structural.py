"""Guarded WP07-D structural runner.

The historical WP07-D contract deliberately remains preparation-only.  This
runner is separate evidence tooling: it refuses to import a solver or build a
production model until a short-lived Owner authorization record is supplied.
It never changes the historical contract and it never enables a fallback.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prepare_wp07d_structural_vnv import (  # noqa: E402
    BODY_LOWER,
    BODY_UPPER,
    MASTER_NODES,
    TRACTION,
    accumulate_constant_t3_traction,
    generate_structured_tet4_mesh,
)
from scripts.wp07d_execution_binding import (  # noqa: E402
    BINDING_PATH,
    EXPECTED_LEVELS,
    EXPECTED_ROUTES,
    UNAUTHORIZED_EXECUTION,
    _file_sha256,
    coordinate_grading_from_authorization,
    formal_contract_identity,
    mesh_axis_fractions_from_authorization,
    mesh_cell_counts_from_authorization,
    load_binding,
    penalty_integration_from_authorization,
    validate_authorized_execution_source,
    validate_binding,
    validate_formal_requalification_authorization,
)

AUTHORIZATION_TOKEN = "OWNER_AUTHORIZED_WP07D_STRUCTURAL_EXECUTION"


def _nonfinite_json_values(value: Any, *, path: str = "$") -> list[dict[str, str]]:
    """Locate non-finite numeric leaves before strict JSON result serialization."""

    found: list[dict[str, str]] = []
    stack: list[tuple[str, Any]] = [(path, value)]
    while stack:
        current_path, current = stack.pop()
        if isinstance(current, Mapping):
            stack.extend((f"{current_path}.{key}", item) for key, item in current.items())
        elif isinstance(current, (list, tuple)):
            stack.extend((f"{current_path}[{index}]", item) for index, item in enumerate(current))
        elif isinstance(current, (float, np.floating)) and not math.isfinite(float(current)):
            label = "NaN" if math.isnan(float(current)) else ("+Infinity" if current > 0 else "-Infinity")
            found.append({"path": current_path, "value": label})
    return found


def _sanitize_known_nonfinite_result_diagnostics(
    payload: dict[str, Any],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Encode only rejected line-search trial merit sentinels; reject all other non-finites."""

    allowed_path = re.compile(
        r"\$\.solver\.increments\[\d+\]\.diagnostics\.robustness\.line_search\.events"
        r"\[\d+\]\.merit_history\[\d+\]"
    )
    sanitized: list[dict[str, str]] = []
    unresolved: list[dict[str, str]] = []

    def visit(value: Any, path: str = "$") -> Any:
        if isinstance(value, dict):
            for key, item in list(value.items()):
                value[key] = visit(item, f"{path}.{key}")
            return value
        if isinstance(value, list):
            for index, item in enumerate(value):
                value[index] = visit(item, f"{path}[{index}]")
            return value
        if isinstance(value, tuple):
            return [visit(item, f"{path}[{index}]") for index, item in enumerate(value)]
        if isinstance(value, (float, np.floating)) and not math.isfinite(float(value)):
            label = "NaN" if math.isnan(float(value)) else ("+Infinity" if value > 0 else "-Infinity")
            entry = {"path": path, "value": label}
            if allowed_path.fullmatch(path) and label == "+Infinity":
                sanitized.append(entry)
                return {
                    "nonfinite_source_value": label,
                    "classification": "REJECTED_LINE_SEARCH_TRIAL_MERIT_SENTINEL",
                }
            unresolved.append(entry)
        return value

    visit(payload)
    return sanitized, unresolved


def _emit_post_solve_nonlinear_summary(monitor: Any, diagnostics: Mapping[str, Any]) -> dict[str, Any]:
    """Emit truthful per-increment telemetry when this solver API has no live observer hook."""

    increments = diagnostics.get("increments")
    if not isinstance(increments, list):
        return {"mode": "POST_SOLVE_SUMMARY_UNAVAILABLE", "increment_count": 0, "newton_iterations": 0}

    total_iterations = 0
    emitted = 0
    for index, increment in enumerate(increments, start=1):
        if not isinstance(increment, Mapping):
            continue
        step_value = increment.get("increment", index)
        step = step_value if isinstance(step_value, int) and not isinstance(step_value, bool) else index
        iteration_value = increment.get("iterations", 0)
        iterations = (
            iteration_value
            if isinstance(iteration_value, int) and not isinstance(iteration_value, bool)
            else 0
        )
        total_iterations += iterations
        load_factor = increment.get("load_factor")
        residual = increment.get("relative_residual")
        monitor.observe_nonlinear(
            {
                "event": "ITERATION",
                "load_step": step,
                "newton_iteration": iterations,
                "target_load_factor": load_factor,
                "relative_residual": residual,
                "telemetry_sampling": "POST_SOLVE_INCREMENT_SUMMARY",
            },
            source="runner_post_solve_summary",
        )
        monitor.observe_nonlinear(
            {
                "event": "STEP_ACCEPTED",
                "load_step": step,
                "current_load_factor": load_factor,
                "iterations": iterations,
                "relative_residual": residual,
                "telemetry_sampling": "POST_SOLVE_INCREMENT_SUMMARY",
            },
            source="runner_post_solve_summary",
        )
        emitted += 1
    return {
        "mode": "POST_SOLVE_INCREMENT_SUMMARY",
        "increment_count": emitted,
        "newton_iterations": total_iterations,
    }


def _git(*arguments: str) -> str:
    completed = subprocess.run(["git", *arguments], cwd=ROOT, check=True, capture_output=True, text=True)
    return completed.stdout.strip()


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Execution authorization must be a JSON object.")
    return value


def _graded_contact_edge_nodes(nodes: np.ndarray, exponent: float) -> np.ndarray:
    """Refine only the body coordinates near the clamp/contact intersection."""

    if not np.isfinite(exponent) or exponent < 1.0:
        raise ValueError("WP07-D coordinate grading exponent must be finite and at least one.")
    output = np.asarray(nodes, dtype=float).copy()
    if exponent == 1.0:
        return output
    for coordinate, lower, upper in ((0, BODY_LOWER[0], BODY_UPPER[0]), (2, BODY_LOWER[2], BODY_UPPER[2])):
        normalized = (output[:, coordinate] - lower) / (upper - lower)
        output[:, coordinate] = lower + (upper - lower) * normalized**exponent
    return output


def require_authorization(
    path: Path,
    binding: Mapping[str, Any],
    binding_path: Path,
    *,
    route: str,
    mesh: str,
    execution_kind: str = "PRIMARY_PRODUCTION",
) -> dict[str, Any]:
    """Validate a per-run Owner record before importing production solvers."""

    if route not in EXPECTED_ROUTES or mesh not in EXPECTED_LEVELS:
        raise ValueError("Requested route or mesh is outside the frozen WP07-D scope.")
    if not path.is_file():
        raise PermissionError(UNAUTHORIZED_EXECUTION)
    authorization = _load_object(path)
    if authorization.get("token") != binding["authorization"]["token"]:
        raise PermissionError(UNAUTHORIZED_EXECUTION)
    if authorization.get("structural_solves_allowed") is not True:
        raise PermissionError(UNAUTHORIZED_EXECUTION)
    if authorization.get("route") != route or authorization.get("mesh") != mesh:
        raise PermissionError(UNAUTHORIZED_EXECUTION)
    if authorization.get("binding_file_sha256") != _file_sha256(binding_path):
        raise PermissionError("WP07-D authorization does not bind the current execution policy.")
    if authorization.get("authorized_base_sha") != binding["governing"]["authorized_base_sha"]:
        raise PermissionError("WP07-D authorization has the wrong governing base.")
    validate_formal_requalification_authorization(
        authorization,
        binding,
        binding_path,
        route=route,
        mesh=mesh,
        execution_kind=execution_kind,
    )
    penalty_integration_from_authorization(binding, authorization, route=route)
    coordinate_grading_from_authorization(binding, authorization)
    mesh_cell_counts_from_authorization(binding, authorization, level=mesh)
    mesh_axis_fractions_from_authorization(binding, authorization, level=mesh)
    validate_authorized_execution_source(authorization)
    return authorization


def production_model(
    route: str,
    level: str,
    *,
    penalty_integration: str = "nodal",
    coordinate_grading_exponent: float = 1.0,
    mesh_cell_counts: tuple[int, int, int] | None = None,
    mesh_axis_fractions: tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]] | None = None,
) -> Any:
    """Create one frozen production model after the execution gate has opened."""

    if route not in EXPECTED_ROUTES or level not in EXPECTED_LEVELS:
        raise ValueError("Unknown frozen WP07-D route or mesh level.")
    # Deliberately local: contact/solver imports cannot occur on an
    # unauthorized invocation of this module.
    from solveur.core.model import FiniteElementModel

    mesh = generate_structured_tet4_mesh(
        level, cell_counts=mesh_cell_counts, axis_fractions=mesh_axis_fractions
    )
    body_nodes = _graded_contact_edge_nodes(mesh.nodes, coordinate_grading_exponent)
    master_offset = len(body_nodes)
    nodes = np.vstack((body_nodes, MASTER_NODES))
    nodal_forces = accumulate_constant_t3_traction(body_nodes, mesh.top_faces, TRACTION)
    fixed = [
        {"node": int(index), "dofs": ["UX", "UY", "UZ"]}
        for index, point in enumerate(body_nodes)
        if np.isclose(point[0], BODY_LOWER[0], rtol=0.0, atol=1.0e-14)
    ]
    fixed.extend({"node": master_offset + index, "dofs": ["UX", "UY", "UZ"]} for index in range(3))
    loads = [
        {"node": int(node), "dof": dof, "value": float(force[component])}
        for node, force in enumerate(nodal_forces)
        for component, dof in enumerate(("UX", "UY", "UZ"))
        if force[component] != 0.0
    ]
    parameters: dict[str, Any] = {"contact_search_mode": "initial"}
    if route == "PENALTY":
        if penalty_integration not in {"nodal", "surface_lumped"}:
            raise ValueError("Unknown WP07-D penalty integration mode.")
        parameters.update(
            {
                "contact_mode": "penalty",
                "contact_penalty": 1.0e8,
                "load_increments": 8,
                "adaptive_load_steps": False,
                "tolerance": 1.0e-10,
                "max_iterations": 100,
                "experimental_linear_solver": "minres",
                "experimental_linear_preconditioner": "jacobi",
                "experimental_linear_rtol": 1.0e-11,
                "experimental_linear_atol": 1.0e-14,
                "experimental_linear_maxiter": 10000,
                "experimental_linear_direct_fallback": False,
                "experimental_line_search": "existing",
                "experimental_floor_aware_termination": True,
                "contact_penalty_integration": penalty_integration,
            }
        )
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": "TET4", "nodes": list(element), "material": "elastic"} for element in mesh.elements],
        materials={"elastic": {"type": "isotropic_3d", "E": 1.0e6, "nu": 0.3}},
        fixed_dofs=fixed,
        loads=loads,
        contacts=[
            {
                "name": "wp07d_initial_master_plane",
                "slave_nodes": list(mesh.slave_nodes),
                "slave_patch_faces": [list(face) for face in mesh.bottom_faces],
                "master_nodes": [master_offset, master_offset + 1, master_offset + 2],
                "friction_coefficient": 0.0,
            }
        ],
        analysis={
            "type": "linear_static" if route == "ACTIVE_SET" else "geometric_nonlinear_static",
            "method": "direct" if route == "ACTIVE_SET" else "newton_raphson",
            "parameters": parameters,
        },
    )


def _external_vector(model: Any, dofs: Any) -> np.ndarray:
    values = np.zeros(dofs.ndof, dtype=float)
    for load in model.loads:
        values[dofs.index(load.node, load.dof)] += float(load.value)
    return values


def _fixed_indices(model: Any, dofs: Any) -> np.ndarray:
    return np.unique(
        [dofs.index(condition.node, name) for condition in model.fixed_dofs for name in condition.dofs]
    )


def _deformed_position(model: Any, dofs: Any, displacement: np.ndarray, node: int) -> np.ndarray:
    position = np.asarray(model.nodes[int(node)], dtype=float).copy()
    for component, name in enumerate(("UX", "UY", "UZ")):
        position[component] += float(displacement[dofs.index(int(node), name)])
    return position


def _deformed_positions(model: Any, dofs: Any, displacement: np.ndarray) -> np.ndarray:
    """Return current positions without changing the frozen model geometry."""

    values = np.asarray(displacement, dtype=float)
    if values.shape != (dofs.ndof,):
        raise ValueError("Displacement vector has an incompatible size.")
    return np.asarray(model.nodes, dtype=float) + values.reshape((model.node_count, 3))


def _json_safe(value: Any) -> Any:
    """Convert exception diagnostics to a strict-JSON-compatible value."""

    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if np.isfinite(value) else str(value)
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return str(value)


def failure_payload(route: str, mesh: str, error: BaseException, *, execution_sha: str) -> dict[str, Any]:
    """Build fail-closed evidence without discarding numerical diagnostics."""

    raw_reason = getattr(error, "reason", None)
    reason = getattr(raw_reason, "value", raw_reason)
    raw_diagnostics = getattr(error, "diagnostics", {})
    diagnostics = raw_diagnostics if isinstance(raw_diagnostics, Mapping) else {"raw": raw_diagnostics}
    return {
        "schema_version": 1,
        "status": "FAIL_CLOSED",
        "route": route,
        "mesh": mesh,
        "execution_sha": execution_sha,
        "terminal_classification": "STRUCTURAL_SOLVE_EXCEPTION",
        "exception_type": type(error).__name__,
        "exception_message": str(error),
        "reason": _json_safe(reason),
        "diagnostics": _json_safe(diagnostics),
        "production_mechanics_changed": None,
        "thresholds_changed": False,
        "fallback_used": False,
        "reference": "NOT_RUN_BY_THIS_COMMAND",
        "replay": "NOT_RUN",
    }


def _resultant_and_moment(
    dofs: Any,
    vector: np.ndarray,
    positions: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Evaluate a nodal force vector at an explicit coordinate configuration."""

    values = np.asarray(vector, dtype=float)
    coordinates = np.asarray(positions, dtype=float)
    if values.shape != (dofs.ndof,) or coordinates.ndim != 2 or coordinates.shape[1] != 3:
        raise ValueError("Force vector and coordinate configuration are incompatible.")
    forces = values.reshape((coordinates.shape[0], 3))
    return np.sum(forces, axis=0), np.sum(np.cross(coordinates, forces), axis=0)


def _body_node_count(model: Any) -> int:
    """Return the body-node prefix; master nodes have no body elements."""

    return 1 + max(int(node) for element in model.elements for node in element.nodes)


def _body_support_vector(model: Any, dofs: Any, support: np.ndarray) -> np.ndarray:
    """Keep only reactions on the deformable body clamp, excluding fixed masters."""

    body_count = _body_node_count(model)
    output = np.zeros_like(np.asarray(support, dtype=float))
    body_dofs = np.arange(dofs.ndof, dtype=int).reshape((model.node_count, 3))[:body_count]
    output[body_dofs.reshape(-1)] = np.asarray(support, dtype=float)[body_dofs.reshape(-1)]
    return output


def _body_contact_force_vector(
    model: Any,
    dofs: Any,
    displacement: np.ndarray,
    route: str,
    details: Mapping[str, Any],
) -> tuple[np.ndarray, float, float, str | None]:
    """Recover body-side contact forces without changing the solve."""

    forces = np.zeros(dofs.ndof, dtype=float)
    maximum_penetration = 0.0
    contact_energy: float | None = None
    if route == "ACTIVE_SET":
        rows = details.get("contacts", [])
        if not isinstance(rows, list):
            raise ValueError("Active-set contact details must contain contact rows.")
        for row in rows:
            if not isinstance(row, Mapping) or not bool(row.get("active", False)):
                continue
            node = int(row["slave_node"])
            pressure = float(row["pressure"])
            normal = np.asarray(row["normal"], dtype=float)
            force = pressure * normal
            for component, name in enumerate(("UX", "UY", "UZ")):
                forces[dofs.index(node, name)] += force[component]
            maximum_penetration = max(maximum_penetration, max(-float(row["gap"]), 0.0))
        energy_status = "NOT_APPLICABLE_ACTIVE_SET"
    else:
        from solveur.contact.support import _expanded_contacts

        gaps = details.get("gaps", [])
        normals = details.get("normals", [])
        if not isinstance(gaps, (list, tuple)) or not isinstance(normals, (list, tuple)):
            raise ValueError("Penalty contact details must contain gaps and normals.")
        contacts = _expanded_contacts(model.contacts)
        effective_penalties = details.get("effective_penalties")
        if not isinstance(effective_penalties, (list, tuple)) or len(effective_penalties) != len(contacts):
            raise ValueError("Penalty contact details lack effective per-slave penalties.")
        contact_energy_value = 0.0
        for gap, normal, contact, effective_penalty in zip(
            gaps, normals, contacts, effective_penalties, strict=True
        ):
            local_penalty = float(effective_penalty)
            if not np.isfinite(local_penalty) or local_penalty <= 0.0:
                raise ValueError("Penalty contact details contain an invalid per-slave penalty.")
            penetration = max(-float(gap), 0.0)
            maximum_penetration = max(maximum_penetration, penetration)
            contact_energy_value += 0.5 * local_penalty * penetration * penetration
            force = local_penalty * penetration * np.asarray(normal, dtype=float)
            for component, name in enumerate(("UX", "UY", "UZ")):
                forces[dofs.index(int(contact.slave_node), name)] += force[component]
        contact_energy = float(contact_energy_value)
        energy_status = None
    return forces, float(maximum_penetration), contact_energy or 0.0, energy_status


def _body_contact_forces(
    model: Any,
    dofs: Any,
    displacement: np.ndarray,
    route: str,
    details: Mapping[str, Any],
) -> tuple[np.ndarray, np.ndarray, float, float, str | None]:
    """Recover body-side contact observables without changing the solve."""

    forces, maximum_penetration, contact_energy, energy_status = _body_contact_force_vector(
        model, dofs, displacement, route, details
    )
    current_positions = _deformed_positions(model, dofs, displacement)
    resultant, moment = _resultant_and_moment(dofs, forces, current_positions)
    return resultant, moment, float(maximum_penetration), contact_energy or 0.0, energy_status


def _production_observables(model: Any, dofs: Any, displacement: np.ndarray, route: str, result: Mapping[str, Any]) -> dict[str, Any]:
    details = result.get("solver", {}).get("contact", {})
    if not isinstance(details, Mapping):
        raise ValueError("Production result lacks contact details.")
    contact_force_vector, maximum_penetration, contact_energy, energy_status = _body_contact_force_vector(
        model, dofs, displacement, route, details
    )
    reference_positions = np.asarray(model.nodes, dtype=float)
    current_positions = _deformed_positions(model, dofs, displacement)
    contact_resultant, contact_moment = _resultant_and_moment(dofs, contact_force_vector, current_positions)
    _, contact_moment_reference = _resultant_and_moment(dofs, contact_force_vector, reference_positions)
    if route == "ACTIVE_SET":
        equilibrium = result.get("audit", {}).get("equilibrium", {})
        if not isinstance(equilibrium, Mapping):
            raise ValueError("Active-set production result lacks equilibrium audit.")
        reaction_resultant = np.asarray(equilibrium["reaction_resultant"], dtype=float)
        reaction_moment = np.asarray(equilibrium["reaction_moment_about_origin"], dtype=float)
        external_moment = np.asarray(equilibrium["external_moment_about_origin"], dtype=float)
        force_error = float(equilibrium["force_balance_relative_error"])
        moment_error = float(equilibrium["moment_balance_relative_error"])
        free_error = float(equilibrium["free_relative_residual"])
        strain_energy = float(equilibrium["secant_internal_energy"])
    else:
        from solveur.contact.solver import assemble_penalty_contact
        from solveur.core.assembly.geometric import build_total_lagrangian_assembly

        external = _external_vector(model, dofs)
        fixed = _fixed_indices(model, dofs)
        material_assembly = build_total_lagrangian_assembly(model)
        material_internal, _ = material_assembly.assemble(displacement, tangent_required=False)
        contact_internal, _, final_details = assemble_penalty_contact(
            model,
            dofs,
            displacement,
            penalty=float(details["penalty"]),
        )
        residual = np.asarray(material_internal + contact_internal - external, dtype=float)
        support = np.zeros_like(residual)
        support[fixed] = residual[fixed]
        body_support = _body_support_vector(model, dofs, support)
        reaction_vector = body_support + contact_force_vector
        reaction_resultant, reaction_moment = _resultant_and_moment(dofs, reaction_vector, current_positions)
        _, reaction_moment_reference = _resultant_and_moment(dofs, reaction_vector, reference_positions)
        external_resultant, external_moment = _resultant_and_moment(dofs, external, current_positions)
        _, external_moment_reference = _resultant_and_moment(dofs, external, reference_positions)
        force_scale = max(float(np.linalg.norm(external_resultant)), float(np.linalg.norm(reaction_resultant)), 1.0)
        moment_scale = max(float(np.linalg.norm(external_moment)), float(np.linalg.norm(reaction_moment)), 1.0)
        force_error = float(np.linalg.norm(external_resultant + reaction_resultant) / force_scale)
        moment_error = float(np.linalg.norm(external_moment + reaction_moment) / moment_scale)
        reference_moment_scale = max(
            float(np.linalg.norm(external_moment_reference)),
            float(np.linalg.norm(reaction_moment_reference)),
            1.0,
        )
        reference_moment_error = float(
            np.linalg.norm(external_moment_reference + reaction_moment_reference) / reference_moment_scale
        )
        free = np.setdiff1d(np.arange(dofs.ndof, dtype=int), fixed)
        free_error = float(np.linalg.norm(residual[free]) / max(float(np.linalg.norm(external[free])), 1.0))
        strain_energy = float(material_assembly.strain_energy(displacement))
        details = final_details
    if route == "ACTIVE_SET":
        reaction_moment_reference = reaction_moment
        external_moment_reference = np.asarray(
            result.get("audit", {}).get("external_moment_about_origin", [0.0, 0.0, 0.0]), dtype=float
        )
        reference_moment_error = moment_error
    return {
        "schema_version": 2,
        "source": "runner_postprocessed_from_frozen_final_state",
        "reaction_resultant": {"vector": reaction_resultant.tolist(), "norm": float(np.linalg.norm(reaction_resultant))},
        "reaction_moment_about_origin": {"vector": reaction_moment.tolist(), "norm": float(np.linalg.norm(reaction_moment))},
        "reaction_moment_about_reference_origin": {"vector": reaction_moment_reference.tolist(), "norm": float(np.linalg.norm(reaction_moment_reference))},
        "contact_resultant_body_side": {"vector": contact_resultant.tolist(), "norm": float(np.linalg.norm(contact_resultant))},
        "contact_moment_body_side_about_origin": {"vector": contact_moment.tolist(), "norm": float(np.linalg.norm(contact_moment))},
        "contact_moment_body_side_about_reference_origin": {"vector": contact_moment_reference.tolist(), "norm": float(np.linalg.norm(contact_moment_reference))},
        "external_moment_about_origin": {"vector": np.asarray(external_moment, dtype=float).tolist(), "norm": float(np.linalg.norm(external_moment))},
        "external_moment_about_reference_origin": {"vector": np.asarray(external_moment_reference, dtype=float).tolist(), "norm": float(np.linalg.norm(external_moment_reference))},
        "maximum_penetration": maximum_penetration,
        "contact_energy": contact_energy if energy_status is None else None,
        "contact_energy_status": energy_status or "COMPUTED_FIXED_NORMAL_PENALTY_POTENTIAL",
        "strain_energy": strain_energy,
        "equilibrium": {
            "force_balance_relative_error": force_error,
            "moment_balance_relative_error": moment_error,
            "free_residual_relative": free_error,
            "coordinate_configuration": "CURRENT_DEFORMED_BODY" if route == "PENALTY" else "REFERENCE",
            "reaction_definition": "BODY_CLAMP_PLUS_BODY_SIDE_CONTACT" if route == "PENALTY" else "SOLVER_AUDIT_REACTION",
            "reference_configuration_moment_balance_relative_error": reference_moment_error,
            "reference_configuration_moment_limit_unchanged": True,
        },
        "finite": True,
    }


def execute(
    route: str,
    mesh: str,
    authorization_path: Path,
    output: Path,
    *,
    binding_path: Path = BINDING_PATH,
    heartbeat_interval: float = 5.0,
    execution_kind: str = "PRIMARY_PRODUCTION",
) -> dict[str, Any]:
    """Execute exactly one authorized structural case and flush raw evidence."""

    binding = load_binding(binding_path)
    validate_binding(binding)
    authorization = require_authorization(
        authorization_path,
        binding,
        binding_path,
        route=route,
        mesh=mesh,
        execution_kind=execution_kind,
    )
    penalty_integration = penalty_integration_from_authorization(binding, authorization, route=route)
    coordinate_grading_exponent = coordinate_grading_from_authorization(binding, authorization)
    mesh_cell_counts = mesh_cell_counts_from_authorization(binding, authorization, level=mesh)
    mesh_axis_fractions = mesh_axis_fractions_from_authorization(binding, authorization, level=mesh)
    from scripts.wp07d_run_telemetry import WP07DRunMonitor
    from solveur.core.telemetry.events import EventStatus, EventType

    analysis_type = "linear_static" if route == "ACTIVE_SET" else "geometric_nonlinear_static"
    with WP07DRunMonitor(
        output,
        route=route,
        mesh=mesh,
        analysis_type=analysis_type,
        heartbeat_interval=heartbeat_interval,
    ) as monitor:
        initial_progress: dict[str, Any] = {"phase": "MODEL_GENERATION"}
        if route == "PENALTY":
            initial_progress["total_steps"] = 8
        monitor.set_progress(**initial_progress)
        model = production_model(
            route,
            mesh,
            penalty_integration=penalty_integration,
            coordinate_grading_exponent=coordinate_grading_exponent,
            mesh_cell_counts=mesh_cell_counts,
            mesh_axis_fractions=mesh_axis_fractions,
        )
        dofs = model.dof_manager()
        if route == "ACTIVE_SET":
            from solveur.core.solvers.static import LinearStaticSolver

            result = LinearStaticSolver().solve(
                model,
                detail_level="full",
                telemetry=monitor.emitter,
            )
        else:
            from solveur.core.analyses.geometric_nonlinear import GeometricNonlinearStaticSolver

            monitor.emit(
                EventType.MESH_READY,
                status=EventStatus.COMPLETED,
                metrics={
                    "nodes": model.node_count,
                    "elements": len(model.elements),
                    "dofs": dofs.ndof,
                    "mesh_status": "VALIDATED_BY_FROZEN_RUNNER",
                },
            )
            monitor.emit(
                EventType.ASSEMBLY_START,
                status=EventStatus.STARTED,
                metrics={
                    "nodes": model.node_count,
                    "elements": len(model.elements),
                    "dofs": dofs.ndof,
                },
            )
            monitor.set_progress(phase="SOLVE", telemetry_mode="HEARTBEAT_WITH_POST_SOLVE_INCREMENT_SUMMARY")
            result = GeometricNonlinearStaticSolver().solve(model)
            telemetry_summary = _emit_post_solve_nonlinear_summary(monitor, result.solver)
        monitor.set_progress(phase="POSTPROCESSING")
        raw_path = output / "result.json"
        payload = result.to_dict()
        payload["wp07d_observables"] = _production_observables(
            model, dofs, np.asarray(result.displacements, dtype=float), route, payload
        )
        payload["wp07d_mesh"] = {
            "cell_counts": list(mesh_cell_counts) if mesh_cell_counts is not None else None,
            "axis_fractions": (
                {axis: list(values) for axis, values in zip(("x", "y", "z"), mesh_axis_fractions, strict=True)}
                if mesh_axis_fractions is not None
                else None
            ),
            "coordinate_grading_exponent": coordinate_grading_exponent,
        }
        contract_identity = formal_contract_identity(binding)
        if contract_identity is not None:
            payload["wp07d_contract_provenance"] = contract_identity
            payload["wp07d_contract_provenance"]["owner_decision"] = binding["owner_decision"]
        payload["wp07d_execution_kind"] = execution_kind
        if route == "PENALTY":
            payload["wp07d_runner_telemetry"] = telemetry_summary
        monitor.set_progress(phase="RESULT_ARCHIVE")
        sanitized_values, unresolved_values = _sanitize_known_nonfinite_result_diagnostics(payload)
        serialization_diagnostic: dict[str, Any] | None = None
        if sanitized_values or unresolved_values:
            diagnostic = {
                "schema_version": 1,
                "status": (
                    "FAIL_CLOSED_UNEXPECTED_NONFINITE_RESULT"
                    if unresolved_values
                    else "PASS_TOOLING_ONLY_KNOWN_LINE_SEARCH_SENTINEL"
                ),
                "route": route,
                "mesh": mesh,
                "execution_sha": _git("rev-parse", "HEAD"),
                "sanitized_count": len(sanitized_values),
                "unresolved_count": len(unresolved_values),
                "sanitized_values": sanitized_values[:256],
                "unresolved_values": unresolved_values[:256],
                "truncated": len(sanitized_values) > 256 or len(unresolved_values) > 256,
                "sanitization_scope": "rejected line-search trial merit-history sentinel only",
                "solver_mechanics_changed": False,
                "thresholds_changed": False,
            }
            serialization_path = output / "serialization_diagnostic.json"
            serialization_path.write_text(
                json.dumps(diagnostic, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
            )
            serialization_diagnostic = diagnostic
            if unresolved_values:
                raise ValueError(
                    f"Unexpected non-finite result fields prevent archival: {len(unresolved_values)} field(s); "
                    "see serialization_diagnostic.json."
                )
            payload["serialization_diagnostic"] = diagnostic
        raw_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    report = {
        "schema_version": 1,
        "status": "COMPLETED",
        "route": route,
        "mesh": mesh,
        "authorized_base_sha": binding["governing"]["authorized_base_sha"],
        "execution_sha": _git("rev-parse", "HEAD"),
        "binding_path": str(binding_path.relative_to(ROOT)).replace("\\", "/"),
        "authorization_path": str(authorization_path.relative_to(ROOT)).replace("\\", "/"),
        "binding_file_sha256": _file_sha256(binding_path),
        "authorization_file_sha256": _file_sha256(authorization_path),
        "authorization_token": authorization["token"],
        "execution_kind": execution_kind,
        "penalty_integration": penalty_integration,
        "coordinate_grading_exponent": coordinate_grading_exponent,
        "mesh_cell_counts": list(mesh_cell_counts) if mesh_cell_counts is not None else None,
        "mesh_axis_fractions": (
            {axis: list(values) for axis, values in zip(("x", "y", "z"), mesh_axis_fractions, strict=True)}
            if mesh_axis_fractions is not None
            else None
        ),
        "result_file": "result.json",
        "result_file_sha256": _file_sha256(raw_path),
        "telemetry_file": "telemetry.jsonl",
        "telemetry_file_sha256": _file_sha256(output / "telemetry.jsonl"),
        "telemetry_status": monitor.telemetry_status,
        "telemetry_sampling_mode": (
            "LIVE_SOLVER_EVENTS" if route == "ACTIVE_SET" else "HEARTBEAT_WITH_POST_SOLVE_INCREMENT_SUMMARY"
        ),
        "progress_file": "progress.json",
        "progress_file_sha256": _file_sha256(output / "progress.json"),
        "heartbeat_interval_seconds": heartbeat_interval,
        "production_mechanics_changed": bool(binding["invariants"]["production_mechanics_changed"]),
        "thresholds_changed": False,
    }
    contract_identity = formal_contract_identity(binding)
    if contract_identity is not None:
        report["formal_contract_provenance"] = contract_identity
        report["owner_decision"] = binding["owner_decision"]
        report["source_contains_wp07_candidate_changes_since_governing_base"] = binding[
            "source_lineage_disclosure"
        ]["source_contains_wp07_candidate_changes_since_governing_base"]
    diagnostic_path = output / "serialization_diagnostic.json"
    if diagnostic_path.is_file():
        report["serialization_diagnostic_file"] = diagnostic_path.name
        report["serialization_diagnostic_file_sha256"] = _file_sha256(diagnostic_path)
        report["serialization_diagnostic_status"] = serialization_diagnostic["status"] if serialization_diagnostic else None
    (output / "run.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--route", choices=EXPECTED_ROUTES, required=True)
    parser.add_argument("--mesh", choices=EXPECTED_LEVELS, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--binding", type=Path, default=BINDING_PATH)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--heartbeat-interval", type=float, default=5.0)
    parser.add_argument(
        "--execution-kind",
        choices=("PRIMARY_PRODUCTION", "REPLAY"),
        default="PRIMARY_PRODUCTION",
    )
    args = parser.parse_args(argv)
    args.binding = args.binding.resolve()
    args.authorization = args.authorization.resolve()
    args.output = args.output.resolve()
    try:
        print(
            json.dumps(
                execute(
                    args.route,
                    args.mesh,
                    args.authorization,
                    args.output,
                    binding_path=args.binding,
                    heartbeat_interval=args.heartbeat_interval,
                    execution_kind=args.execution_kind,
                ),
                indent=2,
                sort_keys=True,
            )
        )
    except (OSError, ValueError, PermissionError, subprocess.CalledProcessError) as error:
        print(f"WP07-D structural execution blocked or failed closed: {error}", file=sys.stderr)
        return 2
    except Exception as error:  # noqa: BLE001 - terminal evidence must survive solver exceptions.
        args.output.mkdir(parents=True, exist_ok=True)
        failure = failure_payload(
            args.route,
            args.mesh,
            error,
            execution_sha=_git("rev-parse", "HEAD"),
        )
        binding = load_binding(args.binding)
        failure.update(
            {
                "execution_kind": args.execution_kind,
                "binding_path": str(args.binding.relative_to(ROOT)).replace("\\", "/"),
                "binding_file_sha256": _file_sha256(args.binding),
                "authorization_path": str(args.authorization.relative_to(ROOT)).replace("\\", "/"),
                "authorization_file_sha256": _file_sha256(args.authorization)
                if args.authorization.is_file()
                else None,
                "formal_contract_provenance": formal_contract_identity(binding),
                "owner_decision": binding.get("owner_decision"),
            }
        )
        (args.output / "failure.json").write_text(
            json.dumps(failure, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
        )
        print(json.dumps(failure, indent=2, sort_keys=True), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
