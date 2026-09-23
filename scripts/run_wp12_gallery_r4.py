"""Run the frozen WP12 R4 gallery correlation serially against Code_Aster."""

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

from scripts import audit_wp12_expanded_code_aster as auditor  # noqa: E402
from scripts import run_wp12_diverse_code_aster as r3_runner  # noqa: E402
from scripts import run_wp12_expanded_code_aster as engine  # noqa: E402
from scripts.wp12_gallery_models import FAMILIES, GEOMETRIES, MATERIALS, case_catalog  # noqa: E402


BRANCH = "codex/wp12-expanded-correlation-r4"
REVISION = "R4_GALLERY_864_CASES_6_TOPOLOGIES_3_MATERIALS"
EXPECTED_CASES = 864


class GalleryCampaignError(RuntimeError):
    """Raised when the frozen R4 contract or execution preconditions fail."""


def _git(repo_root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


def _case_record(case: Any) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "family": case.family,
        "geometry": case.geometry,
        "material_variant": case.material_variant,
        "material": dict(case.material),
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


def _verify_prior_r36(contract: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    prior = contract.get("extends_campaign", {})
    path_fields = {
        "contract_path": "contract_sha256",
        "manifest_path": "manifest_sha256",
        "summary_path": "summary_sha256",
        "audit_path": "audit_sha256",
    }
    paths: dict[str, Path] = {}
    for path_field, hash_field in path_fields.items():
        path = (repo_root / str(prior.get(path_field, ""))).resolve()
        if repo_root not in path.parents or not path.is_file():
            raise GalleryCampaignError(f"R3.6 lineage path is missing or unsafe: {path_field}")
        if engine.sha256_file(path) != prior.get(hash_field):
            raise GalleryCampaignError(f"R3.6 lineage SHA-256 mismatch: {path_field}")
        paths[path_field] = path

    old_contract = engine.load_json(paths["contract_path"])
    old_summary = engine.load_json(paths["summary_path"])
    old_audit = engine.load_json(paths["audit_path"])
    if (
        old_contract.get("case_count") != 144
        or old_summary.get("status") != "PASS_WITH_LIMITATIONS"
        or old_summary.get("pass_candidate_count") != 144
        or old_audit.get("audit_status") != "PASS_WITH_LIMITATIONS"
        or old_audit.get("case_pass_count") != 144
    ):
        raise GalleryCampaignError("R3.6 lineage is not the completed 144/144 campaign.")

    raw_root = (repo_root / str(old_contract.get("output_root", ""))).resolve()
    if repo_root not in raw_root.parents or not raw_root.is_dir():
        raise GalleryCampaignError("R3.6 raw evidence directory is unavailable.")
    manifest = engine.load_json(paths["manifest_path"]).get("files")
    actual_files = {
        item.relative_to(raw_root).as_posix()
        for item in raw_root.rglob("*")
        if item.is_file() and item.name != "manifest.json"
    }
    if not isinstance(manifest, dict) or actual_files != set(manifest):
        raise GalleryCampaignError("R3.6 raw file set differs from its immutable manifest.")
    for relative, entry in manifest.items():
        item = raw_root / relative
        if (
            not item.is_file()
            or item.stat().st_size != entry.get("size_bytes")
            or engine.sha256_file(item) != entry.get("sha256")
        ):
            raise GalleryCampaignError(f"R3.6 raw evidence hash mismatch: {relative}")

    recomputed = auditor.audit(paths["contract_path"], raw_root, repo_root)
    if recomputed.get("audit_status") != "PASS_WITH_LIMITATIONS" or recomputed.get("case_pass_count") != 144:
        raise GalleryCampaignError("Independent R3.6 raw evidence audit no longer passes.")
    return {
        "revision": old_contract.get("revision"),
        "case_count": 144,
        **{field: prior[field] for field in path_fields},
        "recomputed_audit_status": recomputed["audit_status"],
        "historical_evidence_reused_as_r4_results": False,
    }


def preflight(contract_path: Path, repo_root: Path) -> tuple[dict[str, Any], list[Any], dict[str, Any]]:
    contract_path, repo_root = contract_path.resolve(), repo_root.resolve()
    contract = engine.load_json(contract_path)
    engine.validate_external_configuration(contract)
    if contract.get("revision") != REVISION or contract.get("status") != "FROZEN":
        raise GalleryCampaignError("R4 gallery contract revision/status is not frozen as expected.")
    if contract.get("execution_authorized") is not True or contract.get("abort_on_execution_failure") is not True:
        raise GalleryCampaignError("R4 requires explicit execution authorization and fail-closed stop policy.")
    if contract.get("output_overwrite_allowed") is not False:
        raise GalleryCampaignError("R4 output overwrite must remain prohibited.")
    if _git(repo_root, "branch", "--show-current") != BRANCH:
        raise GalleryCampaignError("Checkout is not on the isolated R4 branch.")
    if _git(repo_root, "status", "--porcelain"):
        raise GalleryCampaignError("Working tree must be clean before R4 execution.")
    base = str(contract.get("branch_base_sha", ""))
    freeze = str(contract.get("freeze_commit_sha", ""))
    if _git(repo_root, "rev-parse", "--verify", f"{base}^{{commit}}") != base:
        raise GalleryCampaignError("R4 branch base SHA is not resolvable.")
    if _git(repo_root, "rev-parse", "HEAD^") != freeze:
        raise GalleryCampaignError("R4 frozen contract is not immediately after its preparation commit.")
    if subprocess.run(["git", "merge-base", "--is-ancestor", base, "HEAD"], cwd=repo_root, check=False).returncode:
        raise GalleryCampaignError("R4 execution SHA does not descend from the R3.6 evidence commit.")
    if subprocess.run(["git", "diff", "--quiet", base, "HEAD", "--", "src/"], cwd=repo_root, check=False).returncode:
        raise GalleryCampaignError("R4 campaign unexpectedly changes production source.")

    tracked_sources = {
        "runner_sha": "scripts/run_wp12_gallery_r4.py",
        "model_builder_sha": "scripts/wp12_gallery_models.py",
        "auditor_sha": "scripts/audit_wp12_expanded_code_aster.py",
        "contract_builder_sha": "scripts/freeze_wp12_gallery_r4_contract.py",
    }
    for field, relative in tracked_sources.items():
        if _git(repo_root, "log", "-1", "--format=%H", "--", relative) != contract.get(field):
            raise GalleryCampaignError(f"R4 {field} does not resolve to the current tracked source.")

    prior_verified = _verify_prior_r36(contract, repo_root)
    if prior_verified.get("recomputed_audit_status") != contract.get("extends_campaign", {}).get("recomputed_audit_status"):
        raise GalleryCampaignError("R3.6 prior-campaign audit status differs from frozen lineage.")
    cases = case_catalog()
    expected = contract.get("cases")
    if len(cases) != EXPECTED_CASES or contract.get("case_count") != EXPECTED_CASES:
        raise GalleryCampaignError("R4 matrix does not contain exactly 864 frozen cases.")
    if not isinstance(expected, list) or len(expected) != EXPECTED_CASES:
        raise GalleryCampaignError("R4 frozen case records are incomplete.")
    for case, frozen in zip(cases, expected, strict=True):
        if _case_record(case) != frozen:
            raise GalleryCampaignError(f"Generated model differs from frozen R4 case {case.case_id}.")
    if set(contract.get("families", [])) != set(FAMILIES):
        raise GalleryCampaignError("R4 family set differs from generated catalog.")
    if set(contract.get("geometry_catalog_m", {})) != set(GEOMETRIES):
        raise GalleryCampaignError("R4 topology set differs from generated catalog.")
    if set(contract.get("material_catalog", {})) != set(MATERIALS):
        raise GalleryCampaignError("R4 material set differs from generated catalog.")

    output_paths = [
        (repo_root / str(contract[field])).resolve()
        for field in ("output_root", "manifest_path", "audit_path", "summary_path", "report_path")
    ]
    if any(repo_root not in path.parents for path in output_paths):
        raise GalleryCampaignError("R4 evidence paths must remain inside the isolated repository.")
    if any(path.exists() for path in output_paths):
        raise GalleryCampaignError("R4 evidence output already exists; overwrite/resume is forbidden.")

    docker = shutil.which("docker")
    if docker is None:
        raise GalleryCampaignError("Docker CLI is unavailable.")
    image = subprocess.run(
        [docker, "image", "inspect", engine.IMAGE, "--format", "{{.Id}}"], capture_output=True, text=True
    )
    if image.returncode != 0 or image.stdout.strip() != contract.get("code_aster_image_id"):
        raise GalleryCampaignError("Pinned Code_Aster image ID is unavailable or mismatched.")
    probe = subprocess.run(
        [docker, "run", "--rm", "--entrypoint", "/bin/bash", engine.IMAGE, "-lc", engine._runtime_command(f"{engine.ASTER_RUNNER} --version")],
        capture_output=True,
        text=True,
    )
    runtime_version = probe.stdout.strip()
    if probe.returncode != 0 or not runtime_version.startswith(f"code_aster {contract['code_aster_version']} "):
        raise GalleryCampaignError("Pinned Code_Aster runtime/import preflight failed.")
    readiness = {
        "status": "PREFLIGHT_PASS",
        "branch": BRANCH,
        "execution_sha": _git(repo_root, "rev-parse", "HEAD"),
        "contract_sha256": engine.sha256_file(contract_path),
        "code_aster_image_id": image.stdout.strip(),
        "code_aster_runtime_version": runtime_version,
        "case_count": len(cases),
        "prior_r36_audit": prior_verified,
        "output_paths_absent": True,
        "sequential_execution": True,
        "cpu_per_container": 1,
        "mpi": False,
    }
    return readiness, cases, contract


def _run_case(case: Any, case_root: Path, contract: dict[str, Any], readiness: dict[str, Any]) -> dict[str, Any]:
    """Run through the R3 serializer while binding this case's frozen material."""
    original_material = engine.MATERIAL
    engine.MATERIAL = dict(case.material)
    try:
        result = r3_runner._run_case(case, case_root, contract, readiness)
    finally:
        engine.MATERIAL = original_material
    result["geometry"] = case.geometry
    result["material_variant"] = case.material_variant
    case_path = case_root / "case.json"
    case_record = engine.load_json(case_path)
    case_record["material_variant"] = case.material_variant
    engine.write_json(case_path, case_record)
    engine.write_json(case_root / "result.json", result)
    return result


def execute(contract_path: Path, repo_root: Path) -> dict[str, Any]:
    readiness, cases, contract = preflight(contract_path, repo_root)
    repo_root = repo_root.resolve()
    output_root = (repo_root / contract["output_root"]).resolve()
    manifest_path = (repo_root / contract["manifest_path"]).resolve()
    output_root.mkdir(parents=True, exist_ok=False)
    engine.write_json(output_root / "preflight.json", readiness)
    results: dict[str, dict[str, Any]] = {}
    started = datetime.now(timezone.utc)
    for index, case in enumerate(cases, start=1):
        case_root = output_root / case.case_id
        try:
            result = _run_case(case, case_root, contract, readiness)
        except Exception as exc:  # Preserve evidence and stop at first failure.
            result = {
                "status": "FAIL_CLOSED_EXECUTION",
                "case_id": case.case_id,
                "family": case.family,
                "geometry": case.geometry,
                "material_variant": case.material_variant,
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
                "family": case.family,
                "geometry": case.geometry,
                "material_variant": case.material_variant,
                "mesh": case.mesh,
                "load_case": case.load_case,
                "status": result["status"],
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "elapsed_seconds": (datetime.now(timezone.utc) - started).total_seconds(),
            },
        )
        engine._manifest(output_root, manifest_path)
        if result.get("status") == "FAIL_CLOSED_EXECUTION":
            break

    passed = sum(row.get("status") == "PASS_CANDIDATE" for row in results.values())
    coverage: dict[str, dict[str, dict[str, int]]] = {}
    for field, catalog in (("family", FAMILIES), ("geometry", GEOMETRIES), ("material_variant", MATERIALS)):
        coverage[field] = {
            value: {
                "cases": sum(row.get(field) == value for row in results.values()),
                "passed": sum(row.get(field) == value and row.get("status") == "PASS_CANDIDATE" for row in results.values()),
                "failed": sum(row.get(field) == value and row.get("status") != "PASS_CANDIDATE" for row in results.values()),
            }
            for value in catalog
        }
    summary = {
        "schema": "wp12-r4-gallery-raw-summary-v1",
        "work_package": "WP12",
        "campaign": REVISION,
        "revision": contract["revision"],
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
        "code_aster_image": contract["code_aster_image"],
        "code_aster_image_id": readiness["code_aster_image_id"],
        "code_aster_runtime_version": readiness["code_aster_runtime_version"],
        "coverage": coverage,
        "cases": results,
        "limitations": contract["limitations"],
        "execution_started_utc": started.isoformat(),
        "execution_finished_utc": datetime.now(timezone.utc).isoformat(),
    }
    engine.write_json(output_root / "wp12_gallery_r4_raw_summary.json", summary)
    engine._manifest(output_root, manifest_path)
    return summary


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
            result = {**readiness, "revision": contract["revision"], "case_ids": [case.case_id for case in cases]}
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0 if result.get("status") in {"PREFLIGHT_PASS", "PASS_CANDIDATE_WITH_LIMITATIONS"} else 2
    except (GalleryCampaignError, OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"WP12_R4_GALLERY_FAIL_CLOSED: {type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
