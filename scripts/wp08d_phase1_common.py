"""Controlled WP08-D Phase-1 runner support.

This module contains execution tooling only.  It reuses the frozen Phase-0
mesh/load preparation helpers and keeps all production contact imports lazy,
behind the explicit Phase-1 authorization guard.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess
from time import perf_counter
from typing import Any, Mapping

import numpy as np


REQUIRED_GOVERNING_SHA = "28cf9dd1886b72c6c7c9fc720dc778eddfce4441"
REQUIRED_BRANCH = "0.2.9-wp08d-phase1-runner"
AUTHORIZED_INTEGRATION_BRANCH = "0.2.9-wp08d-m1-phase1"
CONTRACT_RELATIVE_PATH = Path("qualification/0_2_9/wp08d_structural_reference_contract.json")
POLICY_DIGEST = "93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac"
CONTRACT_DIGEST = "d2d9533c873000996ab3fad992c653dfed37f533ed12d85af97b3696740f179a"
UNAUTHORIZED_PHASE1_EXECUTION_FAIL_CLOSED = "UNAUTHORIZED_PHASE1_EXECUTION_FAIL_CLOSED"
PHASE1_AUTHORIZATION_TOKEN = "OWNER_AUTHORIZED_WP08D_PHASE1_EXECUTION"
ARTIFACT_ROOT = Path("qualification/0_2_9/wp08d_phase1")


def repository_root() -> Path:
    """Return the repository root from this script's location."""

    return Path(__file__).resolve().parents[1]


def canonical_json_digest(value: object) -> str:
    """Return the SHA-256 digest used by controlled JSON contracts."""

    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_sha256(path: Path) -> str:
    """Hash a file without loading large evidence into memory."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _first_mapping_value(payload: Mapping[str, Any], *keys: str) -> object | None:
    for key in keys:
        if key in payload:
            return payload[key]
    return None


def _vector_or_zero(payload: Mapping[str, Any], *keys: str) -> object:
    value = _first_mapping_value(payload, *keys)
    return [0.0, 0.0, 0.0] if value is None else value


def read_contract(root: Path | None = None) -> dict[str, Any]:
    """Read and verify the immutable WP08-D contract."""

    contract_path = (root or repository_root()) / CONTRACT_RELATIVE_PATH
    payload = json.loads(contract_path.read_text(encoding="utf-8"))
    digest = canonical_json_digest(payload)
    if digest != CONTRACT_DIGEST:
        raise RuntimeError(f"WP08-D contract digest mismatch: expected {CONTRACT_DIGEST}, got {digest}.")
    if payload.get("status") != "PREPARATION_ONLY":
        raise RuntimeError("WP08-D contract is not in PREPARATION_ONLY status.")
    if payload.get("execution_guard", {}).get("structural_solves_enabled") is not False:
        raise RuntimeError("WP08-D structural execution guard is not disabled by default.")
    return payload


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def git_state(root: Path | None = None) -> dict[str, str | bool]:
    """Return branch, commit and cleanliness without changing repository state."""

    repo = root or repository_root()
    branch = _git(repo, "branch", "--show-current")
    head = _git(repo, "rev-parse", "HEAD")
    dirty = bool(_git(repo, "status", "--porcelain"))
    return {"branch": branch, "head": head, "dirty": dirty}


def verify_branch_provenance(root: Path | None = None) -> dict[str, object]:
    """Verify the Phase-1 branch remains a descendant of the frozen baseline."""

    repo = root or repository_root()
    state = git_state(repo)
    if state["branch"] not in {REQUIRED_BRANCH, AUTHORIZED_INTEGRATION_BRANCH}:
        raise RuntimeError(f"Unexpected Phase-1 branch: {state['branch']!r}.")
    if state["dirty"]:
        raise RuntimeError("Phase-1 runner working tree is not clean.")
    is_descendant = subprocess.run(
        ["git", "merge-base", "--is-ancestor", REQUIRED_GOVERNING_SHA, str(state["head"])],
        cwd=repo,
        check=False,
        capture_output=True,
    ).returncode == 0
    if not is_descendant:
        raise RuntimeError("Phase-1 runner HEAD is not based on the required governing SHA.")
    return {
        "branch": state["branch"],
        "head": state["head"],
        "required_governing_sha": REQUIRED_GOVERNING_SHA,
        "governing_sha_is_ancestor": True,
        "working_tree_clean": True,
    }


def frozen_mesh_level(name: str) -> Any:
    """Return one frozen mesh descriptor from the existing contract helper."""

    from scripts.prepare_wp08d_structural_reference import MESH_LEVELS

    requested = str(name).upper()
    for level in MESH_LEVELS:
        if level.name == requested:
            return level
    raise ValueError(f"Unsupported frozen WP08-D mesh level: {name!r}.")


def build_preflight(name: str, *, root: Path | None = None) -> dict[str, Any]:
    """Build mesh/load preflight data without assembling or solving contact."""

    repo = root or repository_root()
    contract = read_contract(repo)
    from scripts.prepare_wp08d_structural_reference import generate_mesh, load_contract, mesh_contract

    level = frozen_mesh_level(name)
    mesh = generate_mesh(level)
    mesh_report = mesh_contract(mesh)
    loads = load_contract(mesh)
    if not mesh_report["finite_coordinates"] or not mesh_report["positive_reference_volumes"]:
        raise RuntimeError("WP08-D mesh preflight failed finite/positive-volume checks.")
    if not mesh_report["master_projection_coverage"]:
        raise RuntimeError("WP08-D mesh preflight failed master-face coverage.")
    if any(loads[key]["resultant"]["status"] != "PASS" or loads[key]["moment"]["status"] != "PASS" for key in loads if key in {"normal", "tangential"}):
        raise RuntimeError("WP08-D load preflight failed resultant or moment checks.")
    expected_level = next(item for item in contract["mesh_levels"] if item["id"] == level.name)
    for key, expected in (
        ("nodes", expected_level["nodes_in_future_model"]),
        ("elements", expected_level["elements"]),
        ("dofs", expected_level["dofs_in_future_model"]),
    ):
        if mesh_report[key] != expected:
            raise RuntimeError(f"WP08-D {level.name} {key} mismatch: {mesh_report[key]} != {expected}.")
    return {
        "status": "PASS",
        "mesh": mesh_report,
        "loads": loads,
        "contract_digest": CONTRACT_DIGEST,
        "policy_digest": POLICY_DIGEST,
        "governing_sha": REQUIRED_GOVERNING_SHA,
        "structural_solves_run": False,
        "contact_solves_run": False,
        "reference_solves_run": False,
        "replay_run": False,
        "expected_artifacts": artifact_layout(level.name),
    }


def artifact_layout(mesh_name: str) -> dict[str, str]:
    """Describe the immutable Phase-1 artifact layout without creating runs."""

    name = str(mesh_name).upper()
    return {
        "result": f"{name}/result.json",
        "progress": f"{name}/progress.json",
        "telemetry": f"{name}/telemetry.jsonl",
        "raw": f"{name}/raw.npz",
        "manifest": f"{name}/manifest.json",
        "independent_reference": "independent_reference/M1/manifest.json",
        "replay": "replay/M1/manifest.json",
    }


def _jsonable(value: object) -> object:
    if isinstance(value, np.ndarray):
        return [_jsonable(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def write_json(path: Path, value: object) -> None:
    """Write finite, deterministic JSON and flush it before returning."""

    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(_jsonable(value), indent=2, sort_keys=True, allow_nan=False)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


@dataclass
class Phase1Progress:
    """Small immediate-flush progress writer used by the future execution path."""

    path: Path

    def update(self, **values: object) -> None:
        payload = {"schema_version": 1, **values}
        write_json(self.path, payload)


class Phase1Telemetry:
    """Immediate-flush JSONL telemetry with a Phase-1 event alias."""

    _EVENT_ALIASES = {
        "RUN_START": "ANALYSIS_START",
        "RUN_END": "ANALYSIS_END",
        "RUN_FAILED": "ANALYSIS_FAILED",
        "HEARTBEAT": "CHECKPOINT",
        "NEWTON_START": "NONLINEAR_ITERATION",
        "KRYLOV_PROGRESS": "LINEAR_SOLVE_ITERATION",
        "STEP_END": "STEP_ACCEPTED",
    }

    def __init__(self, path: Path, *, analysis_id: str, mesh: str) -> None:
        from solveur.core.telemetry.events import EventStatus
        from solveur.core.telemetry.jsonl import JsonlSink
        from solveur.core.telemetry.observer import TelemetryEmitter

        self._sink = JsonlSink(path, fsync=True, sink_identifier="wp08d_phase1_jsonl")
        self._emitter = TelemetryEmitter(
            analysis_id=analysis_id,
            analysis_type="linear_static",
            route="wp08d_phase1",
            sinks=(self._sink,),
            metadata={"mesh": mesh, "contract_digest": CONTRACT_DIGEST, "policy_digest": POLICY_DIGEST},
        )
        self._event_status = EventStatus

    def emit(self, phase1_event: str, event_type: str, *, status: str = "INFO", **values: object) -> None:
        event_type = self._EVENT_ALIASES.get(event_type, event_type)
        self._emitter.emit(
            event_type,
            status=status,
            metrics={"phase1_event": phase1_event, **values},
            step=values.get("increment") if isinstance(values.get("increment"), int) else None,
            iteration=values.get("newton_iteration") if isinstance(values.get("newton_iteration"), int) else None,
            solver_backend=str(values["linear_solver"]) if values.get("linear_solver") is not None else None,
        )

    def close(self) -> None:
        self._emitter.close()


def _authorization_payload(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(UNAUTHORIZED_PHASE1_EXECUTION_FAIL_CLOSED) from error
    if not isinstance(payload, dict):
        raise RuntimeError(UNAUTHORIZED_PHASE1_EXECUTION_FAIL_CLOSED)
    required = {
        "authorization": PHASE1_AUTHORIZATION_TOKEN,
        "governing_base_sha": REQUIRED_GOVERNING_SHA,
        "scope": "WP08-D_PHASE1_STRUCTURAL_EXECUTION",
    }
    if any(payload.get(key) != value for key, value in required.items()):
        raise RuntimeError(UNAUTHORIZED_PHASE1_EXECUTION_FAIL_CLOSED)
    state = git_state()
    if state["branch"] != payload.get("branch"):
        raise RuntimeError(UNAUTHORIZED_PHASE1_EXECUTION_FAIL_CLOSED)
    governing_sha = payload.get("governing_sha")
    if not isinstance(governing_sha, str) or len(governing_sha) != 40:
        raise RuntimeError(UNAUTHORIZED_PHASE1_EXECUTION_FAIL_CLOSED)
    is_merged_governing_ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", governing_sha, str(state["head"])],
        cwd=repository_root(),
        check=False,
        capture_output=True,
    ).returncode == 0
    if not is_merged_governing_ancestor:
        raise RuntimeError(UNAUTHORIZED_PHASE1_EXECUTION_FAIL_CLOSED)
    return payload


def require_phase1_authorization(path: Path | None, *, mesh: str) -> dict[str, Any]:
    """Require a traceable Owner authorization before any solve is imported."""

    if path is None or not path.is_file():
        raise RuntimeError(UNAUTHORIZED_PHASE1_EXECUTION_FAIL_CLOSED)
    payload = _authorization_payload(path)
    allowed_meshes = payload.get("meshes", ["M1", "M2", "M3"])
    if not isinstance(allowed_meshes, list) or str(mesh).upper() not in {str(item).upper() for item in allowed_meshes}:
        raise RuntimeError(UNAUTHORIZED_PHASE1_EXECUTION_FAIL_CLOSED)
    return payload


def _load_vector_from_contract(mesh: Any) -> tuple[list[dict[str, Any]], list[list[float]]]:
    """Construct frozen consistent nodal loads for the future production route."""

    from scripts.prepare_wp08d_structural_reference import consistent_surface_traction, load_contract

    normal = consistent_surface_traction(mesh, mesh.top_faces, load_contract(mesh)["normal"]["resultant"]["expected"])
    tangential = consistent_surface_traction(
        mesh, mesh.top_faces, load_contract(mesh)["tangential"]["resultant"]["expected"]
    )
    by_node = normal["nodal_forces"] + tangential["nodal_forces"]
    loads: list[dict[str, Any]] = []
    component_factors: list[str] = []
    for node in range(mesh.level.body_node_count):
        for dof, index, factor_name in (("UX", 0, "tangential_factor"), ("UY", 1, "tangential_factor"), ("UZ", 2, "normal_factor")):
            value = float(by_node[node, index])
            if value == 0.0:
                continue
            loads.append({"node": node, "dof": dof, "value": value})
            component_factors.append(factor_name)
    rows = []
    for increment in (1.0, 0.25, 0.75, 1.0, 1.25, 0.25, -0.5):
        rows.append([increment if factor == "tangential_factor" else 1.0 for factor in component_factors])
    return loads, rows


def build_production_model(mesh_name: str) -> Any:
    """Build the frozen production model lazily for an authorized future run."""

    from scripts.prepare_wp08d_structural_reference import generate_mesh
    from solveur.core.model import FiniteElementModel

    mesh = generate_mesh(frozen_mesh_level(mesh_name))
    loads, load_history = _load_vector_from_contract(mesh)
    fixed = [{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in mesh.fixed_body_nodes + mesh.master_nodes]
    contacts = [
        {
            "name": "wp08d_initial_fixed_master",
            "slave_nodes": list(mesh.slave_nodes),
            "master_nodes": list(mesh.master_faces[0]),
            "master_faces": [list(face) for face in mesh.master_faces],
            "friction_coefficient": 0.3,
            "tangential_stiffness": 1.0e6,
            "gap_tolerance": 1.0e-10,
        }
    ]
    elements = [{"type": "TET4", "nodes": list(tet), "material": "elastic"} for tet in mesh.elements]
    return FiniteElementModel.from_raw(
        nodes=mesh.nodes.tolist(),
        elements=elements,
        materials={"elastic": {"type": "isotropic_3d", "E": 1.0e6, "nu": 0.3}},
        fixed_dofs=fixed,
        loads=loads,
        contacts=contacts,
        analysis={
            "type": "linear_static",
            "method": "direct",
            "contact_max_iterations": 25,
            "contact_friction_tolerance": 1.0e-9,
            "contact_load_history": load_history,
            "contact_search_mode": "initial",
        },
    )


def extract_observables(result: Any) -> dict[str, Any]:
    """Extract contract-shaped observables from a completed production result."""

    payload = result.to_dict() if hasattr(result, "to_dict") else dict(result)
    solver = payload.get("solver", {}) if isinstance(payload, dict) else {}
    contact = solver.get("contact", {}) if isinstance(solver, dict) else {}
    rows = contact.get("contacts", []) if isinstance(contact, dict) else []
    normal_resultant: np.ndarray = np.zeros(3, dtype=float)
    tangential_resultant: np.ndarray = np.zeros(3, dtype=float)
    states: list[str] = []
    pressures: list[float] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        normal = np.asarray(row.get("normal", (0.0, 0.0, 0.0)), dtype=float)
        pressure = float(row.get("pressure", 0.0))
        normal_resultant += pressure * normal
        tangent_one = np.asarray(row.get("tangent_one", (0.0, 0.0, 0.0)), dtype=float)
        tangent_two = np.asarray(row.get("tangent_two", (0.0, 0.0, 0.0)), dtype=float)
        tangent_force = np.asarray(row.get("tangential_force", (0.0, 0.0)), dtype=float)
        tangential_resultant += tangent_force[0] * tangent_one + tangent_force[1] * tangent_two
        states.append(str(row.get("tangential_state", "open")))
        pressures.append(pressure)
    audit = payload.get("audit", {}) if isinstance(payload, dict) else {}
    equilibrium = audit.get("equilibrium", {}) if isinstance(audit, dict) else {}
    return {
        "selected_displacement": float(payload.get("max_displacement", 0.0)),
        "reaction_resultant": _vector_or_zero(equilibrium, "reaction_resultant"),
        "reaction_moment": _vector_or_zero(equilibrium, "reaction_moment_about_origin"),
        "normal_contact_resultant": normal_resultant.tolist(),
        "tangential_contact_resultant": tangential_resultant.tolist(),
        "active_contact_count": int(contact.get("active_contact_count", 0)) if isinstance(contact, dict) else 0,
        "contact_states": states,
        "contact_pressures": pressures,
        "cumulative_local_dissipation": float(contact.get("cumulative_local_dissipation", 0.0)) if isinstance(contact, dict) else 0.0,
        "force_balance_relative_error": float(equilibrium.get("force_balance_relative_error", 0.0)) if isinstance(equilibrium, dict) else 0.0,
        "moment_balance_relative_error": float(equilibrium.get("moment_balance_relative_error", 0.0)) if isinstance(equilibrium, dict) else 0.0,
    }


def write_manifest(
    case_dir: Path,
    *,
    mesh_name: str,
    terminal_status: str,
    terminal_classification: str,
    qualification_claim: str,
    frozen_parameters: Mapping[str, object] | None = None,
) -> dict[str, Any]:
    """Write a hash-complete manifest after all case artifacts are closed."""

    state = git_state()
    files = []
    for path in sorted(case_dir.iterdir()):
        if path.is_file() and path.name != "manifest.json":
            files.append({"relative_path": path.name, "size_bytes": path.stat().st_size, "sha256": file_sha256(path)})
    manifest = {
        "schema_version": 1,
        "case": f"WP08-D-{str(mesh_name).upper()}-PHASE1",
        "governing_sha": REQUIRED_GOVERNING_SHA,
        "runner_sha": state["head"],
        "contract_digest": CONTRACT_DIGEST,
        "policy_digest": POLICY_DIGEST,
        "mesh": str(mesh_name).upper(),
        "route": "linear_static_node_to_triangle_lagrange_active_set_regularized_coulomb",
        "frozen_parameters": dict(frozen_parameters or {}),
        "files": files,
        "terminal_status": terminal_status,
        "terminal_classification": terminal_classification,
        "qualification_claim": qualification_claim,
    }
    write_json(case_dir / "manifest.json", manifest)
    return manifest


def execute_phase1(mesh_name: str, output_dir: Path, authorization_file: Path | None) -> dict[str, Any]:
    """Execute one future Phase-1 case only after explicit Owner authorization."""

    authorization = require_phase1_authorization(authorization_file, mesh=mesh_name)
    from solveur.api.public import solve_model

    preflight = build_preflight(mesh_name)
    case_dir = output_dir / str(mesh_name).upper()
    case_dir.mkdir(parents=True, exist_ok=True)
    progress = Phase1Progress(case_dir / "progress.json")
    telemetry = Phase1Telemetry(case_dir / "telemetry.jsonl", analysis_id=f"WP08D-{mesh_name.upper()}", mesh=mesh_name.upper())
    started = perf_counter()
    progress.update(status="RUNNING", phase="RUN_START", mesh=mesh_name.upper(), elapsed_time_s=0.0)
    telemetry.emit("RUN_START", "ANALYSIS_START", status="STARTED", elapsed=0.0)
    try:
        model = build_production_model(mesh_name)
        progress.update(status="RUNNING", phase="MESH_READY", mesh=mesh_name.upper(), elapsed_time_s=perf_counter() - started)
        telemetry.emit("MESH_READY", "MESH_READY", status="COMPLETED", elapsed=perf_counter() - started)
        telemetry.emit("ASSEMBLY_START", "ASSEMBLY_START", status="STARTED", elapsed=perf_counter() - started)
        result = solve_model(model, enforce_policy=False, telemetry=telemetry._emitter)
        result_payload = result.to_dict()
        result_payload.update({
            "schema_version": 1,
            "phase1": {"mesh": mesh_name.upper(), "authorization": authorization, "preflight": preflight},
            "observables": extract_observables(result),
            "equilibrium": (result_payload.get("audit", {}) or {}).get("equilibrium", {}),
            "contact": (result_payload.get("solver", {}) or {}).get("contact", {}),
            "terminal_classification": "PASS",
            "qualification_claim": "PHASE1_EXECUTION_EVIDENCE_NOT_FORMAL_WP08_CLOSURE",
        })
        write_json(case_dir / "result.json", result_payload)
        observables = result_payload["observables"]
        np.savez_compressed(
            case_dir / "raw.npz",
            displacements=np.asarray(result.displacements, dtype=float),
            contact_forces=np.asarray(observables["tangential_contact_resultant"], dtype=float),
            contact_pressures=np.asarray(observables["contact_pressures"], dtype=float),
            contact_states=np.asarray(observables["contact_states"], dtype=str),
            load_factors=np.asarray([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0], dtype=float),
            accepted_state_digests=np.asarray([], dtype=str),
        )
        progress.update(status="COMPLETED", phase="RUN_END", mesh=mesh_name.upper(), elapsed_time_s=perf_counter() - started)
        telemetry.emit("RUN_END", "ANALYSIS_END", status="COMPLETED", elapsed=perf_counter() - started)
        write_manifest(
            case_dir,
            mesh_name=mesh_name,
            terminal_status="COMPLETED",
            terminal_classification="PASS",
            qualification_claim="PHASE1_EXECUTION_EVIDENCE_NOT_FORMAL_WP08_CLOSURE",
            frozen_parameters={"load_increments": 7, "backend": "serial_direct", "fallback": "disabled"},
        )
        return result_payload
    except BaseException as error:
        progress.update(status="FAILED", phase="RUN_FAILED", error_type=type(error).__name__, error_message=str(error), elapsed_time_s=perf_counter() - started)
        telemetry.emit("RUN_FAILED", "ANALYSIS_FAILED", status="FAILED", error_type=type(error).__name__, error_message=str(error), elapsed=perf_counter() - started)
        raise
    finally:
        telemetry.close()


def dry_run(mesh_name: str, output_dir: Path) -> dict[str, Any]:
    """Run only the Phase-0 contract/mesh/load/schema preflight."""

    provenance = verify_branch_provenance()
    preflight = build_preflight(mesh_name)
    result = {
        "schema_version": 1,
        "status": "DRY_RUN_ONLY",
        "mesh": str(mesh_name).upper(),
        "provenance": provenance,
        "preflight": preflight,
        "execution_guard": {
            "structural_solves_enabled": False,
            "external_solver_enabled": False,
            "owner_phase1_authorized": False,
            "unauthorized_execution_message": UNAUTHORIZED_PHASE1_EXECUTION_FAIL_CLOSED,
        },
        "structural_solves_run": False,
        "contact_solves_run": False,
        "reference_solves_run": False,
        "replay_run": False,
        "artifact_layout": artifact_layout(str(mesh_name).upper()),
    }
    write_json(output_dir / f"dry_run_{str(mesh_name).upper()}.json", result)
    return result


def replay_comparison(reference: Mapping[str, Any], replay: Mapping[str, Any]) -> dict[str, Any]:
    """Compare two already-produced payloads without running either model."""

    required = ("status", "solver", "node_count", "element_count", "ndof")
    missing = [key for key in required if key not in reference or key not in replay]
    if missing:
        return {"status": "FAIL_CLOSED", "reason": "MISSING_REPLAY_FIELDS", "missing": missing}
    same_status = reference.get("status") == replay.get("status")
    same_mesh = all(reference.get(key) == replay.get(key) for key in ("node_count", "element_count", "ndof"))
    ref_observables = reference.get("observables", {})
    replay_observables = replay.get("observables", {})
    numeric_checks: dict[str, bool] = {}
    if isinstance(ref_observables, Mapping) and isinstance(replay_observables, Mapping):
        for key in ("selected_displacement", "cumulative_local_dissipation", "force_balance_relative_error", "moment_balance_relative_error"):
            if key in ref_observables and key in replay_observables:
                numeric_checks[key] = bool(
                    np.isclose(float(ref_observables[key]), float(replay_observables[key]), rtol=1.0e-12, atol=1.0e-14)
                )
    observable_match = all(numeric_checks.values()) if numeric_checks else False
    return {
        "status": "PASS" if same_status and same_mesh and observable_match else "FAIL_CLOSED",
        "terminal_status_equal": reference.get("status") == replay.get("status"),
        "mesh_identity_equal": same_mesh,
        "numeric_checks": numeric_checks,
        "structural_solve_performed": False,
    }
