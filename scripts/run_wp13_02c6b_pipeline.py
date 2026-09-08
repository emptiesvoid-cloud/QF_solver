"""WP13-02C6b sequencing and immutability guards.

This module does not execute a harmonic solve.  It separates candidate
schema validation from semantic validation and final evidence promotion for
the future C6c campaign.  The C6 archive from the blocked C6 attempt is
historical input only and is never rewritten here.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_wp13_02c5_harmonic_pipeline as c5  # noqa: E402


CONTRACT_PATH = ROOT / "qualification/0_2_8/wp13_02c_harmonic_contract.json"
FINAL_SCHEMA_PATH = ROOT / "qualification/0_2_8/wp13_02c6_harmonic_evidence.schema.json"
CANDIDATE_SCHEMA_PATH = ROOT / "qualification/0_2_8/wp13_02c6b_candidate.schema.json"
C6_RUNNER_RELATIVE = "scripts/run_wp13_02c6_harmonic_final.py"
C6B_RELATIVE = "scripts/run_wp13_02c6b_pipeline.py"
FINAL_SCHEMA_RELATIVE = "qualification/0_2_8/wp13_02c6_harmonic_evidence.schema.json"
CANDIDATE_SCHEMA_RELATIVE = "qualification/0_2_8/wp13_02c6b_candidate.schema.json"
C6C_FREEZE_RECORD_PATH = ROOT / "qualification/0_2_8/wp13_02c6c_pipeline_freeze.json"
C6_STATUS_RECORD_PATH = ROOT / "qualification/0_2_8/wp13_02c6b_status.json"
C6C_OUTPUT_RELATIVE = "qualification/0_2_8/wp13_02c6c_harmonic_final"


class C6bComplianceError(ValueError):
    """Raised when the C6c evidence pipeline violates its frozen protocol."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_revision() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _schema_errors(manifest: dict[str, Any], schema_path: Path) -> list[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return [error.message for error in jsonschema.Draft202012Validator(schema).iter_errors(c5._json_safe(manifest))]


def validate_candidate_manifest(manifest: dict[str, Any]) -> list[str]:
    """Validate a candidate without allowing it to claim final validity."""

    errors = _schema_errors(manifest, CANDIDATE_SCHEMA_PATH)
    if manifest.get("evidence_schema_valid") is not False:
        errors.append("candidate must declare evidence_schema_valid=false")
    if manifest.get("semantic_validator_valid") is not False:
        errors.append("candidate must declare semantic_validator_valid=false")
    return errors


def validate_final_manifest(manifest: dict[str, Any]) -> list[str]:
    """Validate only a manifest that has already passed semantic validation."""

    errors = _schema_errors(manifest, FINAL_SCHEMA_PATH)
    if manifest.get("evidence_schema_valid") is not True:
        errors.append("final manifest must declare evidence_schema_valid=true")
    if manifest.get("semantic_validator_valid") is not True:
        errors.append("final manifest must declare semantic_validator_valid=true")
    return errors


def c6c_pipeline_components() -> list[dict[str, str]]:
    """Return every source producer consumed by the future C6c evidence pack."""

    components = [copy.deepcopy(item) for item in c5.PIPELINE_COMPONENTS]
    components.extend(
        [
            {
                "name": "c2_harness",
                "path": "scripts/run_wp13_02c2_harmonic_harness.py",
                "role": "independent interface/failure harness source",
            },
            {
                "name": "c3_modal_evidence",
                "path": "scripts/derive_wp13_02c3_modal_evidence.py",
                "role": "historical modal evidence derivation source",
            },
            {
                "name": "c6_campaign_driver",
                "path": C6_RUNNER_RELATIVE,
                "role": "frozen C6c campaign driver and manifest builder",
            },
            {
                "name": "c6_candidate_schema",
                "path": CANDIDATE_SCHEMA_RELATIVE,
                "role": "candidate/prevalidation schema",
            },
            {
                "name": "c6_final_schema",
                "path": FINAL_SCHEMA_RELATIVE,
                "role": "final evidence schema",
            },
            {
                "name": "c6b_sequence_guard",
                "path": C6B_RELATIVE,
                "role": "sequence, semantic and immutability guard",
            },
        ]
    )
    return components


def c6c_pipeline_component_digests() -> dict[str, str]:
    digests: dict[str, str] = {}
    for component in c6c_pipeline_components():
        path = ROOT / component["path"]
        if not path.is_file():
            raise C6bComplianceError(f"Missing C6c pipeline component: {component['path']}")
        digests[component["name"]] = sha256_file(path)
    return digests


def c6c_pipeline_combined_digest(digests: dict[str, str]) -> str:
    payload = {key: digests[key] for key in sorted(digests)}
    return c5.canonical_digest(payload)


def build_c6c_pre_run_freeze(*, repo_sha: str | None = None) -> dict[str, Any]:
    digests = c6c_pipeline_component_digests()
    return {
        "freeze_version": 1,
        "pipeline_components": c6c_pipeline_components(),
        "pipeline_component_digests": digests,
        "pipeline_combined_digest": c6c_pipeline_combined_digest(digests),
        "campaign_driver_path": C6_RUNNER_RELATIVE,
        "campaign_driver_digest": digests["c6_campaign_driver"],
        "campaign_schema_path": FINAL_SCHEMA_RELATIVE,
        "campaign_schema_digest": digests["c6_final_schema"],
        "contract_blob_digest": sha256_file(CONTRACT_PATH),
        "schema_blob_digest": sha256_file(c5.EVIDENCE_SCHEMA_PATH),
        "candidate_schema_digest": sha256_file(CANDIDATE_SCHEMA_PATH),
        "final_schema_digest": sha256_file(FINAL_SCHEMA_PATH),
        "repo_sha": repo_sha or git_revision(),
        "environment": c5.environment_snapshot() | {"pipeline": "WP13-02C6c frozen evidence pipeline"},
        "pre_run_freeze_valid": True,
        "numerical_campaign_started": False,
        "post_run_pipeline_mutation_allowed": False,
        "post_run_manifest_rewrite_allowed": False,
    }


def assert_c6c_pipeline_unchanged(freeze: dict[str, Any]) -> None:
    if not isinstance(freeze.get("repo_sha"), str) or not re.fullmatch(r"[0-9a-f]{40}", freeze["repo_sha"]):
        raise C6bComplianceError("C6c freeze repo_sha is missing or malformed.")
    if freeze["repo_sha"] != git_revision():
        raise C6bComplianceError("Repository SHA changed after the C6c pre-run freeze.")
    if freeze.get("contract_blob_digest") != sha256_file(CONTRACT_PATH):
        raise C6bComplianceError("Frozen contract digest changed after the C6c pre-run freeze.")
    if freeze.get("candidate_schema_digest") != sha256_file(CANDIDATE_SCHEMA_PATH):
        raise C6bComplianceError("Candidate schema digest changed after the C6c pre-run freeze.")
    if freeze.get("final_schema_digest") != sha256_file(FINAL_SCHEMA_PATH):
        raise C6bComplianceError("Final schema digest changed after the C6c pre-run freeze.")
    current = c6c_pipeline_component_digests()
    if current != freeze.get("pipeline_component_digests"):
        raise C6bComplianceError("C6c pipeline component digest changed after freeze.")
    if c6c_pipeline_combined_digest(current) != freeze.get("pipeline_combined_digest"):
        raise C6bComplianceError("C6c combined pipeline digest changed after freeze.")
    if freeze.get("post_run_pipeline_mutation_allowed") is not False:
        raise C6bComplianceError("Post-run pipeline mutation must remain disabled.")
    if freeze.get("post_run_manifest_rewrite_allowed") is not False:
        raise C6bComplianceError("Post-run manifest rewrite must remain disabled.")
    if freeze.get("pre_run_freeze_valid") is not True:
        raise C6bComplianceError("C6c pre-run freeze is not valid.")


def validate_c6c_freeze_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(record.get("repo_sha"), str) or not re.fullmatch(r"[0-9a-f]{40}", record["repo_sha"]):
        errors.append("repo_sha is missing or malformed")
    try:
        current = build_c6c_pre_run_freeze(repo_sha=record.get("repo_sha"))
    except C6bComplianceError as exc:
        return [str(exc)]
    if record.get("contract_blob_digest") != current["contract_blob_digest"]:
        errors.append("contract digest does not match the frozen contract")
    if record.get("candidate_schema_digest") != current["candidate_schema_digest"]:
        errors.append("candidate schema digest does not match")
    if record.get("final_schema_digest") != current["final_schema_digest"]:
        errors.append("final schema digest does not match")
    if record.get("pipeline_component_digests") != current["pipeline_component_digests"]:
        errors.append("pipeline component digests do not match")
    if record.get("pipeline_combined_digest") != current["pipeline_combined_digest"]:
        errors.append("pipeline combined digest does not match")
    if record.get("c6c_expected_pipeline_digest") != current["pipeline_combined_digest"]:
        errors.append("C6C expected pipeline digest does not match")
    if record.get("pipeline_components") != current["pipeline_components"]:
        errors.append("pipeline component declaration does not match")
    for key in (
        "pre_run_freeze_valid",
        "numerical_campaign_started",
        "post_run_pipeline_mutation_allowed",
        "post_run_manifest_rewrite_allowed",
    ):
        if record.get(key) != current[key]:
            errors.append(f"freeze flag {key} is invalid")
    return errors


def validate_c6_semantics(manifest: dict[str, Any], contract: dict[str, Any]) -> list[str]:
    """Apply C5 semantic rules to a C6 candidate without C5 schema recursion."""

    errors: list[str] = []
    if manifest.get("contract_id") != contract["contract_id"]:
        errors.append("contract_id does not match frozen contract")
    if manifest.get("contract_values_single_source_of_truth") is not True:
        errors.append("contract values are not declared single-source")
    energy = manifest.get("energy_contract", {})
    energy_path = "metric_definitions.interface_energy"
    if energy.get("contract_path") != energy_path:
        errors.append("energy contract path is not literal contract path")
    if energy.get("literal_definition") != c5.contract_value(contract, energy_path):
        errors.append("energy literal definition differs from frozen contract")
    if energy.get("formula_literal_match") is not True:
        errors.append("energy formula literal guard did not pass")
    if manifest.get("post_run_manifest_rewrite_allowed") is not False:
        errors.append("post-run manifest rewrite is allowed or unspecified")
    if manifest.get("post_run_pipeline_mutation_allowed") is not False:
        errors.append("post-run pipeline mutation is allowed or unspecified")
    failure_cases = manifest.get("failure_executions", {}).get("cases", {})
    for case_id in contract["failure_contract"]["cases"]:
        if case_id not in failure_cases:
            errors.append(f"missing failure case {case_id}")
        else:
            errors.extend(c5.validate_failure_record(case_id, failure_cases[case_id], contract))
    modal = manifest.get("modal_coordinate_pipeline", {})
    for field in ("phi_source", "phi_digest", "mass_source", "mass_digest", "normalization", "projection_formula"):
        if not modal.get(field):
            errors.append(f"modal pipeline metadata missing {field}")
    if modal.get("projection_formula") != "q = phi^H M x":
        errors.append("modal projection formula is not contractual")
    if modal.get("frozen_pipeline") is not True:
        errors.append("modal coordinate is not produced in frozen pipeline")
    required_replay = set(c5.replay_fields_from_contract(contract))
    replay = manifest.get("replay_pipeline", {})
    if set(replay.get("fields", [])) != required_replay:
        errors.append("replay fields differ from contract")
    if replay.get("runtime_iteration_semantics") == "synthetic":
        errors.append("synthetic iteration metadata is forbidden")
    if "iterations" in replay.get("fields", []) and replay.get("runtime_iteration_semantics") != "observed_runtime_metadata":
        errors.append("synthetic iteration field is present")
    records = manifest.get("historical_owner_records", {})
    c4_path = "qualification/0_2_8/wp13_02c4_owner_gate.json"
    if records.get("WP13-02C4") != c4_path:
        errors.append("WP13-02C4 Owner reject record is missing")
    elif not (ROOT / c4_path).is_file():
        errors.append("WP13-02C4 Owner reject record file is missing")
    else:
        c4_record = json.loads((ROOT / c4_path).read_text(encoding="utf-8"))
        if c4_record.get("verdict") != "REJECT_CONTRACT_VIOLATION":
            errors.append("WP13-02C4 Owner reject record verdict is not preserved")
    return errors


def promote_candidate(candidate: dict[str, Any], *, post_run_digest: str) -> dict[str, Any]:
    """Promote only a semantically validated candidate into final evidence."""

    final = copy.deepcopy(candidate)
    final["evidence_schema_valid"] = True
    final["semantic_validator_valid"] = True
    final["evidence_schema_errors"] = []
    final["semantic_validation_errors"] = []
    final["post_run_pipeline_digest"] = post_run_digest
    final["pipeline_digest_match"] = True
    final["pipeline_mutation_detected"] = False
    final["evidence_integrity"] = True
    return final


def _semantic_failure_stage(errors: list[str]) -> str:
    joined = " ".join(errors).lower()
    if "failure case" in joined or "failure" in joined:
        return "failure_contract"
    if "replay" in joined:
        return "replay"
    return "semantic_validation"


def finalize_candidate(
    candidate: dict[str, Any], contract: dict[str, Any]
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Run the non-circular candidate -> semantic -> final sequence."""

    candidate_errors = validate_candidate_manifest(candidate)
    if candidate_errors:
        return None, partial_failure_record("schema", candidate_errors)
    semantic_errors = validate_c6_semantics(candidate, contract)
    if semantic_errors:
        return None, partial_failure_record(_semantic_failure_stage(semantic_errors), semantic_errors)
    try:
        assert_c6c_pipeline_unchanged(candidate["pipeline_freeze"])
    except (KeyError, C6bComplianceError) as exc:
        return None, partial_failure_record("freeze", [str(exc)])
    final = promote_candidate(
        candidate,
        post_run_digest=candidate["pipeline_freeze"]["pipeline_combined_digest"],
    )
    final_errors = validate_final_manifest(final)
    if final_errors:
        return None, partial_failure_record("final_schema", final_errors)
    return final, None


def write_final_manifest_once(path: Path, manifest: dict[str, Any]) -> None:
    """Write final evidence exactly once; never overwrite an existing record."""

    if path.exists():
        raise C6bComplianceError("Final manifest rewrite is forbidden.")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(c5._json_safe(manifest), indent=2, sort_keys=True) + "\n"
    with path.open("x", encoding="utf-8", newline="") as stream:
        stream.write(payload)


def write_partial_failure_once(path: Path, record: dict[str, Any]) -> None:
    """Persist a non-qualifying failure record once, without making evidence pass."""

    if path.exists():
        raise C6bComplianceError("Partial-failure record rewrite is forbidden.")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(c5._json_safe(record), indent=2, sort_keys=True) + "\n"
    with path.open("x", encoding="utf-8", newline="") as stream:
        stream.write(payload)


def write_archive_once(path: Path, arrays: dict[str, Any]) -> None:
    """Write the future NPZ exactly once; never replace a prior archive."""

    if path.exists():
        raise C6bComplianceError("Final NPZ rewrite is forbidden.")
    path.parent.mkdir(parents=True, exist_ok=True)
    import numpy as np

    with path.open("xb") as stream:
        np.savez_compressed(stream, **arrays)


def assert_output_paths_clean(
    manifest_path: Path,
    archive_path: Path,
    failure_path: Path | None = None,
    freeze_path: Path | None = None,
) -> None:
    if manifest_path.exists():
        raise C6bComplianceError("C6c final manifest already exists.")
    if archive_path.exists():
        raise C6bComplianceError("C6c final NPZ already exists.")
    if failure_path is not None and failure_path.exists():
        raise C6bComplianceError("C6c failure record already exists.")
    if freeze_path is not None and freeze_path.exists():
        raise C6bComplianceError("C6c pre-run freeze already exists.")


def partial_failure_record(stage: str, errors: list[str]) -> dict[str, Any]:
    return {
        "record_id": "QF-028-WP13-02C6B-PARTIAL-FAILURE",
        "work_package": "WP13-02C6B",
        "status": "FAIL/BLOCKED",
        "stage": stage,
        "errors": list(errors),
        "final_claim_allowed": False,
        "qualified_manifest_created": False,
        "historical_c6_status": "BLOCKED_SCHEMA_SEQUENCE",
    }
