"""Fail-closed analysis for the fresh WP07-D formal rebind R1 campaign."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prepare_wp07d_structural_vnv import (  # noqa: E402
    BODY_LOWER,
    BODY_UPPER,
    generate_structured_tet4_mesh,
)
from scripts.wp07d_execution_binding import (  # noqa: E402
    EXPECTED_LEVELS,
    EXPECTED_ROUTES,
    FORMAL_REBIND_R1_BINDING_PATH,
    _file_sha256,
    formal_contract_identity,
    load_binding,
    load_contract_for_binding,
    validate_binding,
)

ARTIFACT_ROOT = Path("qualification/0_2_9/wp07d_formal_rebind_r1")
RUN_ROOT = ARTIFACT_ROOT / "runs"
AUTH_ROOT = ARTIFACT_ROOT / "authorizations"
PRE_REPLAY_REPORT = ARTIFACT_ROOT / "replay_authorization_gate.json"
FINAL_REPORT = ARTIFACT_ROOT / "analysis_final.json"
REPLAY_GATE_PATH = PRE_REPLAY_REPORT
ACTIVE_BINDING_PATH = FORMAL_REBIND_R1_BINDING_PATH


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object at {path}.")
    return value


def _git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _relative_delta(left: float, right: float, scale: float = 1.0) -> float:
    floor = max(1.0e-14, 64.0 * float(np.finfo(float).eps) * float(scale))
    if not math.isfinite(left) or not math.isfinite(right):
        raise ValueError("A compared observable is non-finite.")
    return abs(right - left) / max(abs(left), abs(right), floor)


def _vector_norm(value: Any) -> float:
    vector = np.asarray(value, dtype=float)
    if vector.ndim != 1 or not np.all(np.isfinite(vector)):
        raise ValueError("A required vector observable is missing or non-finite.")
    return float(np.linalg.norm(vector))


def _mesh_and_nodes(binding: Mapping[str, Any], level: str) -> tuple[Any, np.ndarray]:
    definition = binding["mesh_definition"]
    raw_counts = definition["cell_counts_by_level"][level]
    if not isinstance(raw_counts, (list, tuple)) or len(raw_counts) != 3:
        raise ValueError(f"WP07-D {level} cell counts must have exactly three entries.")
    counts = (int(raw_counts[0]), int(raw_counts[1]), int(raw_counts[2]))
    raw_axes = definition.get("axis_fractions_by_level", {}).get(level)
    axes: tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]] | None = None
    if isinstance(raw_axes, Mapping):
        axes = (
            tuple(float(value) for value in raw_axes["x"]),
            tuple(float(value) for value in raw_axes["y"]),
            tuple(float(value) for value in raw_axes["z"]),
        )
    mesh = generate_structured_tet4_mesh(level, cell_counts=counts, axis_fractions=axes)
    nodes = np.asarray(mesh.nodes, dtype=float).copy()
    exponent = float(definition["coordinate_grading_exponent"])
    for axis in (0, 2):
        lower = float(BODY_LOWER[axis])
        upper = float(BODY_UPPER[axis])
        normalized = (nodes[:, axis] - lower) / (upper - lower)
        nodes[:, axis] = lower + (upper - lower) * normalized**exponent
    return mesh, nodes


def _selected_displacement(result: Mapping[str, Any], nodes: np.ndarray) -> float:
    top = np.flatnonzero(np.isclose(nodes[:, 2], BODY_UPPER[2], rtol=0.0, atol=1.0e-14))
    raw = result.get("displacements")
    if not isinstance(raw, list):
        raise ValueError("Result has no displacement field.")
    if raw and isinstance(raw[0], Mapping):
        by_node = {int(row["node"]): row["dofs"] for row in raw if isinstance(row, Mapping)}
        values = [float(by_node[int(index)]["UZ"]) for index in top]
    else:
        vector = np.asarray(raw, dtype=float)
        if vector.ndim != 1 or vector.size < 3 * len(nodes):
            raise ValueError("Result displacement vector is incompatible with the frozen mesh.")
        values = vector.reshape((-1, 3))[: len(nodes), 2][top].tolist()
    if not values or not np.all(np.isfinite(values)):
        raise ValueError("Selected top-face displacement is missing or non-finite.")
    return float(np.mean(np.abs(values)))


def _contact_region(mesh: Any, nodes: np.ndarray, active_nodes: list[int]) -> float:
    tributary: np.ndarray = np.zeros(len(nodes), dtype=float)
    total_area = 0.0
    for face in mesh.bottom_faces:
        xyz = nodes[list(face)]
        area = 0.5 * float(np.linalg.norm(np.cross(xyz[1] - xyz[0], xyz[2] - xyz[0])))
        total_area += area
        tributary[list(face)] += area / 3.0
    if total_area <= 0.0 or any(node < 0 or node >= len(nodes) for node in active_nodes):
        raise ValueError("Active contact region cannot be evaluated on the frozen mesh.")
    return float(math.fsum(float(tributary[node]) for node in sorted(set(active_nodes))) / total_area)


def _safe_vector_delta(left: Any, right: Any, scale: float) -> float:
    return _relative_delta(_vector_norm(left), _vector_norm(right), scale)


def _active_identity_metrics(
    route: str,
    result: Mapping[str, Any],
    nodes: np.ndarray,
    *,
    char_length: float,
    char_force: float,
    initial_gap: float,
    contact_rows: list[Mapping[str, Any]] | None = None,
) -> dict[str, float]:
    if route != "ACTIVE_SET":
        return {}
    if contact_rows is not None:
        active = [row for row in contact_rows if row.get("active") is True]
        open_rows = [row for row in contact_rows if row.get("active") is False]
        if not contact_rows or any(
            "gap" not in row
            or "pressure" not in row
            or "complementarity" not in row
            or not all(math.isfinite(float(row[key])) for key in ("gap", "pressure", "complementarity"))
            for row in contact_rows
        ):
            raise ValueError("Production active-set raw contact rows are incomplete.")
        active_set = {int(row["slave_node"]) for row in active}
        max_gap = max((abs(float(row["gap"])) for row in active), default=0.0)
        complementarity = max((abs(float(row["complementarity"])) for row in contact_rows), default=0.0)
        open_force = max((abs(float(row["pressure"])) for row in open_rows), default=0.0)
        wrong_sign = max((max(-float(row["pressure"]), 0.0) for row in contact_rows), default=0.0)
        clamped = [node for node in active_set if abs(float(nodes[node, 0] - BODY_LOWER[0])) <= 1.0e-14]
        if clamped:
            raise ValueError("Active-set contact includes a node on the fixed clamp.")
        return {
            "normalized_gap": max_gap / char_length,
            "normalized_complementarity": complementarity / (char_length * char_force),
            "open_contact_force": open_force / char_force,
            "wrong_sign_pressure": wrong_sign / char_force,
        }

    reference_active_nodes = [int(node) for node in result.get("active_slave_nodes", [])]
    displacements = np.asarray(result.get("displacements"), dtype=float)
    contact_forces = np.asarray(result.get("contact_nodal_forces"), dtype=float)
    if (
        displacements.ndim != 1
        or displacements.size != 3 * len(nodes)
        or not np.all(np.isfinite(displacements))
    ):
        raise ValueError("Independent active-set displacement vector is incompatible with the mesh.")
    if contact_forces.shape != (len(nodes), 3) or not np.all(np.isfinite(contact_forces)):
        raise ValueError("Independent active-set contact-force field is incompatible with the mesh.")
    active_set = set(reference_active_nodes)
    all_slave_nodes = [int(node) for node in result.get("slave_nodes", [])]
    # The independent result predates explicit slave-node serialization; the frozen mesh defines them.
    if not all_slave_nodes:
        all_slave_nodes = [int(node) for node in _bottom_slave_nodes(nodes)]
    gaps = {node: initial_gap + float(displacements[3 * node + 2]) for node in all_slave_nodes}
    max_gap = max((abs(gaps[node]) for node in reference_active_nodes), default=0.0)
    max_comp = max((abs(gaps[node] * float(contact_forces[node, 2])) for node in all_slave_nodes), default=0.0)
    open_force = max(
        (float(np.linalg.norm(contact_forces[node])) for node in all_slave_nodes if node not in active_set),
        default=0.0,
    )
    wrong_sign = max((-float(contact_forces[node, 2]) for node in all_slave_nodes), default=0.0)
    clamped = [node for node in reference_active_nodes if abs(float(nodes[node, 0] - BODY_LOWER[0])) <= 1.0e-14]
    if clamped:
        raise ValueError("Independent active-set contact includes a node on the fixed clamp.")
    return {
        "normalized_gap": max_gap / char_length,
        "normalized_complementarity": max_comp / (char_length * char_force),
        "open_contact_force": open_force / char_force,
        "wrong_sign_pressure": max(wrong_sign, 0.0) / char_force,
    }


def _bottom_slave_nodes(nodes: np.ndarray) -> list[int]:
    """Recover fixed-plane slave nodes from the exact bottom face geometry."""

    return np.flatnonzero(np.isclose(nodes[:, 2], BODY_LOWER[2], rtol=0.0, atol=1.0e-14)).tolist()


def _equilibrium_metrics(result: Mapping[str, Any]) -> dict[str, float]:
    observables = result.get("wp07d_observables")
    if not isinstance(observables, Mapping):
        raise ValueError("Result lacks the frozen WP07-D observable record.")
    equilibrium = observables.get("equilibrium")
    if not isinstance(equilibrium, Mapping):
        raise ValueError("Result lacks force/moment equilibrium observables.")
    return {
        "force_equilibrium_relative": float(equilibrium["force_balance_relative_error"]),
        "moment_equilibrium_relative": float(equilibrium["moment_balance_relative_error"]),
    }


def _metrics(
    route: str,
    level: str,
    result: Mapping[str, Any],
    binding: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    mesh, nodes = _mesh_and_nodes(binding, level)
    observables = result.get("wp07d_observables")
    if not isinstance(observables, Mapping):
        raise ValueError("Result lacks frozen WP07-D observables.")
    metrics: dict[str, Any] = {
        "selected_displacement": _selected_displacement(result, nodes),
        "reaction_resultant": _vector_norm(observables["reaction_resultant"]["vector"]),
        "reaction_moment": _vector_norm(observables["reaction_moment_about_origin"]["vector"]),
        "contact_resultant": _vector_norm(observables["contact_resultant_body_side"]["vector"]),
        **_equilibrium_metrics(result),
    }
    char_length = float(contract["scales"]["L_char"])
    char_force = float(contract["scales"]["F_char"])
    initial_gap = float(contract["scales"]["initial_gap_scale"])
    if route == "ACTIVE_SET":
        if "solver" in result:
            contact = result.get("solver", {}).get("contact", {})
            rows = contact.get("contacts") if isinstance(contact, Mapping) else None
            if not isinstance(rows, list):
                raise ValueError("Production active-set result omits raw contact rows.")
            active_nodes = [int(row["slave_node"]) for row in rows if row.get("active") is True]
            if int(contact.get("active_contact_count", -1)) != len(active_nodes):
                raise ValueError("Production active-set contact count differs from its raw rows.")
            metrics["active_contact_nodes"] = sorted(set(active_nodes))
            metrics["active_contact_region"] = _contact_region(mesh, nodes, active_nodes)
            metrics["active_set_identity"] = _active_identity_metrics(
                route,
                result,
                nodes,
                char_length=char_length,
                char_force=char_force,
                initial_gap=initial_gap,
                contact_rows=rows,
            )
        else:
            active_nodes = [int(node) for node in result.get("active_slave_nodes", [])]
            metrics["active_contact_nodes"] = sorted(set(active_nodes))
            metrics["active_contact_region"] = _contact_region(mesh, nodes, active_nodes)
            identity = _active_identity_metrics(
                route,
                result,
                nodes,
                char_length=char_length,
                char_force=char_force,
                initial_gap=initial_gap,
            )
            metrics["active_set_identity"] = identity
    else:
        metrics["maximum_penetration"] = float(observables["maximum_penetration"])
        metrics["normalized_penetration"] = metrics["maximum_penetration"] / float(
            contract["scales"]["penalty_penetration_scale"]
        )
        energy = observables.get("contact_energy")
        if energy is None or not math.isfinite(float(energy)):
            raise ValueError("Penalty route lacks finite contract contact energy.")
        metrics["contact_energy"] = float(energy)
    if not all(math.isfinite(float(value)) for key, value in metrics.items() if isinstance(value, (int, float))):
        raise ValueError("A required WP07-D metric is non-finite.")
    return metrics


def _case_paths(route: str, level: str, role: str) -> tuple[Path, Path, Path]:
    kind = "PRIMARY_PRODUCTION" if role == "primary" else "INDEPENDENT_REFERENCE"
    output = RUN_ROOT / route / level / role
    authorization = AUTH_ROOT / kind / f"{route}_{level}.json"
    return output / "result.json", output / "run.json", authorization


def _verify_case_provenance(
    *,
    route: str,
    level: str,
    role: str,
    result_path: Path,
    run_path: Path,
    authorization_path: Path,
    binding: Mapping[str, Any],
    contract_identity: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    problems: list[str] = []
    if not result_path.is_file() or not run_path.is_file() or not authorization_path.is_file():
        return {}, {}, [f"Missing {role} result, run manifest, or case authorization for {route}/{level}."]
    result = _read(result_path)
    run = _read(run_path)
    authorization = _read(authorization_path)
    kind = "PRIMARY_PRODUCTION" if role == "primary" else "INDEPENDENT_REFERENCE"
    expected_binding_sha = _file_sha256(ACTIVE_BINDING_PATH)
    if (
        run.get("route") != route
        or run.get("mesh") != level
        or run.get("execution_kind") != kind
        or run.get("status") != "COMPLETED"
        or run.get("authorization_file_sha256") != _file_sha256(authorization_path)
        or run.get("binding_file_sha256") != expected_binding_sha
        or run.get("result_file_sha256") != _file_sha256(result_path)
        or run.get("execution_sha") != authorization.get("execution_sha")
        or authorization.get("route") != route
        or authorization.get("mesh") != level
        or authorization.get("execution_kind") != kind
        or authorization.get("binding_file_sha256") != expected_binding_sha
        or authorization.get("formal_contract_file_sha256") != contract_identity.get("file_sha256")
        or authorization.get("owner_decision_file_sha256") != binding["owner_decision"]["file_sha256"]
        or result.get("execution_kind", result.get("wp07d_execution_kind")) != kind
    ):
        problems.append(f"{role} provenance mismatch for {route}/{level}.")
    expected_counts = binding["mesh_definition"]["cell_counts_by_level"][level]
    nx, ny, nz = (int(value) for value in expected_counts)
    expected_body_nodes = (nx + 1) * (ny + 1) * (nz + 1)
    expected_tet4 = 6 * nx * ny * nz
    expected_axes = binding["mesh_definition"].get("axis_fractions_by_level", {}).get(level)
    expected_exponent = float(binding["mesh_definition"]["coordinate_grading_exponent"])
    if role == "primary":
        mesh_meta = result.get("wp07d_mesh", {})
        if (
            mesh_meta.get("cell_counts") != expected_counts
            or mesh_meta.get("axis_fractions") != expected_axes
            or mesh_meta.get("coordinate_grading_exponent") != expected_exponent
            or result.get("node_count") != expected_body_nodes + 3
            or result.get("element_count") != expected_tet4
            or result.get("ndof") != 3 * (expected_body_nodes + 3)
        ):
            problems.append(f"Primary {route}/{level} result mesh/counts differ from the bound hierarchy.")
    else:
        if (
            result.get("route") != route
            or result.get("mesh_cell_counts") != expected_counts
            or result.get("mesh_axis_fractions") != expected_axes
            or result.get("coordinate_grading_exponent") != expected_exponent
            or len(result.get("displacements", [])) != 3 * expected_body_nodes
        ):
            problems.append(f"Independent reference {route}/{level} mesh differs from the bound hierarchy.")
        if route == "PENALTY" and result.get("penalty_integration") != binding["routes"][route]["penalty_integration"]:
            problems.append("Independent penalty reference integration differs from the frozen contract.")
    run_identity = run.get("formal_contract_provenance", {})
    result_identity = result.get("formal_contract_provenance", result.get("wp07d_contract_provenance", {}))
    for identity in (run_identity, result_identity):
        if (
            not isinstance(identity, Mapping)
            or identity.get("file_sha256") != contract_identity.get("file_sha256")
            or identity.get("revision") != contract_identity.get("revision")
        ):
            problems.append(f"{role} formal contract provenance differs for {route}/{level}.")
            break
    return result, run, problems


def _case_record(
    route: str,
    level: str,
    binding: Mapping[str, Any],
    contract: Mapping[str, Any],
    contract_identity: Mapping[str, Any],
) -> dict[str, Any]:
    primary_path, primary_run_path, primary_auth_path = _case_paths(route, level, "primary")
    reference_path, reference_run_path, reference_auth_path = _case_paths(route, level, "reference")
    primary, primary_run, primary_problems = _verify_case_provenance(
        route=route,
        level=level,
        role="primary",
        result_path=ROOT / primary_path,
        run_path=ROOT / primary_run_path,
        authorization_path=ROOT / primary_auth_path,
        binding=binding,
        contract_identity=contract_identity,
    )
    reference, reference_run, reference_problems = _verify_case_provenance(
        route=route,
        level=level,
        role="reference",
        result_path=ROOT / reference_path,
        run_path=ROOT / reference_run_path,
        authorization_path=ROOT / reference_auth_path,
        binding=binding,
        contract_identity=contract_identity,
    )
    problems = primary_problems + reference_problems
    production_metrics: dict[str, Any] = {}
    reference_metrics: dict[str, Any] = {}
    if primary:
        try:
            production_metrics = _metrics(route, level, primary, binding, contract)
        except (KeyError, TypeError, ValueError, IndexError) as error:
            problems.append(f"Production observable extraction failed for {route}/{level}: {error}")
    if reference:
        try:
            reference_metrics = _metrics(route, level, reference, binding, contract)
        except (KeyError, TypeError, ValueError, IndexError) as error:
            problems.append(f"Independent-reference observable extraction failed for {route}/{level}: {error}")

    primary_status = primary.get("status")
    reference_status = reference.get("status")
    production_pass = bool(primary) and not primary_problems and bool(production_metrics)
    reference_pass = bool(reference) and not reference_problems and bool(reference_metrics)
    if route == "ACTIVE_SET":
        production_pass = production_pass and primary_status == "PASS" and primary.get("solver", {}).get(
            "contact", {}
        ).get("converged") is True
        contact_solver = primary.get("solver", {}).get("contact", {})
        backend = str(contact_solver.get("convergence", {}).get("backend", ""))
        production_pass = production_pass and "spsolve" in backend.lower()
        reference_pass = (
            reference_pass
            and reference_status == "PASS"
            and reference.get("route") == route
            and reference.get("wp07d_observables", {}).get("source")
            == "independent_numpy_scipy_reference_postprocessed"
        )
    else:
        solver = primary.get("solver", {})
        increments = solver.get("increments", []) if isinstance(solver, Mapping) else []
        fallback_count = 0
        linear_diagnostics: list[Mapping[str, Any]] = []
        for increment in increments if isinstance(increments, list) else []:
            diagnostics = increment.get("diagnostics", {}) if isinstance(increment, Mapping) else {}
            linear = diagnostics.get("linear_system_diagnostics", []) if isinstance(diagnostics, Mapping) else []
            if isinstance(linear, list):
                valid_rows = [item for item in linear if isinstance(item, Mapping)]
                linear_diagnostics.extend(valid_rows)
                fallback_count += sum(bool(item.get("fallback_used")) for item in valid_rows)
                if len(valid_rows) != len(linear):
                    fallback_count += 1
        tolerance = float(binding["routes"][route]["newton_tolerance"])
        linear_policy_pass = bool(linear_diagnostics) and all(
            item.get("linear_backend") == "scipy.sparse.linalg.minres"
            and item.get("preconditioner") == "jacobi"
            and item.get("fallback_used") is False
            for item in linear_diagnostics
        )
        production_pass = (
            production_pass
            and str(primary_status).lower() in {"success", "pass"}
            and solver.get("converged") is True
            and len(increments) == 8
            and fallback_count == 0
            and solver.get("history_is_partial") is False
            and linear_policy_pass
            and float(solver.get("final_relative_residual", math.inf)) <= tolerance
        )
        reference_pass = (
            reference_pass
            and reference_status == "PASS"
            and reference.get("route") == route
            and reference.get("penalty_integration") == binding["routes"][route]["penalty_integration"]
            and len(reference.get("accepted_increments", [])) == 8
        )
    equilibrium_limit = float(contract["thresholds"]["equilibrium"]["force_relative"])
    for label, metrics in (("production", production_metrics), ("reference", reference_metrics)):
        if metrics and (
            metrics.get("force_equilibrium_relative", math.inf) > equilibrium_limit
            or metrics.get("moment_equilibrium_relative", math.inf)
            > float(contract["thresholds"]["equilibrium"]["moment_relative"])
        ):
            problems.append(f"{label} force/moment equilibrium failed for {route}/{level}.")
            if label == "production":
                production_pass = False
            else:
                reference_pass = False

    if route == "ACTIVE_SET":
        identity_limits = contract["thresholds"]["active_set_identity"]
        for role, role_metrics in (("production", production_metrics), ("reference", reference_metrics)):
            identity = role_metrics.get("active_set_identity", {})
            for name, limit in identity_limits.items():
                if float(identity.get(name, math.inf)) > float(limit):
                    problems.append(f"{role} active-set identity {name} failed for {route}/{level}.")
                    if role == "production":
                        production_pass = False
                    else:
                        reference_pass = False

    reference_deltas: dict[str, float] = {}
    if production_metrics and reference_metrics:
        for key in ("selected_displacement", "reaction_resultant", "reaction_moment", "contact_resultant"):
            reference_deltas[key] = _relative_delta(
                float(production_metrics[key]), float(reference_metrics[key]), 50000.0
            )
        if route == "PENALTY":
            reference_deltas["maximum_penetration"] = _relative_delta(
                float(production_metrics["maximum_penetration"]),
                float(reference_metrics["maximum_penetration"]),
                float(contract["scales"]["penalty_penetration_scale"]),
            )
            reference_deltas["contact_energy"] = _relative_delta(
                float(production_metrics["contact_energy"]), float(reference_metrics["contact_energy"])
            )

    return {
        "case_id": f"WP07D-{route}-{level}",
        "route": route,
        "mesh": level,
        "status": "PASS" if production_pass and reference_pass else "FAIL_CLOSED",
        "production_status": primary_status if primary else "MISSING",
        "reference_status": reference_status if reference else "MISSING",
        "production_run_status": primary_run.get("status", "MISSING"),
        "reference_run_status": reference_run.get("status", "MISSING"),
        "production_result_path": primary_path.as_posix(),
        "production_result_sha256": _file_sha256(ROOT / primary_path) if (ROOT / primary_path).is_file() else None,
        "production_run_path": primary_run_path.as_posix(),
        "production_run_sha256": _file_sha256(ROOT / primary_run_path) if (ROOT / primary_run_path).is_file() else None,
        "reference_result_path": reference_path.as_posix(),
        "reference_result_sha256": _file_sha256(ROOT / reference_path) if (ROOT / reference_path).is_file() else None,
        "reference_run_path": reference_run_path.as_posix(),
        "reference_run_sha256": _file_sha256(ROOT / reference_run_path) if (ROOT / reference_run_path).is_file() else None,
        "production_telemetry_status": primary_run.get("telemetry_status", "UNAVAILABLE"),
        "reference_telemetry_status": reference_run.get("telemetry_status", "UNAVAILABLE"),
        "production_metrics": production_metrics,
        "reference_metrics": reference_metrics,
        "production_reference_relative_deltas": {
            "status": "REPORTED_NO_FROZEN_NUMERICAL_AGREEMENT_TOLERANCE_IN_CONTRACT",
            "values": reference_deltas,
        },
        "problems": problems,
    }


def _route_convergence_gates(
    route: str,
    records: Mapping[str, Mapping[str, Any]],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    limits = contract["thresholds"]["mesh_m2_to_m3"]
    m2 = records["M2"]["production_metrics"]
    m3 = records["M3"]["production_metrics"]
    mappings: dict[str, tuple[str, str, float]] = {
        "selected_displacement": ("selected_displacement", "selected_displacement_relative", 1.0),
        "reaction_resultant": ("reaction_resultant", "reaction_resultant_relative", 50000.0),
        "reaction_moment": ("reaction_moment", "reaction_moment_relative", 50000.0),
        "contact_resultant": ("contact_resultant", "contact_resultant_relative", 50000.0),
    }
    if route == "ACTIVE_SET":
        mappings["active_contact_region"] = (
            "active_contact_region",
            "active_set_contact_region_relative",
            1.0,
        )
    else:
        mappings["normalized_penetration"] = (
            "normalized_penetration",
            "penalty_normalized_penetration_relative",
            1.0,
        )
        mappings["contact_energy"] = ("contact_energy", "penalty_contact_energy_relative", 1.0)
    gates: dict[str, dict[str, Any]] = {}
    for label, (metric, limit_name, scale) in mappings.items():
        try:
            delta = _relative_delta(float(m2[metric]), float(m3[metric]), scale)
            limit = float(limits[limit_name])
            status = "PASS" if delta <= limit else "FAIL_CLOSED"
        except (KeyError, TypeError, ValueError):
            delta = None
            limit = float(limits[limit_name])
            status = "FAIL_CLOSED"
        gates[label] = {"m2_to_m3_relative_delta": delta, "frozen_limit": limit, "status": status}
    return gates


def build_pre_replay_report(
    binding_path: Path = FORMAL_REBIND_R1_BINDING_PATH,
) -> dict[str, Any]:
    binding = load_binding(binding_path)
    validate_binding(binding)
    contract = load_contract_for_binding(binding)
    identity = formal_contract_identity(binding)
    if identity is None:
        raise ValueError("Formal R1 contract identity is not available.")
    routes: dict[str, Any] = {}
    for route in EXPECTED_ROUTES:
        records = {
            level: _case_record(route, level, binding, contract, identity) for level in EXPECTED_LEVELS
        }
        mesh_gates = _route_convergence_gates(route, records, contract)
        cases_pass = all(record["status"] == "PASS" for record in records.values())
        convergence_pass = all(gate["status"] == "PASS" for gate in mesh_gates.values())
        route_pass = cases_pass and convergence_pass
        replay_level = str(binding["routes"][route]["replay_level"])
        routes[route] = {
            "status": "PASS_READY_FOR_REPLAY" if route_pass else "FAIL_CLOSED",
            "replay_level": replay_level,
            "cases": records,
            "m2_to_m3_gates": mesh_gates,
            "production_reference_agreement": "DELTAS_RECORDED; CONTRACT_HAS_NO_NUMERICAL_AGREEMENT_TOLERANCE",
            "production_and_reference_cases_pass": cases_pass,
            "convergence_gates_pass": convergence_pass,
        }
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_id": (
            "QF-029-WP07-D-CONTACT-R2-PRE-REPLAY-GATE-001"
            if binding.get("artifact_id") == "QF-029-WP07-D-EXECUTION-BINDING-CONTACT-R2-001"
            else "QF-029-WP07-D-FORMAL-REBIND-R1-PRE-REPLAY-ANALYSIS-001"
        ),
        "status": "PASS_REPLAY_GATES_EVALUATED" if any(
            item["status"] == "PASS_READY_FOR_REPLAY" for item in routes.values()
        ) else "FAIL_CLOSED_NO_REPLAY_AUTHORIZED",
        "authorized_base_sha": binding["governing"]["authorized_base_sha"],
        "execution_sha": _git("rev-parse", "HEAD"),
        "binding_path": binding_path.relative_to(ROOT).as_posix(),
        "binding_file_sha256": _file_sha256(binding_path),
        "formal_contract_provenance": identity,
        "owner_decision": binding["owner_decision"],
        "policy_digest": binding["governing"]["policy_digest"],
        "analysis_script_path": Path(__file__).relative_to(ROOT).as_posix(),
        "analysis_script_sha256": _file_sha256(Path(__file__)),
        "routes": routes,
        "replay_authorizations_created": False,
        "replay_run": False,
        "wp07e_run": False,
        "formal_points_awarded": 0,
    }
    if binding.get("artifact_id") == "QF-029-WP07-D-EXECUTION-BINDING-CONTACT-R2-001":
        report["requalification_contract_sha256"] = binding["source_requalification"]["sha256"]
        report["run_root"] = RUN_ROOT.as_posix()
        report["authorization_root"] = AUTH_ROOT.as_posix()
        report["production_mechanics_changed_by_requalification"] = True
        report["thresholds_changed"] = False
        report["wp07e_run"] = False
    return report


def _flatten_numeric(value: Any, prefix: str = "$") -> dict[str, float]:
    found: dict[str, float] = {}
    if isinstance(value, Mapping):
        for key, item in value.items():
            found.update(_flatten_numeric(item, f"{prefix}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.update(_flatten_numeric(item, f"{prefix}[{index}]"))
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        if math.isfinite(number):
            found[prefix] = number
        else:
            raise ValueError(f"Non-finite replay observable at {prefix}.")
    return found


def _replay_comparison(route: str, level: str, binding: Mapping[str, Any]) -> dict[str, Any]:
    primary_path, primary_run_path, _ = _case_paths(route, level, "primary")
    replay_root = ROOT / RUN_ROOT / route / level / "replay"
    replay_path = replay_root / "result.json"
    replay_run_path = replay_root / "run.json"
    replay_auth_path = AUTH_ROOT / "REPLAY" / f"{route}_{level}.json"
    if not all(path.is_file() for path in (ROOT / primary_path, ROOT / primary_run_path, replay_path, replay_run_path, replay_auth_path)):
        return {"status": "FAIL_CLOSED_MISSING_REPLAY_EVIDENCE"}
    primary = _read(ROOT / primary_path)
    replay = _read(replay_path)
    run = _read(replay_run_path)
    authorization = _read(replay_auth_path)
    problems: list[str] = []
    if (
        run.get("status") != "COMPLETED"
        or run.get("route") != route
        or run.get("mesh") != level
        or run.get("execution_kind") != "REPLAY"
        or run.get("result_file_sha256") != _file_sha256(replay_path)
        or run.get("authorization_file_sha256") != _file_sha256(replay_auth_path)
        or run.get("binding_file_sha256") != _file_sha256(ACTIVE_BINDING_PATH)
        or run.get("execution_sha") != authorization.get("execution_sha")
        or replay.get("wp07d_execution_kind") != "REPLAY"
        or authorization.get("execution_kind") != "REPLAY"
        or authorization.get("route") != route
        or authorization.get("mesh") != level
        or authorization.get("structural_solves_allowed") is not True
        or authorization.get("independent_references_allowed") is not False
        or authorization.get("replay_allowed") is not True
        or authorization.get("wp07e_allowed") is not False
        or authorization.get("replay_gate_path") != REPLAY_GATE_PATH.as_posix()
        or authorization.get("replay_gate_file_sha256") != _file_sha256(ROOT / REPLAY_GATE_PATH)
    ):
        problems.append("Replay execution provenance is incomplete or mismatched.")
    if primary.get("status") != replay.get("status"):
        problems.append("Primary and replay terminal statuses differ.")
    primary_values = _flatten_numeric(
        {"displacements": primary.get("displacements"), "wp07d_observables": primary.get("wp07d_observables")}
    )
    replay_values = _flatten_numeric(
        {"displacements": replay.get("displacements"), "wp07d_observables": replay.get("wp07d_observables")}
    )
    if set(primary_values) != set(replay_values):
        problems.append("Primary and replay numeric observable sets differ.")
        deltas: dict[str, float | None] = {}
    else:
        deltas = {
            key: _relative_delta(primary_values[key], replay_values[key])
            for key in sorted(primary_values)
        }
    replay_limit = float(load_contract_for_binding(binding)["thresholds"]["replay"]["relative"])
    floor = float(load_contract_for_binding(binding)["thresholds"]["replay"]["absolute_floor"])
    if any(
        abs(primary_values[key] - replay_values[key])
        > replay_limit * max(abs(primary_values[key]), abs(replay_values[key]), floor)
        for key in set(primary_values) & set(replay_values)
    ):
        problems.append("One or more primary/replay numeric observables exceed the frozen replay tolerance.")
    if route == "ACTIVE_SET":
        primary_contact = primary.get("solver", {}).get("contact", {})
        replay_contact = replay.get("solver", {}).get("contact", {})
        primary_active = sorted(
            int(item["slave_node"])
            for item in primary_contact.get("contacts", [])
            if item.get("active") is True
        )
        replay_active = sorted(
            int(item["slave_node"])
            for item in replay_contact.get("contacts", [])
            if item.get("active") is True
        )
        if primary_active != replay_active:
            problems.append("Primary and replay qualitative active-contact status differs.")
        if primary_contact.get("iteration_count") != replay_contact.get("iteration_count"):
            problems.append("Primary and replay active-set iteration counts differ.")
    else:
        primary_increments = primary.get("solver", {}).get("increments", [])
        replay_increments = replay.get("solver", {}).get("increments", [])
        primary_factors = [item.get("load_factor") for item in primary_increments]
        replay_factors = [item.get("load_factor") for item in replay_increments]
        primary_iterations = [item.get("iterations") for item in primary_increments]
        replay_iterations = [item.get("iterations") for item in replay_increments]
        primary_terminal = [item.get("termination_classification") for item in primary_increments]
        replay_terminal = [item.get("termination_classification") for item in replay_increments]
        if (
            primary_factors != replay_factors
            or primary_iterations != replay_iterations
            or primary_terminal != replay_terminal
            or primary.get("solver", {}).get("newton_iterations")
            != replay.get("solver", {}).get("newton_iterations")
        ):
            problems.append("Primary and replay load-factor/acceptance histories differ.")
    return {
        "status": "PASS" if not problems else "FAIL_CLOSED",
        "route": route,
        "mesh": level,
        "primary_result_sha256": _file_sha256(ROOT / primary_path),
        "replay_result_sha256": _file_sha256(replay_path),
        "replay_run_sha256": _file_sha256(replay_run_path),
        "replay_authorization_sha256": _file_sha256(replay_auth_path),
        "max_relative_delta": max(deltas.values(), default=0.0) if deltas else None,
        "numeric_deltas": deltas,
        "frozen_relative_tolerance": replay_limit,
        "frozen_absolute_floor": floor,
        "problems": problems,
    }


def build_final_report(binding_path: Path = FORMAL_REBIND_R1_BINDING_PATH) -> dict[str, Any]:
    pre = build_pre_replay_report(binding_path)
    binding = load_binding(binding_path)
    identity = formal_contract_identity(binding)
    assert identity is not None
    routes: dict[str, Any] = {}
    for route in EXPECTED_ROUTES:
        pre_route = pre["routes"][route]
        if pre_route["status"] != "PASS_READY_FOR_REPLAY":
            replay = {"status": "SKIPPED_DEPENDENCY_ROUTE_GATES_FAILED"}
        else:
            replay = _replay_comparison(route, str(pre_route["replay_level"]), binding)
        routes[route] = {
            **pre_route,
            "replay": replay,
            "final_route_status": "PASS_CANDIDATE" if replay.get("status") == "PASS" else "FAIL_CLOSED",
        }
    all_pass = all(item["final_route_status"] == "PASS_CANDIDATE" for item in routes.values())
    return {
        "schema_version": 1,
        "artifact_id": (
            "QF-029-WP07-D-CONTACT-R2-FINAL-ANALYSIS-001"
            if binding.get("artifact_id") == "QF-029-WP07-D-EXECUTION-BINDING-CONTACT-R2-001"
            else "QF-029-WP07-D-FORMAL-REBIND-R1-FINAL-ANALYSIS-001"
        ),
        "status": "READY_FOR_OWNER_REVIEW" if all_pass else "FAIL_CLOSED_OR_INCOMPLETE",
        "authorized_base_sha": binding["governing"]["authorized_base_sha"],
        "execution_sha": _git("rev-parse", "HEAD"),
        "binding_path": binding_path.relative_to(ROOT).as_posix(),
        "binding_file_sha256": _file_sha256(binding_path),
        "formal_contract_provenance": identity,
        "owner_decision": binding["owner_decision"],
        "policy_digest": binding["governing"]["policy_digest"],
        "routes": routes,
        "wp07d_candidate_points": "pending Owner review; no points awarded by this analysis",
        "wp07_official_points": "unchanged pending Owner review",
        "global_official_total": "unchanged; ledger not modified",
        "production_mechanics_changed_by_this_rebind": binding.get("artifact_id")
        == "QF-029-WP07-D-EXECUTION-BINDING-CONTACT-R2-001",
        "thresholds_changed": False,
        "full_repository_test_suite_run": False,
        "wp07e_run": False,
        "push_or_merge_performed": False,
        "owner_review_required": True,
    }


def write_new(path: Path, report: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
        stream.flush()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("pre-replay", "final"), default="pre-replay")
    parser.add_argument("--binding", type=Path, default=FORMAL_REBIND_R1_BINDING_PATH)
    args = parser.parse_args(argv)
    binding_path = args.binding.resolve()
    try:
        report = build_pre_replay_report(binding_path) if args.stage == "pre-replay" else build_final_report(binding_path)
        target = PRE_REPLAY_REPORT if args.stage == "pre-replay" else FINAL_REPORT
        write_new(ROOT / target, report)
    except FileExistsError as error:
        print(f"WP07-D analysis refuses to overwrite existing evidence: {error}", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        print(f"WP07-D formal analysis failed closed: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"status": report["status"], "output": target.as_posix()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
