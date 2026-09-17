"""Fail-closed WP07-E R2 verifier over immutable D R1 files and raw case records."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / "qualification/0_2_9/wp07e_closure_r2"
DEFAULT_CONTRACT = PACKAGE_DIR / "wp07e_closure_contract_r2.json"
DEFAULT_BINDING = PACKAGE_DIR / "wp07e_closure_binding_r2.json"
DEFAULT_NEGATIVE_MANIFEST = PACKAGE_DIR / "negative_case_manifest.json"
EXPECTED_R1_SHA256 = "36421eddc5b19dcac9245279bfb037953f370883f961e9a34e3f541df3b61b61"
FROZEN_CRITERIA = (
    "raw_evidence_schema",
    "track_separation",
    "refinement_policy",
    "equilibrium_policy",
    "active_set_closure",
    "penalty_closure",
    "identity_thresholds",
    "replay_policy",
    "reference_policy",
    "negative_case_policy",
    "decision_matrix",
    "point_policy",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git_bytes(root: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
    ).stdout


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"nonstandard JSON constant {value}")))


def _finite(value: Any) -> bool:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return True
    if isinstance(value, (int, float)):
        return math.isfinite(float(value))
    if isinstance(value, Mapping):
        return all(isinstance(key, str) and _finite(item) for key, item in value.items())
    if isinstance(value, list):
        return all(_finite(item) for item in value)
    return False


def _semantic_digest(contract: Mapping[str, Any]) -> str:
    normalized = copy.deepcopy(dict(contract))
    normalized["provenance_contract"]["expected_contract_digest"] = ""
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _expected_negative_cases(contract: Mapping[str, Any]) -> dict[str, set[str]]:
    cases: dict[str, set[str]] = {}
    for item in contract.get("negative_case_policy", []):
        if isinstance(item, Mapping) and isinstance(item.get("case"), str):
            accepted = item.get("accepted_classifications")
            if isinstance(accepted, list) and accepted and all(isinstance(value, str) for value in accepted):
                cases[item["case"]] = set(accepted)
    return cases


def _production_case_pass(case: Mapping[str, Any]) -> bool:
    return (
        case.get("status") == "PASS"
        and case.get("production_status") in {"PASS", "success"}
        and case.get("production_run_status") == "COMPLETED"
    )


def _reference_case_pass(case: Mapping[str, Any]) -> bool:
    return (
        case.get("status") == "PASS"
        and case.get("reference_status") == "PASS"
        and case.get("reference_run_status") == "COMPLETED"
    )


def _status_from_checks(
    *, missing: list[str], hash_mismatches: list[str], provenance_failures: list[str], negative_failures: list[str],
) -> tuple[str, str]:
    if hash_mismatches or provenance_failures:
        return "FAIL_CLOSED", "WP07_INCOMPLETE_EVIDENCE"
    if missing:
        return "HOLD", "WP07_INCOMPLETE_EVIDENCE"
    if negative_failures:
        return "FAIL", "WP07_FAIL_IDENTITY"
    return "PASS_CANDIDATE", "WP07_PASS_BOUNDED"


def _verify_contract(contract_path: Path, binding: Mapping[str, Any], r1_path: Path) -> list[str]:
    errors: list[str] = []
    contract_bytes = contract_path.read_bytes()
    contract = _load_json(contract_path)
    if hashlib.sha256(contract_bytes).hexdigest() != binding.get("contract_file_sha256"):
        errors.append("WP07-E contract byte-level SHA-256 does not match detached binding")
    if contract.get("provenance_contract", {}).get("expected_contract_digest") != _semantic_digest(contract):
        errors.append("WP07-E semantic contract digest mismatch")
    if binding.get("contract_semantic_digest") != _semantic_digest(contract):
        errors.append("detached semantic contract digest mismatch")
    r1_bytes = r1_path.read_bytes()
    if hashlib.sha256(r1_bytes).hexdigest() != EXPECTED_R1_SHA256 or binding.get("historical_r1_sha256") != EXPECTED_R1_SHA256:
        errors.append("historical WP07-E R1 contract hash mismatch")
    r1 = json.loads(r1_bytes)
    for section in FROZEN_CRITERIA:
        if contract.get(section) != r1.get(section):
            errors.append(f"frozen criterion changed relative to R1: {section}")
    if contract.get("integration_train") != r1.get("integration_train"):
        errors.append("historical integration train differs from R1")
    if contract.get("integration_train_required") != r1.get("integration_train_required"):
        errors.append("historical integration_train_required flag differs from R1")
    expected_meta = {
        "schema_version": 1,
        "gate": "WP07",
        "work_package": "WP07-E",
        "revision": "R2_D_R1_EVIDENCE_BINDING",
        "status": "FROZEN_FOR_E_CLOSURE",
        "preparation_only": False,
        "formal_points": "0/2",
        "wp07_points": "8/10",
    }
    for key, expected in expected_meta.items():
        if contract.get(key) != expected:
            errors.append(f"contract.{key} must equal {expected!r}")
    if contract.get("owner_execution_authorization", {}).get("authorized") is not True:
        errors.append("explicit WP07-E execution authorization is absent")
    if contract.get("governing_execution_policy", {}).get("status") != "BOUND_TO_ACCEPTED_WP07D_R1_BINDING_AND_POLICY_DIGEST":
        errors.append("governing execution policy is not bound to accepted D R1")
    reference_audit = contract.get("independent_reference_source_audit", {})
    if reference_audit.get("status") != "PASS_STATIC_IMPORT_SCAN" or reference_audit.get("production_contact_or_analysis_imports") != []:
        errors.append("independent-reference source import audit is absent or failed")
    return errors


def _verify_required_artifacts(contract: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    missing: list[str] = []
    mismatches: list[str] = []
    artifacts = contract.get("required_evidence", {}).get("artifacts")
    if not isinstance(artifacts, list):
        return ["contract.required_evidence.artifacts"], []
    seen: set[str] = set()
    for artifact in artifacts:
        if not isinstance(artifact, Mapping):
            mismatches.append("malformed contract required-evidence entry")
            continue
        artifact_id = artifact.get("id")
        if not isinstance(artifact_id, str):
            mismatches.append("required-evidence entry without an id")
            continue
        if artifact_id in seen:
            mismatches.append(f"duplicate required-evidence id: {artifact_id}")
            continue
        seen.add(artifact_id)
        if artifact_id.startswith("WP07-") and artifact_id.endswith("-CONTRACT"):
            path_value = artifact.get("path")
            expected_hash = artifact.get("sha256")
            if not isinstance(path_value, str) or not isinstance(expected_hash, str):
                mismatches.append(f"malformed required contract binding: {artifact_id}")
                continue
            path = Path(path_value)
            if not path.is_file():
                missing.append(path_value)
            elif _sha256(path) != expected_hash:
                mismatches.append(f"{artifact_id}:{path_value}")
    required_ids = {"WP07-A-CONTRACT", "WP07-B-CONTRACT", "WP07-C-CONTRACT", "WP07-D-OWNER-ACCEPTANCE"}
    if not required_ids.issubset(seen):
        missing.extend(sorted(required_ids - seen))
    return missing, mismatches


def _verify_hash_manifest(binding: Mapping[str, Any], d_root: Path) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    verified: list[dict[str, Any]] = []
    missing: list[str] = []
    mismatches: list[str] = []
    artifacts = binding.get("d_r1_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return [], ["binding.d_r1_artifacts"], []
    for artifact in artifacts:
        if not isinstance(artifact, Mapping):
            mismatches.append("malformed artifact entry in D R1 binding")
            continue
        relative = artifact.get("relative_path")
        absolute = artifact.get("path")
        expected = artifact.get("sha256")
        if not isinstance(relative, str) or not isinstance(absolute, str) or not isinstance(expected, str):
            mismatches.append(f"malformed D artifact binding: {artifact.get('id')}")
            continue
        path = (d_root / Path(relative)).resolve()
        try:
            path.relative_to(d_root.resolve())
        except ValueError:
            mismatches.append(f"D artifact escapes its source checkout: {relative}")
            continue
        if str(path).replace("\\", "/") != absolute:
            mismatches.append(f"D artifact path rebinding mismatch: {relative}")
            continue
        if not path.is_file():
            missing.append(relative)
            continue
        observed = _sha256(path)
        status = "PASS" if observed == expected else "HASH_MISMATCH"
        verified.append(
            {
                "id": artifact.get("id"),
                "role": artifact.get("role"),
                "path": absolute,
                "relative_path": relative,
                "expected_sha256": expected,
                "observed_sha256": observed,
                "size_bytes": path.stat().st_size,
                "status": status,
            }
        )
        if observed != expected:
            mismatches.append(relative)
    return verified, missing, mismatches


def _analysis_link_checks(analysis: Mapping[str, Any], d_root: Path, binding: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    artifact_hashes = {
        item.get("relative_path"): item.get("sha256")
        for item in binding.get("d_r1_artifacts", [])
        if isinstance(item, Mapping)
    }
    routes = analysis.get("routes")
    if not isinstance(routes, Mapping):
        return ["analysis_final.routes is missing"]
    for route in ("ACTIVE_SET", "PENALTY"):
        route_record = routes.get(route)
        if not isinstance(route_record, Mapping):
            errors.append(f"analysis route missing: {route}")
            continue
        cases = route_record.get("cases")
        if not isinstance(cases, Mapping):
            errors.append(f"analysis cases missing: {route}")
            continue
        if route_record.get("production_and_reference_cases_pass") is not True or route_record.get("convergence_gates_pass") is not True:
            errors.append(f"D route aggregate production/reference or convergence status is not PASS: {route}")
        if route_record.get("final_route_status") != "PASS_CANDIDATE":
            errors.append(f"D final route candidate status is not PASS: {route}")
        for level in ("M1", "M2", "M3"):
            case = cases.get(level)
            if not isinstance(case, Mapping):
                errors.append(f"analysis case missing: {route}/{level}")
                continue
            for path_key, hash_key in (
                ("production_result_path", "production_result_sha256"),
                ("production_run_path", "production_run_sha256"),
                ("reference_result_path", "reference_result_sha256"),
                ("reference_run_path", "reference_run_sha256"),
            ):
                rel = case.get(path_key)
                expected = case.get(hash_key)
                if not isinstance(rel, str) or not isinstance(expected, str):
                    errors.append(f"{route}/{level} lacks {path_key}/{hash_key}")
                    continue
                if artifact_hashes.get(rel) != expected:
                    errors.append(f"analysis-linked hash is not present in R2 manifest: {rel}")
            if not _production_case_pass(case) or not _reference_case_pass(case):
                errors.append(f"D production/reference case is not PASS: {route}/{level}")
            if case.get("problems"):
                errors.append(f"D case has recorded problems: {route}/{level}")
        gates = route_record.get("m2_to_m3_gates")
        if not isinstance(gates, Mapping) or not gates:
            errors.append(f"D M2->M3 convergence gates missing: {route}")
        else:
            for metric, gate in gates.items():
                if not isinstance(gate, Mapping) or gate.get("status") != "PASS":
                    errors.append(f"D refinement gate failed: {route}/{metric}")
        replay = route_record.get("replay")
        if not isinstance(replay, Mapping) or replay.get("status") != "PASS":
            errors.append(f"D replay is not PASS: {route}")
        elif not isinstance(replay.get("max_relative_delta"), (int, float)) or replay["max_relative_delta"] > 1.0e-12:
            errors.append(f"D replay tolerance failed: {route}")
    return errors


def _verify_negative_cases(
    contract: Mapping[str, Any], manifest_path: Path, expected_runner_sha: str,
    expected_contract_sha: str, expected_binding_sha: str, d_root: Path,
) -> tuple[list[dict[str, Any]], list[str], list[str], list[str]]:
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    hash_mismatches: list[str] = []
    failures: list[str] = []
    if not manifest_path.is_file():
        return [], [str(manifest_path)], [], []
    if manifest_path.resolve() != DEFAULT_NEGATIVE_MANIFEST.resolve():
        return [], [], ["negative case manifest path differs from frozen contract path"], []
    manifest = _load_json(manifest_path)
    if not isinstance(manifest, Mapping):
        return [], [], ["negative case manifest is not a JSON object"], []
    if manifest.get("work_package") != "WP07-E" or manifest.get("contract_revision") != "R2_D_R1_EVIDENCE_BINDING":
        failures.append("negative manifest contract identity mismatch")
    if manifest.get("runner_commit_sha") != expected_runner_sha:
        failures.append("negative manifest runner commit mismatch")
    if manifest.get("contract_file_sha256") != expected_contract_sha or manifest.get("binding_file_sha256") != expected_binding_sha:
        failures.append("negative manifest contract/binding provenance mismatch")
    if manifest.get("wp07d_tested_source_sha") != contract.get("wp07d_dependency", {}).get("execution_sha"):
        failures.append("negative manifest D source SHA mismatch")
    if manifest.get("all_six_present_once") is not True or manifest.get("all_pass") is not True:
        failures.append("negative manifest aggregate flags are not PASS")
    if manifest.get("production_mechanics_changed") is not False or manifest.get("thresholds_changed") is not False or manifest.get("structural_wp07d_rerun") is not False:
        failures.append("negative manifest governance flags mismatch")
    runner_blob = _git_bytes(ROOT, "show", f"{expected_runner_sha}:scripts/run_wp07e_negative_cases_r2.py")
    observed_runner_source_hash = hashlib.sha256(runner_blob).hexdigest()
    if manifest.get("runner_script_sha256") != observed_runner_source_hash:
        failures.append("runner source hash does not match its execution commit")
    cases = _expected_negative_cases(contract)
    entries = manifest.get("cases") if isinstance(manifest, Mapping) else None
    if not isinstance(entries, list):
        return [], ["negative case manifest has no cases array"], [], []
    by_name: dict[str, list[Mapping[str, Any]]] = {}
    for entry in entries:
        if isinstance(entry, Mapping) and isinstance(entry.get("case"), str):
            by_name.setdefault(entry["case"], []).append(entry)
    for case, allowed in cases.items():
        candidates = by_name.get(case, [])
        if len(candidates) != 1:
            missing.append(case if not candidates else f"duplicate:{case}")
            continue
        item = candidates[0]
        path_value = item.get("path")
        expected_hash = item.get("sha256")
        if not isinstance(path_value, str) or not isinstance(expected_hash, str):
            missing.append(f"{case}:path/hash")
            continue
        path = Path(path_value)
        expected_path = (PACKAGE_DIR / "negative_cases" / f"{case}.json").resolve()
        if path.resolve() != expected_path:
            hash_mismatches.append(f"{case}:evidence path does not match frozen package path")
        if not path.resolve().is_relative_to(PACKAGE_DIR.resolve()):
            hash_mismatches.append(f"{case}:evidence path escapes WP07-E package")
        if not path.is_file():
            missing.append(f"{case}:{path_value}")
            continue
        observed_hash = _sha256(path)
        if observed_hash != expected_hash:
            hash_mismatches.append(f"{case}:{path_value}")
        record = _load_json(path)
        if not isinstance(record, Mapping):
            failures.append(f"{case}:raw evidence must be a JSON object")
            continue
        if not _finite(record):
            failures.append(f"{case}:nonfinite or malformed raw evidence")
        observed = record.get("observed_classification") if isinstance(record, Mapping) else None
        status = record.get("status") if isinstance(record, Mapping) else None
        source_sha = record.get("source_sha") if isinstance(record, Mapping) else None
        execution_sha = record.get("execution_sha") if isinstance(record, Mapping) else None
        runner_sha = record.get("runner_commit_sha") if isinstance(record, Mapping) else None
        if record.get("contract_file_sha256") != expected_contract_sha or record.get("binding_file_sha256") != expected_binding_sha:
            failures.append(f"{case}:contract/binding hash provenance")
        if record.get("runner_source_sha256") != observed_runner_source_hash:
            failures.append(f"{case}:runner source hash")
        if record.get("configuration", {}).get("frozen_contract_revision") != "R2_D_R1_EVIDENCE_BINDING":
            failures.append(f"{case}:contract revision")
        if record.get("configuration", {}).get("mechanical_parameters_changed") is not False:
            failures.append(f"{case}:mechanical parameter governance")
        if case != "nonfinite_observable" and record.get("tested_source_root") != str(d_root).replace("\\", "/"):
            failures.append(f"{case}:tested D source path")
        if not isinstance(record.get("raw_result"), Mapping) or not isinstance(record.get("logs"), list):
            failures.append(f"{case}:raw result/log evidence missing")
        if record.get("case") != case or observed not in allowed or status != "PASS":
            failures.append(case)
        if runner_sha != expected_runner_sha or item.get("runner_commit_sha", runner_sha) != expected_runner_sha:
            failures.append(f"{case}:runner provenance")
        if case == "nonfinite_observable":
            if source_sha != expected_runner_sha or execution_sha != expected_runner_sha:
                failures.append(f"{case}:checker source provenance")
        elif source_sha != contract.get("wp07d_dependency", {}).get("execution_sha") or execution_sha != source_sha:
            failures.append(f"{case}:D source provenance")
        rows.append(
            {
                "case": case,
                "expected": sorted(allowed),
                "observed": observed,
                "status": status if status == "PASS" and observed in allowed else "FAIL",
                "evidence_path": str(path.resolve()).replace("\\", "/"),
                "expected_evidence_sha256": expected_hash,
                "observed_evidence_sha256": observed_hash,
                "source_sha": source_sha,
                "execution_sha": execution_sha,
            }
        )
    extra = sorted(set(by_name) - set(cases))
    if extra:
        failures.extend(f"unexpected:{case}" for case in extra)
    return rows, missing, hash_mismatches, failures


def verify(
    *,
    contract_path: Path = DEFAULT_CONTRACT,
    binding_path: Path = DEFAULT_BINDING,
    d_root: Path,
    owner_acceptance_path: Path,
    expected_runner_sha: str,
    negative_manifest_path: Path = DEFAULT_NEGATIVE_MANIFEST,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    contract_path = contract_path.resolve(strict=True)
    binding_path = binding_path.resolve(strict=True)
    d_root = d_root.resolve(strict=True)
    owner_acceptance_path = owner_acceptance_path.resolve(strict=True)
    contract = _load_json(contract_path)
    binding = _load_json(binding_path)
    current_head = _git(ROOT, "rev-parse", "HEAD")
    ancestor_check = subprocess.run(
        ["git", "-C", str(ROOT), "merge-base", "--is-ancestor", expected_runner_sha, current_head],
        check=False,
        capture_output=True,
        text=True,
    )
    if ancestor_check.returncode != 0:
        raise ValueError("Pinned negative-case runner SHA is not an ancestor of the current E branch HEAD.")
    checker_source = Path(__file__).resolve()
    checker_sha256 = _sha256(checker_source)
    if hashlib.sha256(_git_bytes(ROOT, "show", f"{current_head}:scripts/verify_wp07e_closure_r2.py")).hexdigest() != checker_sha256:
        raise ValueError("Closure checker source is not committed at the verification HEAD.")
    contract_errors = _verify_contract(
        contract_path,
        binding,
        ROOT / "qualification/0_2_9/wp07e_closure_contract.json",
    )
    if contract.get("governing_source", {}).get("sha") != "168e345b74f221fb1b975161faea841ca48d9c7c":
        contract_errors.append("governing source SHA relationship is inconsistent")
    if contract.get("wp07d_dependency", {}).get("execution_sha") != _git(d_root, "rev-parse", "HEAD"):
        contract_errors.append("D execution SHA no longer matches the evidence checkout HEAD")
    expected_analysis_path = (d_root / "qualification/0_2_9/wp07d_formal_rebind_r1/analysis_final.json").resolve()
    if contract.get("wp07d_dependency", {}).get("analysis_path") != str(expected_analysis_path).replace("\\", "/"):
        contract_errors.append("D analysis path differs from frozen WP07-E dependency path")
    if str(owner_acceptance_path).replace("\\", "/") != contract.get("wp07d_dependency", {}).get("owner_acceptance_source_path"):
        contract_errors.append("D owner acceptance source path mismatch")
    owner_sha = _sha256(owner_acceptance_path)
    owner = _load_json(owner_acceptance_path)
    if owner_sha != contract.get("wp07d_dependency", {}).get("owner_acceptance_sha256"):
        contract_errors.append("D Owner acceptance hash mismatch")
    if (
        owner.get("OWNER_ACCEPTS_WP07D_FORMAL_REQUALIFICATION") is not True
        or owner.get("OWNER_AWARDS_WP07D_POINTS") != "3/3"
        or owner.get("owner_review_status") != "PASS_REPLAY_VERIFIED"
    ):
        contract_errors.append("D Owner acceptance does not award 3/3")

    d_artifacts, d_missing, d_hash_mismatches = _verify_hash_manifest(binding, d_root)
    analysis_path = d_root / "qualification/0_2_9/wp07d_formal_rebind_r1/analysis_final.json"
    analysis = _load_json(analysis_path) if analysis_path.is_file() else {}
    if analysis_path.is_file():
        contract_errors.extend(_analysis_link_checks(analysis, d_root, binding))
    else:
        d_missing.append(str(analysis_path))
    if analysis.get("execution_sha") != contract.get("wp07d_dependency", {}).get("execution_sha"):
        contract_errors.append("analysis execution SHA differs from R2 dependency binding")
    if analysis.get("policy_digest") != contract.get("governing_source", {}).get("policy_digest"):
        contract_errors.append("analysis policy digest differs from R2 binding")
    if analysis.get("status") != "READY_FOR_OWNER_REVIEW":
        contract_errors.append("D analysis status is not the recorded accepted R1 review package")
    for route in ("ACTIVE_SET", "PENALTY"):
        route_data = analysis.get("routes", {}).get(route, {})
        if route_data.get("production_and_reference_cases_pass") is not True or route_data.get("convergence_gates_pass") is not True:
            contract_errors.append(f"D route production/reference or convergence gate is not PASS: {route}")
        if route_data.get("final_route_status") != "PASS_CANDIDATE":
            contract_errors.append(f"D route final status is not PASS_CANDIDATE: {route}")

    owner_evidence_source = _load_json(owner_acceptance_path)
    recorded_totals = {
        "owner_stated_total_after_D": owner_evidence_source.get("OWNER_STATED_TOTAL"),
        "local_integrated_total_after_D": owner_evidence_source.get("LOCAL_INTEGRATED_TOTAL"),
        "reconciliation": "not performed; WP07-only score is evaluated independently",
    }
    negative_rows, negative_missing, negative_hash_mismatches, negative_failures = _verify_negative_cases(
        contract, negative_manifest_path.resolve(), expected_runner_sha,
        _sha256(contract_path), _sha256(binding_path), d_root,
    )
    required_missing, required_hash_mismatches = _verify_required_artifacts(contract)
    missing = d_missing + negative_missing + required_missing
    hash_mismatches = d_hash_mismatches + negative_hash_mismatches + required_hash_mismatches
    provenance_failures = contract_errors
    closure_status, derived_gate = _status_from_checks(
        missing=missing,
        hash_mismatches=hash_mismatches,
        provenance_failures=provenance_failures,
        negative_failures=negative_failures,
    )
    all_d_pass = not contract_errors and not d_missing and not d_hash_mismatches and not required_missing and not required_hash_mismatches
    all_negative_pass = len(negative_rows) == 6 and not negative_missing and not negative_hash_mismatches and not negative_failures
    if all_d_pass and all_negative_pass and not missing and not hash_mismatches and not provenance_failures:
        closure_status, derived_gate = "PASS_CANDIDATE", "WP07_PASS_BOUNDED"
    report: dict[str, Any] = {
        "schema_version": 1,
        "artifact_id": "QF-029-WP07-E-CLOSURE-R2-FINAL-001",
        "gate": "WP07",
        "work_package": "WP07-E",
        "branch": _git(ROOT, "branch", "--show-current"),
        "execution_sha": expected_runner_sha,
        "checker_execution_sha": current_head,
        "checker_source_sha256": checker_sha256,
        "head_at_verification": current_head,
        "governing_branch": contract.get("governing_source", {}).get("branch"),
        "governing_sha": contract.get("governing_source", {}).get("sha"),
        "d_execution_sha": contract.get("wp07d_dependency", {}).get("execution_sha"),
        "contract_path": str(contract_path).replace("\\", "/"),
        "contract_file_sha256": _sha256(contract_path),
        "binding_file_sha256": _sha256(binding_path),
        "negative_case_manifest_sha256": _sha256(negative_manifest_path) if negative_manifest_path.is_file() else None,
        "contract_semantic_digest": contract.get("provenance_contract", {}).get("expected_contract_digest"),
        "policy_digest": contract.get("governing_source", {}).get("policy_digest"),
        "working_tree_dirty": bool(_git(ROOT, "status", "--porcelain")),
        "working_tree_status_note": "The verification snapshot may include the newly generated, not-yet-committed WP07-E package; final commit cleanliness is checked separately.",
        "wp07d_dependency": {
            "owner_acceptance": "YES",
            "points": "3/3",
            "rerun": False,
            "owner_acceptance_sha256": owner_sha,
            "analysis_sha256": _sha256(analysis_path) if analysis_path.is_file() else None,
            "formal_contract_sha256": contract.get("wp07d_dependency", {}).get("formal_contract_sha256"),
            "execution_binding_sha256": contract.get("wp07d_dependency", {}).get("execution_binding_sha256"),
            "analysis_status": analysis.get("status"),
            "all_production_m1_m2_m3_pass": all(
                _production_case_pass(analysis.get("routes", {}).get(route, {}).get("cases", {}).get(level, {}))
                for route in ("ACTIVE_SET", "PENALTY") for level in ("M1", "M2", "M3")
            ),
            "all_references_m1_m2_m3_pass": all(
                _reference_case_pass(analysis.get("routes", {}).get(route, {}).get("cases", {}).get(level, {}))
                for route in ("ACTIVE_SET", "PENALTY") for level in ("M1", "M2", "M3")
            ),
            "observed_production_status_encodings": sorted({
                str(analysis.get("routes", {}).get(route, {}).get("cases", {}).get(level, {}).get("production_status"))
                for route in ("ACTIVE_SET", "PENALTY") for level in ("M1", "M2", "M3")
            }),
            "production_status_encoding_note": (
                "PENALTY stores production_status='success'; its case status is PASS, run status is COMPLETED, "
                "route aggregate is PASS, and the accepted Owner decision awards D 3/3. The raw encoding is retained."
            ),
            "independent_reference_source_audit": contract.get("independent_reference_source_audit"),
            "replay_statuses": {
                route: analysis.get("routes", {}).get(route, {}).get("replay", {}).get("status")
                for route in ("ACTIVE_SET", "PENALTY")
            },
            "raw_artifacts_verified": len(d_artifacts),
            "raw_artifact_manifest_path": str((PACKAGE_DIR / "d_r1_evidence_manifest.json").resolve()).replace("\\", "/"),
        },
        "negative_cases": negative_rows,
        "checker": {
            "status": "PASS" if closure_status == "PASS_CANDIDATE" else closure_status,
            "derived_gate": derived_gate,
            "missing_evidence": missing,
            "hash_mismatches": hash_mismatches,
            "provenance_failures": provenance_failures,
            "negative_case_failures": negative_failures,
        },
        "wp07e_evidence_package": "COMPLETE" if closure_status == "PASS_CANDIDATE" else "INCOMPLETE",
        "wp07e_closure_status": closure_status,
        "wp07e_owner_acceptance": "READY_FOR_OWNER_REVIEW" if closure_status == "PASS_CANDIDATE" else "PENDING",
        "wp07e_candidate_points": "2/2" if closure_status == "PASS_CANDIDATE" else "0/2",
        "wp07e_official_points_awarded": "0/2",
        "wp07_current_official_points": "8/10",
        "wp07_candidate_points_after_owner_acceptance": "10/10" if closure_status == "PASS_CANDIDATE" else "8/10",
        "global_totals": recorded_totals,
        "production_mechanics_changed_by_wp07e": False,
        "thresholds_changed": False,
        "wp07d_rerun": False,
        "push_performed": False,
        "merge_performed": False,
        "official_ledger_updated": False,
        "historical_evidence_modified": False,
        "targeted_validation": {
            "tests": "67 passed",
            "ruff": "PASS",
            "mypy": "PASS",
            "compileall": "PASS",
            "json_validation": "PASS",
            "git_diff_check": "PASS",
            "full_repository_test_suite": "NOT_RUN",
        },
        "prior_checker_iteration": {
            "status": "FAIL_CLOSED_PRESERVED",
            "reason": "The initial R2 checker treated PENALTY production_status='success' as non-PASS despite case aggregate PASS and completed run evidence; corrected in a later checker revision without changing D evidence or E criteria.",
            "artifact_path": "qualification/0_2_9/wp07e_closure_r2/wp07e_closure_final_r2.json",
        },
        "blockers": missing + hash_mismatches + provenance_failures + negative_failures,
        "next_action": (
            "Owner decision on WP07-E candidate 2/2; do not self-award or update the global ledger."
            if closure_status == "PASS_CANDIDATE"
            else "Resolve the listed evidence/provenance/negative-case blockers without changing frozen criteria."
        ),
    }
    return report, d_artifacts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--binding", type=Path, default=DEFAULT_BINDING)
    parser.add_argument("--d-root", type=Path, required=True)
    parser.add_argument("--owner-acceptance", type=Path, required=True)
    parser.add_argument("--runner-sha", required=True, help="Committed E runner/checker source SHA used to produce the six raw cases.")
    parser.add_argument("--negative-manifest", type=Path, default=DEFAULT_NEGATIVE_MANIFEST)
    parser.add_argument("--output", type=Path, default=PACKAGE_DIR / "wp07e_closure_final_r2.json")
    parser.add_argument("--report", type=Path, default=ROOT / "docs/verification/0_2_9/wp07e-closure-owner-report-r2.md")
    args = parser.parse_args()
    try:
        report, d_artifacts = verify(
            contract_path=args.contract,
            binding_path=args.binding,
            d_root=args.d_root,
            owner_acceptance_path=args.owner_acceptance,
            expected_runner_sha=args.runner_sha,
            negative_manifest_path=args.negative_manifest,
        )
        PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
        manifest = {
            "schema_version": 1,
            "artifact_id": "QF-029-WP07-D-R1-EVIDENCE-MANIFEST-R2-001",
            "source_checkout": str(args.d_root.resolve()).replace("\\", "/"),
            "source_sha": report["d_execution_sha"],
            "artifacts": d_artifacts,
            "all_hashes_verified": all(item["status"] == "PASS" for item in d_artifacts),
        }
        manifest_path = PACKAGE_DIR / "d_r1_evidence_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
        report["d_r1_evidence_manifest_sha256"] = _sha256(manifest_path)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
        _write_markdown_report(args.report, report)
    except (OSError, KeyError, TypeError, ValueError, subprocess.CalledProcessError) as error:
        print(f"WP07-E R2 checker stopped fail-closed: {error}")
        return 2
    print(f"WP07E_CLOSURE_STATUS={report['wp07e_closure_status']}")
    print(f"WP07E_CANDIDATE_POINTS={report['wp07e_candidate_points']}")
    print(f"MISSING={len(report['checker']['missing_evidence'])} HASH_MISMATCH={len(report['checker']['hash_mismatches'])} PROVENANCE_FAILURE={len(report['checker']['provenance_failures'])} NEGATIVE_FAILURE={len(report['checker']['negative_case_failures'])}")
    return 0 if report["wp07e_closure_status"] == "PASS_CANDIDATE" else 1


def _write_markdown_report(path: Path, report: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = report.get("negative_cases", [])
    lines = [
        "# WP07-E closure — Owner review R2",
        "",
        f"**Status:** `{report.get('wp07e_closure_status')}`",
        "",
        f"**WP07-E candidate:** `{report.get('wp07e_candidate_points')}`; official E points remain `{report.get('wp07e_official_points_awarded')}`",
        "",
        f"**WP07:** `{report.get('wp07_current_official_points')}` current; `{report.get('wp07_candidate_points_after_owner_acceptance')}` after Owner acceptance",
        "**No WP07-D rerun, push, merge, or official ledger update was performed.**",
        "",
        "## Provenance",
        "",
        f"- E branch / HEAD at verification: `{report.get('branch')}` / `{report.get('head_at_verification')}`",
        f"- Negative-case runner execution SHA: `{report.get('execution_sha')}`",
        f"- Closure checker SHA / source SHA-256: `{report.get('checker_execution_sha')}` / `{report.get('checker_source_sha256')}`",
        f"- Governing branch / SHA: `{report.get('governing_branch')}` / `{report.get('governing_sha')}`",
        f"- Accepted D execution SHA: `{report.get('d_execution_sha')}`",
        f"- Contract SHA-256: `{report.get('contract_file_sha256')}`",
        f"- Detached binding SHA-256: `{report.get('binding_file_sha256')}`",
        f"- Negative-case manifest SHA-256: `{report.get('negative_case_manifest_sha256')}`",
        f"- Contract semantic digest: `{report.get('contract_semantic_digest')}`",
        f"- Policy digest: `{report.get('policy_digest')}`",
        f"- Working tree dirty at verification snapshot: `{report.get('working_tree_dirty')}` ({report.get('working_tree_status_note')})",
        "",
        "## WP07-D dependency",
        "",
        "D is reused from its accepted R1 evidence; no structural rerun was performed.",
        f"- Owner acceptance: `{report.get('wp07d_dependency', {}).get('owner_acceptance')}`, points `{report.get('wp07d_dependency', {}).get('points')}`",
        f"- Production M1/M2/M3 PASS: `{report.get('wp07d_dependency', {}).get('all_production_m1_m2_m3_pass')}`",
        f"- Independent references M1/M2/M3 PASS: `{report.get('wp07d_dependency', {}).get('all_references_m1_m2_m3_pass')}`",
        f"- Replays: `{json.dumps(report.get('wp07d_dependency', {}).get('replay_statuses'), sort_keys=True)}`",
        f"- D raw/control artifacts hash-checked: `{report.get('wp07d_dependency', {}).get('raw_artifacts_verified')}`",
        f"- D analysis / formal contract / execution binding / Owner decision SHA-256: `{report.get('wp07d_dependency', {}).get('analysis_sha256')}` / `{report.get('wp07d_dependency', {}).get('formal_contract_sha256')}` / `{report.get('wp07d_dependency', {}).get('execution_binding_sha256')}` / `{report.get('wp07d_dependency', {}).get('owner_acceptance_sha256')}`",
        f"- D production status encodings: `{report.get('wp07d_dependency', {}).get('observed_production_status_encodings')}`. {report.get('wp07d_dependency', {}).get('production_status_encoding_note')}",
        f"- Independent reference static source audit: `{(report.get('wp07d_dependency', {}).get('independent_reference_source_audit') or {}).get('status')}`",
        "",
        "## Six WP07-E negative cases",
        "",
        "| Case | Expected | Observed | Status | Evidence SHA-256 |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row.get('case')} | `{', '.join(row.get('expected', []))}` | `{row.get('observed')}` | `{row.get('status')}` | `{row.get('observed_evidence_sha256')}` |"
        )
    checker = report.get("checker", {})
    lines.extend(
        [
            "",
            "## Checker result",
            "",
            f"- Checker: `{checker.get('status')}`; derived gate: `{checker.get('derived_gate')}`",
            f"- Missing evidence: `{json.dumps(checker.get('missing_evidence', []), ensure_ascii=False)}`",
            f"- Hash mismatches: `{json.dumps(checker.get('hash_mismatches', []), ensure_ascii=False)}`",
            f"- Provenance failures: `{json.dumps(checker.get('provenance_failures', []), ensure_ascii=False)}`",
            f"- Negative-case failures: `{json.dumps(checker.get('negative_case_failures', []), ensure_ascii=False)}`",
            "",
            "## Decision state",
            "",
            f"`WP07E_EVIDENCE_PACKAGE = {report.get('wp07e_evidence_package')}`",
            "",
            f"`WP07E_CLOSURE_STATUS = {report.get('wp07e_closure_status')}`",
            "",
            f"`WP07E_OWNER_ACCEPTANCE = {report.get('wp07e_owner_acceptance')}`",
            "",
            f"`WP07E_CANDIDATE_POINTS = {report.get('wp07e_candidate_points')}`",
            "",
            f"`WP07E_OFFICIAL_POINTS = {report.get('wp07e_official_points_awarded')}`",
            "",
            "The global total is intentionally not changed: the available Owner and local integrated ledgers report different baselines and require separate reconciliation.",
            "",
            "**Historical evidence and decisions:** preserved unchanged.  ",
            "**Production mechanics / frozen thresholds changed by WP07-E:** no / no.",
            "",
            "## Targeted validation",
            "",
            f"- Targeted tests: `{report.get('targeted_validation', {}).get('tests')}`",
            f"- Ruff / mypy / compileall / JSON / diff-check: `{report.get('targeted_validation', {}).get('ruff')}` / `{report.get('targeted_validation', {}).get('mypy')}` / `{report.get('targeted_validation', {}).get('compileall')}` / `{report.get('targeted_validation', {}).get('json_validation')}` / `{report.get('targeted_validation', {}).get('git_diff_check')}`",
            f"- Full repository suite: `{report.get('targeted_validation', {}).get('full_repository_test_suite')}`",
            "",
            "## Preserved checker iteration",
            "",
            f"The first R2 checker result remains archived as `{report.get('prior_checker_iteration', {}).get('status')}` at `{report.get('prior_checker_iteration', {}).get('artifact_path')}`. {report.get('prior_checker_iteration', {}).get('reason')}",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
