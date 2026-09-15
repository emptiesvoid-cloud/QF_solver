"""Audit the bounded WP08 A-E evidence without rerunning structural campaigns."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
QUALIFICATION_ROOT = REPOSITORY_ROOT / "qualification" / "0_2_9"
DOCUMENT_ROOT = REPOSITORY_ROOT / "docs" / "verification" / "0_2_9"
WP08D_EVIDENCE_ROOT = QUALIFICATION_ROOT / "wp08d_phase1_hybrid_stick_slip_reference_replay"

GOVERNING_BASE_SHA = "7b93e71bab06a0e58108bd2479cd46808d533b67"
POLICY_DIGEST = "93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac"
CONTRACT_DIGEST = "d2d9533c873000996ab3fad992c653dfed37f533ed12d85af97b3696740f179a"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


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
        manifest = _read_json(path)
        files = manifest["files"]
        if not isinstance(files, list):
            return False
        for item in files:
            if not isinstance(item, dict):
                return False
            relative_path = item["relative_path"]
            artifact = path.parent / relative_path
            if not artifact.is_file():
                return False
            if artifact.stat().st_size != item["size_bytes"]:
                return False
            if hashlib.sha256(artifact.read_bytes()).hexdigest() != item["sha256"]:
                return False
        return True
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False


def _check_json(path: Path, *, work_package: str, allowed_statuses: set[str]) -> dict[str, Any]:
    payload = _read_json(path)
    status = payload.get("status")
    return {
        "exists": path.is_file(),
        "work_package": payload.get("work_package") == work_package,
        "status": status,
        "status_accepted": status in allowed_statuses,
        "policy_digest": payload.get("policy_digest") == POLICY_DIGEST
        or payload.get("controlled_provenance", {}).get("governing_policy_digest") == POLICY_DIGEST,
        "path": str(path),
    }


def _check_d_evidence() -> dict[str, Any]:
    m1_final_path = QUALIFICATION_ROOT / "wp08d_phase1" / "wp08d_m1_phase1_final.json"
    m2_final_path = WP08D_EVIDENCE_ROOT / "wp08d_m2_independent_reference_replay_final.json"
    m3_final_path = WP08D_EVIDENCE_ROOT / "wp08d_m3_production_reference_replay_final.json"
    m2_replay_path = WP08D_EVIDENCE_ROOT / "wp08d_m2_replay_comparison.json"
    m3_replay_path = WP08D_EVIDENCE_ROOT / "wp08d_m3_replay_comparison.json"
    m1 = _read_json(m1_final_path)
    m2 = _read_json(m2_final_path)
    m3 = _read_json(m3_final_path)
    m2_replay = _read_json(m2_replay_path)
    m3_replay = _read_json(m3_replay_path)
    manifest_paths = {
        "M1_production": QUALIFICATION_ROOT / "wp08d_phase1" / "M1" / "manifest.json",
        "M1_reference": QUALIFICATION_ROOT / "wp08d_phase1" / "independent_reference" / "M1" / "manifest.json",
        "M1_replay": QUALIFICATION_ROOT / "wp08d_phase1" / "replay" / "M1" / "manifest.json",
        "M2_production": QUALIFICATION_ROOT / "wp08d_phase1_hybrid_stick_slip_requalification" / "production" / "M2" / "manifest.json",
        "M2_reference": QUALIFICATION_ROOT / "wp08d_phase1_hybrid_stick_slip_requalification" / "independent_reference" / "M2" / "manifest.json",
        "M2_replay": WP08D_EVIDENCE_ROOT / "replay" / "M2" / "manifest.json",
        "M3_production": WP08D_EVIDENCE_ROOT / "production" / "M3" / "manifest.json",
        "M3_reference": WP08D_EVIDENCE_ROOT / "independent_reference" / "M3" / "manifest.json",
        "M3_replay": WP08D_EVIDENCE_ROOT / "replay" / "M3" / "manifest.json",
    }
    checks = {
        "M1_production": m1.get("production", {}).get("status") == "PASS" and m1.get("production", {}).get("accepted_increments") == 7,
        "M1_reference": m1.get("independent_reference", {}).get("status") == "PASS",
        "M1_replay": m1.get("replay", {}).get("status") == "PASS",
        "M2_production": m2.get("independent_reference", {}).get("accepted_increments") == "7/7",
        "M2_reference": m2.get("independent_reference", {}).get("status") == "PASS_REFERENCE",
        "M2_replay": m2.get("replay", {}).get("status") == "PASS" and m2_replay.get("status") == "PASS",
        "M3_production": m3.get("production", {}).get("status") == "PASS",
        "M3_reference": m3.get("independent_reference", {}).get("status") == "PASS_REFERENCE",
        "M3_replay": m3.get("replay", {}).get("status") == "PASS" and m3_replay.get("status") == "PASS",
        "contract_digest": m2.get("contract_digest") == CONTRACT_DIGEST and m3.get("contract_digest") == CONTRACT_DIGEST,
        "policy_digest": m2.get("policy_digest") == POLICY_DIGEST and m3.get("policy_digest") == POLICY_DIGEST,
        "M1_contract_digest": m1.get("contract_digest") == CONTRACT_DIGEST and m1.get("policy_digest") == POLICY_DIGEST,
        "production_reference_independence": m2.get("independent_reference", {}).get("production_contact_routines_called") is False
        and m3.get("independent_reference", {}).get("production_contact_routines_called") is False,
    }
    manifest_checks = {name: _verify_manifest(path) for name, path in manifest_paths.items()}
    checks["manifests"] = all(manifest_checks.values())
    return {
        "status": "PASS_CANDIDATE_WITH_LIMITATIONS" if all(checks.values()) else "FAIL_CLOSED",
        "checks": checks,
        "manifest_checks": manifest_checks,
        "m2_source_sha": m2.get("execution_source_sha"),
        "m3_authorization_commit": m3.get("execution_authorization_commit"),
        "limitations": [
            "M2/M3 are consumed as already-authorized evidence; no new structural solve is run by this closure audit.",
            "Formal points remain pending Owner review.",
        ],
    }


def run(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    source_sha = _git_value("rev-parse", "HEAD")
    branch = _git_value("branch", "--show-current")
    evidence = {
        "A": _check_json(
            QUALIFICATION_ROOT / "wp08a_frictional_contact_readiness.json",
            work_package="WP08-A",
            allowed_statuses={"PREPARATION_ONLY", "PASS_CANDIDATE_WITH_LIMITATIONS"},
        ),
        "B": _check_json(
            QUALIFICATION_ROOT / "wp08b_frictional_identities_rollback.json",
            work_package="WP08-B",
            allowed_statuses={"PASS_CANDIDATE_WITH_LIMITATIONS"},
        ),
        "C": _check_json(
            QUALIFICATION_ROOT / "wp08c_friction_tangent_dissipation.json",
            work_package="WP08-C",
            allowed_statuses={"PASS_CANDIDATE_WITH_LIMITATIONS"},
        ),
    }
    evidence["D"] = {
        "work_package": "WP08-D",
        **_check_d_evidence(),
    }
    e_path = QUALIFICATION_ROOT / "wp08e_closure" / "wp08e_closure_final.json"
    e = _read_json(e_path)
    evidence["E"] = {
        "work_package": "WP08-E",
        "status": e.get("status"),
        "status_accepted": e.get("status") == "PASS",
        "path": str(e_path),
        "restart": e.get("restart"),
        "negative_controls": e.get("negative_controls"),
        "replay_checks": e.get("replay_checks"),
    }
    component_pass = {
        key: bool(value.get("status_accepted"))
        and bool(value.get("policy_digest", True))
        for key, value in evidence.items()
    }
    component_pass["D"] = evidence["D"]["status"] == "PASS_CANDIDATE_WITH_LIMITATIONS"
    component_pass["E"] = evidence["E"]["status_accepted"]
    all_pass = all(component_pass.values())
    payload: dict[str, Any] = {
        "schema_version": 1,
        "work_package": "WP08",
        "status": "PASS_CANDIDATE_OWNER_REVIEW_REQUIRED" if all_pass else "FAIL_CLOSED",
        "authorized_base_sha": GOVERNING_BASE_SHA,
        "execution_sha": source_sha,
        "branch": branch,
        "contract_digest": CONTRACT_DIGEST,
        "policy_digest": POLICY_DIGEST,
        "component_status": {
            "WP08-A": "PASS_CANDIDATE_WITH_LIMITATIONS" if component_pass["A"] else "FAIL_CLOSED",
            "WP08-B": "PASS_CANDIDATE_WITH_LIMITATIONS" if component_pass["B"] else "FAIL_CLOSED",
            "WP08-C": "PASS_CANDIDATE_WITH_LIMITATIONS" if component_pass["C"] else "FAIL_CLOSED",
            "WP08-D": "PASS_CANDIDATE_WITH_LIMITATIONS" if component_pass["D"] else "FAIL_CLOSED",
            "WP08-E": "PASS_CANDIDATE" if component_pass["E"] else "FAIL_CLOSED",
        },
        "candidate_points": {
            "WP08-A": "1/1",
            "WP08-B": "2/2",
            "WP08-C": "2/2",
            "WP08-D": "2/2",
            "WP08-E": "1/1",
            "WP08": "8/8" if all_pass else "0/8",
        },
        "official_points_before_owner_review": "0/8",
        "evidence": evidence,
        "production_mechanics_changed": True,
        "mechanics_scope": "authorized friction mechanics plus accepted-state checkpoint persistence/validation",
        "thresholds_changed": False,
        "solver_parameters_changed": False,
        "fallback_changed": False,
        "full_test_suite_run": False,
        "structural_solves_run_by_closure": False,
        "next_step": "Owner review and explicit point attribution; do not self-merge or self-award.",
    }
    json_path = output_dir / "wp08abcd_closure_final.json"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=QUALIFICATION_ROOT / "wp08_closure",
    )
    args = parser.parse_args()
    try:
        payload = run(args.output_dir)
    except (OSError, subprocess.SubprocessError, ValueError, json.JSONDecodeError) as error:
        print(f"WP08ABCD_FAIL_CLOSED: {error}")
        return 3
    print(f"WP08ABCD_{payload['status']} output={args.output_dir}")
    return 0 if payload["status"] == "PASS_CANDIDATE_OWNER_REVIEW_REQUIRED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
