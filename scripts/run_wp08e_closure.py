"""Run the bounded WP08-E replay, restart and negative-control closure pack."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping

import numpy as np

from solveur.core.errors import InputValidationError, MeshValidationError
from solveur.core.solvers.static import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader
from solveur.contact.solver import FrictionlessActiveSetSolver


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = REPOSITORY_ROOT / "qualification" / "0_2_9" / "wp08d_phase1_hybrid_stick_slip_reference_replay"
FROZEN_HISTORY = [[0.0, 1.0], [0.2, 1.0], [1.0, 1.0], [0.2, 1.0], [-0.2, 1.0], [-1.0, 1.0], [0.0, 1.0]]
AUTHORIZED_BASE_SHA = "7b93e71bab06a0e58108bd2479cd46808d533b67"
REMEDIATION_SHA = "794de436c13364c16aa85b2ae2c9e7bb09957829"
CONTRACT_DIGEST = "d2d9533c873000996ab3fad992c653dfed37f533ed12d85af97b3696740f179a"
POLICY_DIGEST = "93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac"


def _model() -> dict[str, Any]:
    return {
        "analysis": {
            "type": "linear_static",
            "method": "direct",
            "contact_max_iterations": 16,
            "contact_friction_tolerance": 1.0e-11,
            "contact_load_history": FROZEN_HISTORY,
        },
        "nodes": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.25, 0.25, 0.1]],
        "elements": [],
        "materials": {},
        "fixed_dofs": [
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 1, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UY"]},
        ],
        "springs": [{"node_a": 3, "dofs": ["UX", "UZ"], "stiffness": [1000.0, 1000.0]}],
        "loads": [
            {"node": 3, "dof": "UX", "value": 200.0},
            {"node": 3, "dof": "UZ", "value": -200.0},
        ],
        "contacts": [{
            "name": "wp08e_rough_plane",
            "slave_node": 3,
            "master_nodes": [0, 1, 2],
            "friction_coefficient": 0.5,
            "tangential_stiffness": 10000.0,
        }],
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _git_value(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _verify_manifest(path: Path) -> bool:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        for item in manifest["files"]:
            artifact = path.parent / item["relative_path"]
            if artifact.stat().st_size != item["size_bytes"] or hashlib.sha256(artifact.read_bytes()).hexdigest() != item["sha256"]:
                return False
        return True
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False


def _run_restart(output_dir: Path) -> dict[str, Any]:
    baseline = LinearStaticSolver().solve(JsonModelReader().from_dict(_model()))
    restart_dir = output_dir / "restart"
    restart_dir.mkdir(parents=True, exist_ok=True)
    accepted_step4 = restart_dir / "accepted_step4.json"
    resumed_checkpoint = restart_dir / "resumed_final.json"
    interrupted_data = _model()
    interrupted_data["analysis"] = {**interrupted_data["analysis"], "contact_checkpoint_path": str(accepted_step4)}
    original = getattr(FrictionlessActiveSetSolver, "_solve_friction_increment")

    def stop_after_step_four(*args: Any, **kwargs: Any) -> Any:
        if kwargs.get("step") == 5:
            raise RuntimeError("WP08-E controlled interruption after accepted step four")
        return original(*args, **kwargs)

    setattr(FrictionlessActiveSetSolver, "_solve_friction_increment", staticmethod(stop_after_step_four))
    try:
        try:
            LinearStaticSolver().solve(JsonModelReader().from_dict(interrupted_data))
        except RuntimeError as error:
            if "accepted step four" not in str(error):
                raise
    finally:
        setattr(FrictionlessActiveSetSolver, "_solve_friction_increment", staticmethod(original))

    if not accepted_step4.is_file():
        raise RuntimeError("WP08-E did not persist the accepted step-four checkpoint.")
    resumed_data = _model()
    resumed_data["analysis"] = {
        **resumed_data["analysis"],
        "contact_restart_from": str(accepted_step4),
        "contact_checkpoint_path": str(resumed_checkpoint),
    }
    resumed = LinearStaticSolver().solve(JsonModelReader().from_dict(resumed_data))
    restart_details = resumed.solver["contact"]["restart"]
    return {
        "status": "PASS" if np.allclose(resumed.displacements, baseline.displacements, rtol=0.0, atol=1.0e-12) and restart_details["restarted_from_step"] == 4 else "FAIL_CLOSED",
        "restarted_from_step": restart_details["restarted_from_step"],
        "resumed_steps": restart_details["accepted_steps_written"],
        "displacement_max_abs_delta": float(np.max(np.abs(resumed.displacements - baseline.displacements))),
        "cumulative_dissipation_delta": abs(float(resumed.solver["contact"]["cumulative_local_dissipation"]) - float(baseline.solver["contact"]["cumulative_local_dissipation"])),
        "accepted_checkpoint": str(accepted_step4),
        "resumed_checkpoint": str(resumed_checkpoint),
    }


def _run_negative_controls() -> dict[str, str]:
    controls: dict[str, str] = {}
    for name, value in (("negative_mu", -0.1), ("nonfinite_mu", float("nan"))):
        data = _model()
        data["contacts"][0]["friction_coefficient"] = value
        try:
            JsonModelReader().from_dict(data)
        except InputValidationError:
            controls[name] = "PASS_FAIL_CLOSED"
        else:
            controls[name] = "FAIL_OPEN"

    updated = _model()
    updated["analysis"] = {**updated["analysis"], "contact_search_mode": "updated"}
    try:
        LinearStaticSolver().solve(JsonModelReader().from_dict(updated))
    except MeshValidationError:
        controls["updated_search_friction"] = "PASS_FAIL_CLOSED"
    else:
        controls["updated_search_friction"] = "FAIL_OPEN"

    missing = _model()
    missing["analysis"] = {**missing["analysis"], "contact_restart_from": "missing-wp08e-checkpoint.json"}
    try:
        LinearStaticSolver().solve(JsonModelReader().from_dict(missing))
    except InputValidationError:
        controls["missing_restart_state"] = "PASS_FAIL_CLOSED"
    else:
        controls["missing_restart_state"] = "FAIL_OPEN"
    return controls


def run(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    m2_final = json.loads((EVIDENCE_ROOT / "wp08d_m2_independent_reference_replay_final.json").read_text(encoding="utf-8"))
    m3_final = json.loads((EVIDENCE_ROOT / "wp08d_m3_production_reference_replay_final.json").read_text(encoding="utf-8"))
    replay_m2 = EVIDENCE_ROOT / "wp08d_m2_replay_comparison.json"
    replay_m3 = EVIDENCE_ROOT / "wp08d_m3_replay_comparison.json"
    replay_checks = {
        "M2": m2_final.get("replay", {}).get("status") == "PASS"
        and json.loads(replay_m2.read_text(encoding="utf-8")).get("status") == "PASS"
        if replay_m2.is_file()
        else False,
        "M3": m3_final.get("replay", {}).get("status") == "PASS"
        and json.loads(replay_m3.read_text(encoding="utf-8")).get("status") == "PASS"
        if replay_m3.is_file()
        else False,
    }
    manifest_checks = {
        "M2_replay": _verify_manifest(EVIDENCE_ROOT / "replay" / "M2" / "manifest.json"),
        "M3_replay": _verify_manifest(EVIDENCE_ROOT / "replay" / "M3" / "manifest.json"),
    }
    restart = _run_restart(output_dir)
    negative_controls = _run_negative_controls()
    status = "PASS" if all(replay_checks.values()) and all(manifest_checks.values()) and restart["status"] == "PASS" and all(value == "PASS_FAIL_CLOSED" for value in negative_controls.values()) else "FAIL_CLOSED"
    payload: dict[str, Any] = {
        "schema_version": 1,
        "status": status,
        "scope": "WP08-E bounded replay, accepted-state restart, negative controls and fail-closed closure",
        "authorized_base_sha": AUTHORIZED_BASE_SHA,
        "execution_sha": _git_value("rev-parse", "HEAD"),
        "branch": _git_value("branch", "--show-current"),
        "remediation_sha": REMEDIATION_SHA,
        "evidence_commit_sha": None,
        "final_sha": None,
        "remote_head": "NOT_PUSHED",
        "contract_digest": CONTRACT_DIGEST,
        "policy_digest": POLICY_DIGEST,
        "replay_checks": replay_checks,
        "manifest_checks": manifest_checks,
        "restart": restart,
        "negative_controls": negative_controls,
        "production_mechanics_changed": True,
        "mechanics_scope": "accepted frictional-contact checkpoint persistence and validation only",
        "thresholds_changed": False,
        "solver_parameters_changed": False,
        "fallback_changed": False,
        "full_test_suite_run": False,
        "qualification_claim": "WP08-E_EVIDENCE_PENDING_OWNER_REVIEW",
        "formal_points": "0/1",
    }
    _write_json(output_dir / "wp08e_closure_final.json", payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=REPOSITORY_ROOT / "qualification" / "0_2_9" / "wp08e_closure")
    args = parser.parse_args()
    try:
        payload = run(args.output_dir)
    except (InputValidationError, MeshValidationError, OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        print(f"WP08E_FAIL_CLOSED: {error}")
        return 3
    print(f"WP08E_{payload['status']} output={args.output_dir}")
    return 0 if payload["status"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
