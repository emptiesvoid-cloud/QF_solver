"""Materialize SHA-bound per-case records for Owner-authorized WP07-D R1.

The script only creates authorization JSON files. It does not launch a solve,
reference, replay, WP07-E, push, or merge.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.wp07d_execution_binding import (  # noqa: E402
    EXPECTED_LEVELS,
    EXPECTED_ROUTES,
    FORMAL_REBIND_R1_BINDING_PATH,
    FORMAL_REBIND_R1_REPLAY_GATE_PATH,
    _file_sha256,
    coordinate_grading_from_authorization,
    formal_contract_identity,
    load_binding,
    mesh_axis_fractions_from_authorization,
    mesh_cell_counts_from_authorization,
    penalty_integration_from_authorization,
    validate_authorized_execution_source,
    validate_binding,
    validate_formal_requalification_authorization,
)

AUTH_ROOT = Path("qualification/0_2_9/wp07d_formal_rebind_r1/authorizations")
KINDS = ("PRIMARY_PRODUCTION", "INDEPENDENT_REFERENCE")
REPLAY_ROOT = Path("qualification/0_2_9/wp07d_formal_rebind_r1/authorizations/REPLAY")


def _git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _relative_mesh_axis_fractions(binding: dict[str, Any], level: str) -> dict[str, list[float]] | None:
    mesh = binding["mesh_definition"]
    expected = mesh.get("axis_fractions_by_level", {}).get(level)
    if expected is None:
        return None
    return {axis: list(expected[axis]) for axis in ("x", "y", "z")}


def _record(
    *,
    binding: dict[str, Any],
    binding_path: Path,
    contract_identity: dict[str, Any],
    execution_sha: str,
    kind: str,
    route: str,
    mesh: str,
) -> dict[str, Any]:
    production = kind in {"PRIMARY_PRODUCTION", "REPLAY"}
    record: dict[str, Any] = {
        "schema_version": 1,
        "artifact_id": f"QF-029-WP07-D-R1-AUTH-{kind}-{route}-{mesh}",
        "status": "OWNER_AUTHORIZED_FROZEN_CASE",
        "token": binding["authorization"]["token"],
        "authorization_basis": "OWNER_AUTHORIZES_FORMAL_WP07D_REQUALIFICATION_AFTER_REBIND",
        "authorized_base_sha": binding["governing"]["authorized_base_sha"],
        "execution_sha": execution_sha,
        "binding_path": binding_path.relative_to(ROOT).as_posix(),
        "binding_file_sha256": _file_sha256(binding_path),
        "formal_contract_path": contract_identity["path"],
        "formal_contract_file_sha256": contract_identity["file_sha256"],
        "owner_decision_path": contract_identity["owner_decision_path"],
        "owner_decision_file_sha256": contract_identity["owner_decision_sha256"],
        "policy_digest": binding["governing"]["policy_digest"],
        "route": route,
        "mesh": mesh,
        "execution_kind": kind,
        "structural_solves_allowed": production,
        "independent_references_allowed": not production,
        "replay_allowed": kind == "REPLAY",
        "wp07e_allowed": False,
        "coordinate_grading_exponent": float(binding["mesh_definition"]["coordinate_grading_exponent"]),
        "mesh_cell_counts": list(binding["mesh_definition"]["cell_counts_by_level"][mesh]),
        "mesh_axis_fractions": _relative_mesh_axis_fractions(binding, mesh),
        "owner_instruction": (
            "Run only this exact replay after the SHA-pinned production/reference gate passes. "
            "Do not infer formal points; do not run WP07-E, push, or merge."
            if kind == "REPLAY"
            else "Run only this production case or its independent reference under formal WP07-D R1. "
            "Do not infer formal points; do not run WP07-E, push, or merge."
        ),
    }
    if kind == "REPLAY":
        gate_path = FORMAL_REBIND_R1_REPLAY_GATE_PATH
        record["replay_gate_path"] = gate_path.relative_to(ROOT).as_posix()
        record["replay_gate_file_sha256"] = _file_sha256(gate_path)
    if route == "PENALTY":
        record["penalty_integration"] = penalty_integration_from_authorization(
            binding,
            {"penalty_integration": binding["routes"]["PENALTY"]["penalty_integration"]},
            route=route,
        )
    validate_formal_requalification_authorization(
        record,
        binding,
        binding_path,
        route=route,
        mesh=mesh,
        execution_kind=kind,
    )
    if mesh_cell_counts_from_authorization(binding, record, level=mesh) != tuple(record["mesh_cell_counts"]):
        raise ValueError(f"Generated {kind} {route}/{mesh} authorization has the wrong mesh cell counts.")
    coordinate_grading_from_authorization(binding, record)
    mesh_axis_fractions_from_authorization(binding, record, level=mesh)
    return record


def build() -> dict[str, Any]:
    binding_path = FORMAL_REBIND_R1_BINDING_PATH
    binding = load_binding(binding_path)
    validate_binding(binding)
    identity = formal_contract_identity(binding)
    if identity is None:
        raise ValueError("The formal WP07-D R1 contract is unavailable.")
    execution_sha = _git("rev-parse", "HEAD")
    validate_authorized_execution_source({"execution_sha": execution_sha})
    planned: list[tuple[Path, dict[str, Any]]] = []
    for kind in KINDS:
        for route in EXPECTED_ROUTES:
            for mesh in EXPECTED_LEVELS:
                record = _record(
                    binding=binding,
                    binding_path=binding_path,
                    contract_identity=identity,
                    execution_sha=execution_sha,
                    kind=kind,
                    route=route,
                    mesh=mesh,
                )
                destination = AUTH_ROOT / kind / f"{route}_{mesh}.json"
                planned.append((destination, record))
    existing = [path.as_posix() for path, _ in planned if (ROOT / path).exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite formal WP07-D R1 authorizations: {existing}")
    for relative_path, record in planned:
        path = ROOT / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + "\n")
            stream.flush()
    return {
        "status": "PASS_PER_CASE_AUTHORIZATIONS_CREATED_NO_SOLVES_RUN",
        "execution_sha": execution_sha,
        "binding_sha256": _file_sha256(binding_path),
        "formal_contract_sha256": identity["file_sha256"],
        "authorization_count": len(planned),
        "production_cases": 6,
        "independent_reference_cases": 6,
        "replay_authorizations_created": 0,
        "wp07e_authorized": False,
        "authorizations": [
            {"path": path.as_posix(), "sha256": _file_sha256(ROOT / path)}
            for path, _ in planned
        ],
    }


def build_replay_authorizations() -> dict[str, Any]:
    """Create only route-specific replay records after recomputing the raw-evidence gates."""

    from scripts.analyze_wp07d_formal_rebind_r1 import build_pre_replay_report

    gate_path = FORMAL_REBIND_R1_REPLAY_GATE_PATH
    if not gate_path.is_file():
        raise FileNotFoundError("The formal R1 pre-replay evidence gate does not exist.")
    binding_path = FORMAL_REBIND_R1_BINDING_PATH
    binding = load_binding(binding_path)
    validate_binding(binding)
    identity = formal_contract_identity(binding)
    if identity is None:
        raise ValueError("The formal WP07-D R1 contract is unavailable.")
    execution_sha = _git("rev-parse", "HEAD")
    validate_authorized_execution_source({"execution_sha": execution_sha})
    saved_gate = json.loads(gate_path.read_text(encoding="utf-8"))
    fresh_gate = build_pre_replay_report(binding_path)
    if saved_gate != fresh_gate:
        raise ValueError("Saved replay gate differs from a fresh analysis of the current raw evidence.")
    if (
        saved_gate.get("execution_sha") != execution_sha
        or saved_gate.get("binding_file_sha256") != _file_sha256(binding_path)
        or saved_gate.get("formal_contract_provenance", {}).get("file_sha256") != identity["file_sha256"]
    ):
        raise ValueError("Replay gate source, contract, or binding provenance is stale.")

    planned: list[tuple[Path, dict[str, Any]]] = []
    skipped: dict[str, str] = {}
    for route in EXPECTED_ROUTES:
        route_gate = saved_gate.get("routes", {}).get(route, {})
        if route_gate.get("status") != "PASS_READY_FOR_REPLAY":
            skipped[route] = "ROUTE_GATES_NOT_PASS"
            continue
        mesh = str(binding["routes"][route]["replay_level"])
        record = _record(
            binding=binding,
            binding_path=binding_path,
            contract_identity=identity,
            execution_sha=execution_sha,
            kind="REPLAY",
            route=route,
            mesh=mesh,
        )
        planned.append((REPLAY_ROOT / f"{route}_{mesh}.json", record))
    if not planned:
        return {
            "status": "FAIL_CLOSED_NO_REPLAY_ROUTE_PASSED",
            "execution_sha": execution_sha,
            "replay_authorizations_created": 0,
            "skipped_routes": skipped,
            "structural_solves_run": False,
            "replay_run": False,
        }
    existing = [path.as_posix() for path, _ in planned if (ROOT / path).exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite formal WP07-D R1 replay authorizations: {existing}")
    for relative_path, record in planned:
        path = ROOT / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + "\n")
            stream.flush()
    return {
        "status": "PASS_ROUTE_GATED_REPLAY_AUTHORIZATIONS_CREATED_NO_SOLVES_RUN",
        "execution_sha": execution_sha,
        "binding_sha256": _file_sha256(binding_path),
        "formal_contract_sha256": identity["file_sha256"],
        "replay_gate_sha256": _file_sha256(gate_path),
        "replay_authorizations_created": len(planned),
        "authorized_replays": [
            {"path": path.as_posix(), "sha256": _file_sha256(ROOT / path)}
            for path, _ in planned
        ],
        "skipped_routes": skipped,
        "wp07e_authorized": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorize-replays", action="store_true")
    args = parser.parse_args()
    result = build_replay_authorizations() if args.authorize_replays else build()
    print(json.dumps(result, indent=2, sort_keys=True))
