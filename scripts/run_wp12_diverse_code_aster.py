"""Execute frozen WP12 R3.6 diverse-topology Code_Aster correlations serially."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts import run_wp12_expanded_code_aster as engine  # noqa: E402
from scripts.wp12_diverse_models import (  # noqa: E402
    FAMILIES,
    code_aster_command_text,
    code_aster_mesh_text,
    case_catalog,
)

class CampaignError(RuntimeError):
    """Raised when the frozen R3.6 contract or execution preconditions fail."""


def _git(repo_root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


def _verify_prior_attempts(contract: dict[str, Any], repo_root: Path) -> None:
    attempts = contract.get("supersedes_failed_attempts")
    if not isinstance(attempts, list) or len(attempts) != 2:
        raise CampaignError("R3.6 R2 must bind both preserved failed attempts.")
    expected_ids = {"r3_6_attempt1_serializer_recursion", "r3_6_r1_force_node_label"}
    if {row.get("attempt_id") for row in attempts if isinstance(row, dict)} != expected_ids:
        raise CampaignError("R3.6 R2 prior-attempt lineage is incomplete or unexpected.")

    for attempt in attempts:
        if not isinstance(attempt, dict):
            raise CampaignError("R3.6 R2 prior-attempt record is malformed.")
        paths: dict[str, Path] = {}
        for field in ("contract_path", "manifest_path", "audit_path", "summary_path", "raw_root"):
            relative = Path(str(attempt.get(field, "")))
            resolved = (repo_root / relative).resolve()
            if not relative.parts or repo_root not in resolved.parents:
                raise CampaignError(f"R3.6 R2 prior-attempt path is invalid: {field}")
            paths[field] = resolved
        for field in ("contract_path", "manifest_path", "audit_path", "summary_path"):
            path = paths[field]
            digest_field = f"{field.removesuffix('_path')}_sha256"
            if not path.is_file() or engine.sha256_file(path) != attempt.get(digest_field):
                raise CampaignError(f"R3.6 R2 prior-attempt hash mismatch: {field}")

        prior_contract = engine.load_json(paths["contract_path"])
        prior_manifest = engine.load_json(paths["manifest_path"])
        prior_audit = engine.load_json(paths["audit_path"])
        prior_summary = engine.load_json(paths["summary_path"])
        if (
            prior_audit.get("audit_status") != "FAIL_CLOSED"
            or prior_audit.get("case_count") != 144
            or prior_audit.get("case_pass_count") != 0
            or prior_audit.get("contract_sha256") != attempt.get("contract_sha256")
            or prior_audit.get("manifest_sha256") != attempt.get("manifest_sha256")
            or prior_summary.get("status") != "FAIL_CLOSED"
            or prior_summary.get("candidate_cases_passed") != 0
            or prior_summary.get("contract_sha256") != attempt.get("contract_sha256")
            or prior_contract.get("revision") != attempt.get("revision")
        ):
            raise CampaignError("R3.6 R2 prior-attempt failure classification is inconsistent.")

        entries = prior_manifest.get("files")
        if not isinstance(entries, dict) or not entries:
            raise CampaignError("R3.6 R2 prior-attempt manifest is empty or invalid.")
        raw_root = paths["raw_root"]
        actual = {
            path.relative_to(raw_root).as_posix()
            for path in raw_root.rglob("*")
            if path.is_file()
        }
        if actual != set(entries):
            raise CampaignError("R3.6 R2 prior-attempt raw file set differs from its manifest.")
        for relative, entry in entries.items():
            path = raw_root / relative
            if (
                not path.is_file()
                or path.stat().st_size != entry.get("size_bytes")
                or engine.sha256_file(path) != entry.get("sha256")
            ):
                raise CampaignError(f"R3.6 R2 prior-attempt raw hash mismatch: {relative}")

        first_case_id = "tet4_l_section_beam_h1_axial_x"
        first = prior_summary.get("cases", {}).get(first_case_id, {})
        if attempt["attempt_id"] == "r3_6_attempt1_serializer_recursion":
            if (
                prior_summary.get("attempted_case_count") != 1
                or prior_summary.get("not_started_case_count") != 143
                or "RecursionError" not in first.get("error", "")
            ):
                raise CampaignError("R3.6 attempt-1 lineage is not the preserved pre-solver failure.")
            case_root = raw_root / first_case_id
            if any((case_root / name).exists() for name in ("process.json", "container.cid", "aster_raw.json")):
                raise CampaignError("R3.6 attempt-1 unexpectedly contains Code_Aster process evidence.")
        else:
            process = engine.load_json(raw_root / first_case_id / "process.json")
            if (
                prior_summary.get("attempted_case_count") != 1
                or prior_summary.get("not_started_case_count") != 143
                or first.get("status") != "FAIL_CLOSED_EXECUTION"
                or process.get("exit_code") != 2
                or (raw_root / first_case_id / "aster_raw.json").exists()
            ):
                raise CampaignError("R3.6 R1 lineage is not the preserved Code_Aster input failure.")


def _case_record(case: Any) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "family": case.family,
        "geometry": case.geometry,
        "dimensions_m": list(case.dimensions),
        "mesh": case.mesh,
        "divisions": list(case.divisions),
        "load_case": case.load_case,
        "resultant_N": list(case.resultant),
        "load_area_m2": case.load_area,
        "load_moment_origin_Nm": list(case.load_moment),
        "model_fingerprint": case.fingerprint,
        "nodes": len(case.model.nodes),
        "elements": len(case.connectivity),
        "dofs": int(case.system.stiffness.shape[0]),
    }


def _run_case(case: Any, case_root: Path, contract: dict[str, Any], readiness: dict[str, Any]) -> dict[str, Any]:
    """Call the stable R3 execution routine with R3.6-only serializers."""
    previous_mesh_text = engine._mesh_text
    previous_comm_text = engine._comm_text
    engine._mesh_text = code_aster_mesh_text
    engine._comm_text = code_aster_command_text
    try:
        result = engine._run_case(case, case_root, contract, readiness)
    finally:
        engine._mesh_text = previous_mesh_text
        engine._comm_text = previous_comm_text
    result["geometry"] = case.geometry
    engine.write_json(case_root / "result.json", result)
    return result


def preflight(contract_path: Path, repo_root: Path) -> tuple[dict[str, Any], list[Any], dict[str, Any]]:
    contract_path, repo_root = contract_path.resolve(), repo_root.resolve()
    contract = engine.load_json(contract_path)
    engine.validate_external_configuration(contract)
    if contract.get("revision") not in {
        "R3_6_DIVERSE_TOPOLOGY_144_CASE_LINEAR_STATIC_CORRELATION",
        "R3_6_DIVERSE_TOPOLOGY_144_CASE_LINEAR_STATIC_CORRELATION_R1",
        "R3_6_DIVERSE_TOPOLOGY_144_CASE_LINEAR_STATIC_CORRELATION_R2",
    }:
        raise CampaignError("Contract revision is not WP12 R3.6 diverse topology.")
    if contract.get("status") != "FROZEN" or contract.get("execution_authorized") is not True:
        raise CampaignError("R3.6 contract is not frozen and execution-authorized.")
    if contract.get("abort_on_execution_failure") is not True or contract.get("output_overwrite_allowed") is not False:
        raise CampaignError("R3.6 fail-closed/overwrite policy is invalid.")
    if contract["revision"].endswith("_R1") and contract.get("supersedes_failed_attempt", {}).get("code_aster_process_started") is not False:
        raise CampaignError("R3.6 R1 is missing the preserved pre-solver failure lineage.")
    if contract["revision"].endswith("_R2"):
        _verify_prior_attempts(contract, repo_root)

    expected_branch = str(contract.get("branch", ""))
    if _git(repo_root, "branch", "--show-current") != expected_branch:
        raise CampaignError("Current branch differs from the frozen R3.6 branch.")
    if _git(repo_root, "status", "--porcelain"):
        raise CampaignError("Working tree must be clean before R3.6 execution.")
    base = str(contract.get("branch_base_sha", ""))
    if _git(repo_root, "rev-parse", "--verify", f"{base}^{{commit}}") != base:
        raise CampaignError("Frozen R3.6 base SHA is not resolvable.")
    if subprocess.run(["git", "merge-base", "--is-ancestor", base, "HEAD"], cwd=repo_root, check=False).returncode:
        raise CampaignError("R3.6 branch does not descend from its frozen base.")
    if _git(repo_root, "rev-parse", "HEAD^") != contract.get("freeze_commit_sha"):
        raise CampaignError("Frozen R3.6 contract does not immediately follow its preparation commit.")
    if subprocess.run(["git", "diff", "--quiet", base, "HEAD", "--", "src/"], cwd=repo_root, check=False).returncode:
        raise CampaignError("R3.6 preparation changed production source.")

    source_paths = {
        "runner_sha": "scripts/run_wp12_diverse_code_aster.py",
        "model_builder_sha": "scripts/wp12_diverse_models.py",
        "auditor_sha": "scripts/audit_wp12_expanded_code_aster.py",
        "contract_builder_sha": "scripts/freeze_wp12_diverse_contract.py",
    }
    for field, relative_path in source_paths.items():
        latest = _git(repo_root, "log", "-1", "--format=%H", "--", relative_path)
        if latest != contract.get(field):
            raise CampaignError(f"Frozen {field} differs from tracked source commit.")

    cases = case_catalog()
    expected_cases = contract.get("cases")
    if not isinstance(expected_cases, list) or len(expected_cases) != len(cases) or len(cases) != 144:
        raise CampaignError("Frozen R3.6 case matrix is incomplete or has the wrong size.")
    for case, expected in zip(cases, expected_cases, strict=True):
        if _case_record(case) != expected:
            raise CampaignError(f"Generated model differs from frozen case {case.case_id}.")
    if set(contract.get("families", [])) != set(FAMILIES) or contract.get("case_count") != len(cases):
        raise CampaignError("Frozen R3.6 family or case coverage differs from generated catalog.")

    output_root = (repo_root / str(contract["output_root"])).resolve()
    manifest_path = (repo_root / str(contract["manifest_path"])).resolve()
    if repo_root not in output_root.parents or repo_root not in manifest_path.parents:
        raise CampaignError("Frozen R3.6 output paths must remain inside the repository.")
    if output_root.exists() or manifest_path.exists():
        raise CampaignError("R3.6 output already exists; refusing any overwrite or implicit resume.")

    audit_path = (repo_root / str(contract["audit_path"])).resolve()
    if repo_root not in audit_path.parents or audit_path.exists():
        raise CampaignError("Frozen R3.6 audit path escapes repository or already exists.")
    docker = shutil.which("docker")
    if docker is None:
        raise CampaignError("Docker CLI unavailable.")
    image = subprocess.run([docker, "image", "inspect", engine.IMAGE, "--format", "{{.Id}}"], capture_output=True, text=True)
    if image.returncode != 0 or image.stdout.strip() != contract.get("code_aster_image_id"):
        raise CampaignError("Pinned Code_Aster image ID is unavailable or mismatched.")
    probe = subprocess.run(
        [docker, "run", "--rm", "--entrypoint", "/bin/bash", engine.IMAGE, "-lc", engine._runtime_command(f"{engine.ASTER_RUNNER} --version")],
        capture_output=True,
        text=True,
    )
    runtime_version = probe.stdout.strip()
    if probe.returncode != 0 or not runtime_version.startswith(f"code_aster {contract['code_aster_version']} "):
        raise CampaignError("Pinned Code_Aster runtime/import preflight failed.")
    readiness = {
        "status": "PREFLIGHT_PASS",
        "branch": expected_branch,
        "execution_sha": _git(repo_root, "rev-parse", "HEAD"),
        "contract_sha256": engine.sha256_file(contract_path),
        "code_aster_image_id": image.stdout.strip(),
        "code_aster_runtime_version": runtime_version,
        "case_count": len(cases),
        "output_path_absent": True,
        "sequential_execution": True,
    }
    return readiness, cases, contract


def execute(contract_path: Path, repo_root: Path) -> dict[str, Any]:
    readiness, cases, contract = preflight(contract_path, repo_root)
    root = repo_root.resolve()
    output_root = (root / contract["output_root"]).resolve()
    manifest_path = (root / contract["manifest_path"]).resolve()
    output_root.mkdir(parents=True, exist_ok=False)
    engine.write_json(output_root / "preflight.json", readiness)
    results: dict[str, dict[str, Any]] = {}
    for index, case in enumerate(cases, start=1):
        case_root = output_root / case.case_id
        try:
            result = _run_case(case, case_root, contract, readiness)
        except Exception as exc:  # Keep failure evidence; never silently retry.
            result = {
                "status": "FAIL_CLOSED_EXECUTION",
                "case_id": case.case_id,
                "family": case.family,
                "geometry": case.geometry,
                "source_sha": readiness["execution_sha"],
                "runner_sha": contract["runner_sha"],
                "contract_sha256": readiness["contract_sha256"],
                "error": f"{type(exc).__name__}: {exc}",
            }
            if case_root.exists():
                engine.write_json(case_root / "result.json", result)
        results[case.case_id] = result
        engine.write_json(
            output_root / "progress.json",
            {
                "completed_cases": index,
                "total_cases": len(cases),
                "current_case": case.case_id,
                "current_family": case.family,
                "current_geometry": case.geometry,
                "current_mesh": case.mesh,
                "current_status": result["status"],
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            },
        )
        engine._manifest(output_root, manifest_path)
        if result.get("status") == "FAIL_CLOSED_EXECUTION":
            break

    passed = sum(row.get("status") == "PASS_CANDIDATE" for row in results.values())
    family_summary = {
        family: {
            "cases": sum(row.get("family") == family for row in results.values()),
            "passed": sum(row.get("family") == family and row.get("status") == "PASS_CANDIDATE" for row in results.values()),
            "failed": sum(row.get("family") == family and row.get("status") != "PASS_CANDIDATE" for row in results.values()),
        }
        for family in FAMILIES
    }
    geometry_summary = {
        geometry: {
            "cases": sum(row.get("geometry") == geometry for row in results.values()),
            "passed": sum(row.get("geometry") == geometry and row.get("status") == "PASS_CANDIDATE" for row in results.values()),
            "failed": sum(row.get("geometry") == geometry and row.get("status") != "PASS_CANDIDATE" for row in results.values()),
        }
        for geometry in contract["geometry_catalog_m"]
    }
    summary = {
        "work_package": "WP12",
        "campaign": f"{contract['revision']} diverse-topology same-mesh linear-static Code_Aster correlation",
        "status": "PASS_CANDIDATE_WITH_LIMITATIONS" if passed == len(cases) else "FAIL_CLOSED",
        "case_count": len(cases),
        "attempted_case_count": len(results),
        "not_started_case_count": len(cases) - len(results),
        "execution_aborted_on_error": len(results) < len(cases),
        "candidate_cases_passed": passed,
        "official_points_changed": False,
        "branch": readiness["branch"],
        "execution_sha": readiness["execution_sha"],
        "runner_sha": contract["runner_sha"],
        "model_builder_sha": contract["model_builder_sha"],
        "auditor_sha": contract["auditor_sha"],
        "contract_builder_sha": contract["contract_builder_sha"],
        "contract_sha256": readiness["contract_sha256"],
        "code_aster_image": engine.IMAGE,
        "code_aster_image_id": readiness["code_aster_image_id"],
        "code_aster_runtime_version": readiness["code_aster_runtime_version"],
        "families": family_summary,
        "geometries": geometry_summary,
        "cases": results,
        "limitations": contract["limitations"],
    }
    engine.write_json(output_root / "wp12_expanded_summary.json", summary)
    (output_root / "wp12_expanded_summary.md").write_text(
        _render_summary(summary), encoding="utf-8", newline="\n"
    )
    engine._manifest(output_root, manifest_path)
    return summary


def _render_summary(summary: dict[str, Any]) -> str:
    lines = [
        "# WP12 R3.6 — Diverse-topology Code_Aster correlation",
        "",
        f"Status: **{summary['status']}**",
        "",
        f"Cases: {summary['candidate_cases_passed']}/{summary['case_count']} PASS_CANDIDATE",
        f"Attempted: {summary['attempted_case_count']}; not started: {summary['not_started_case_count']}; aborted on execution error: {summary['execution_aborted_on_error']}",
        "",
        "| Geometry | Cases | PASS | FAIL/HOLD |",
        "|---|---:|---:|---:|",
    ]
    for geometry, record in summary["geometries"].items():
        lines.append(f"| {geometry} | {record['cases']} | {record['passed']} | {record['failed']} |")
    lines.extend(["", "Official WP12 points are unchanged; R3.6 is supplemental evidence only.", "", "## Scope limitations", ""])
    lines.extend(f"- {item}" for item in summary["limitations"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    contract_path = args.contract if args.contract.is_absolute() else repo_root / args.contract
    try:
        if args.execute:
            result = execute(contract_path, repo_root)
        else:
            readiness, cases, contract = preflight(contract_path, repo_root)
            result = {
                **readiness,
                "revision": contract["revision"],
                "case_ids": [case.case_id for case in cases],
            }
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0 if result.get("status") in {"PREFLIGHT_PASS", "PASS_CANDIDATE_WITH_LIMITATIONS"} else 2
    except (CampaignError, OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"WP12_R3_6_FAIL_CLOSED: {type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
