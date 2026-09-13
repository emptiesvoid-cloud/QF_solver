"""Fail-closed WP07-E evidence evaluator and report builder.

The builder consumes already-produced JSON evidence.  It does not execute a
solver, infer missing measurements, or manufacture qualification results.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "qualification" / "0_2_9" / "wp07e_closure_contract.json"

ACTIVE_SET_ID = "ACTIVE_SET"
PENALTY_ID = "PENALTY"
TRACK_IDS = (ACTIVE_SET_ID, PENALTY_ID)
REQUIRED_STATUS = {"PASS", "FAIL", "NOT_APPLICABLE"}
SUPPORTED_FINAL_STATUSES = (
    "WP07_PASS_BOUNDED",
    "WP07_PARTIAL_ACTIVE_SET_ONLY",
    "WP07_PARTIAL_PENALTY_ONLY",
    "WP07_HOLD_STRUCTURAL_CONVERGENCE",
    "WP07_HOLD_REFERENCE",
    "WP07_HOLD_REPLAY",
    "WP07_FAIL_IDENTITY",
    "WP07_FAIL_EQUILIBRIUM",
    "WP07_INCOMPLETE_EVIDENCE",
)
DECISION_PRECEDENCE = (
    "WP07_INCOMPLETE_EVIDENCE",
    "WP07_FAIL_IDENTITY",
    "WP07_FAIL_EQUILIBRIUM",
    "WP07_HOLD_REPLAY",
    "WP07_HOLD_STRUCTURAL_CONVERGENCE",
    "WP07_HOLD_REFERENCE",
    "WP07_PARTIAL_ACTIVE_SET_ONLY",
    "WP07_PARTIAL_PENALTY_ONLY",
    "WP07_PASS_BOUNDED",
)

_IDENTITY_CHECKS = {
    ACTIVE_SET_ID: {"open_zero_force", "closed_gap", "wrong_sign_pressure", "complementarity", "finite", "no_silent_pass"},
    PENALTY_ID: {"open_zero_force", "energy_gradient", "tangent_fd", "no_ghost_force_after_reopen", "rollback", "finite", "no_silent_pass"},
}
_EQUILIBRIUM_CHECKS = {"equilibrium_force", "equilibrium_moment"}
_REPLAY_CHECKS = {"replay"}
_STRUCTURAL_CHECKS = {"refinement", "accepted_load_path"}
_REFERENCE_CHECKS = {"reference"}
_REQUIRED_NEGATIVE_CASES = {
    "reversed_orientation",
    "open_no_contact",
    "excessive_penetration",
    "unsupported_combination",
    "nonfinite_observable",
    "incompatible_restart_metadata",
}


def load_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    """Load the checked-in WP07-E contract without applying defaults."""

    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("WP07-E contract root must be a JSON object.")
    return value


def _get_path(value: Mapping[str, Any], path: str) -> Any:
    current: Any = value
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return _MISSING
        current = current[part]
    return current


class _Missing:
    pass


_MISSING = _Missing()


def _is_finite_payload(value: Any) -> bool:
    """Return false for any nonfinite number nested in JSON-like data."""

    if isinstance(value, bool) or value is None or isinstance(value, str):
        return True
    if isinstance(value, (int, float)):
        return math.isfinite(float(value))
    if isinstance(value, Mapping):
        return all(isinstance(key, str) and _is_finite_payload(item) for key, item in value.items())
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return all(_is_finite_payload(item) for item in value)
    return True


def _artifact_id(record: Mapping[str, Any]) -> str | None:
    for key in ("artifact_id", "record_id", "contract_id"):
        value = record.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _required_artifacts(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    section = contract.get("required_evidence")
    if not isinstance(section, Mapping) or not isinstance(section.get("artifacts"), list):
        return []
    return [item for item in section["artifacts"] if isinstance(item, dict)]


def validate_contract(contract: Mapping[str, Any]) -> list[str]:
    """Validate the closure contract itself; errors make evaluation incomplete."""

    errors: list[str] = []
    expected = {
        "schema_version": 1,
        "gate": "WP07",
        "work_package": "WP07-E",
        "status": "PREPARATION_ONLY",
        "preparation_only": True,
        "qualification_campaign_executed": False,
        "integration_train_required": True,
        "execution_policy_status": "PENDING_GOVERNING_BRANCH_INTEGRATION",
        "no_data_fabrication": True,
    }
    for field, expected_value in expected.items():
        if contract.get(field) != expected_value:
            errors.append(f"contract.{field} must be {expected_value!r}")
    if contract.get("formal_points") != "0/2" or contract.get("wp07_points") != "0/10":
        errors.append("contract point state must remain 0/2 and 0/10 during preparation")

    artifacts = _required_artifacts(contract)
    ids = [item.get("id") for item in artifacts]
    if len(ids) != len(set(ids)) or any(not isinstance(item_id, str) for item_id in ids):
        errors.append("required evidence artifact IDs must be unique nonempty strings")
    for item in artifacts:
        if not item.get("path") or not item.get("role") or not item.get("required_fields"):
            errors.append(f"required artifact {item.get('id')!r} is missing path, role or fields")

    tracks = contract.get("track_separation")
    if not isinstance(tracks, Mapping):
        errors.append("track_separation is missing")
    else:
        for track_id in TRACK_IDS:
            track = tracks.get(track_id)
            if not isinstance(track, Mapping):
                errors.append(f"track {track_id} is missing")
                continue
            checks = track.get("required_checks")
            if not isinstance(checks, list) or not checks:
                errors.append(f"track {track_id} has no required checks")
            if track.get("independent_reference_id") not in ids:
                errors.append(f"track {track_id} references an undeclared independent reference")
        updated = tracks.get("UPDATED_SEARCH_FINITE_SLIDING")
        if not isinstance(updated, Mapping) or updated.get("qualified") is not False:
            errors.append("updated-search must remain explicitly unqualified")

    matrix = contract.get("decision_matrix")
    if not isinstance(matrix, Mapping):
        errors.append("decision_matrix is missing")
    else:
        precedence = matrix.get("precedence_high_to_low")
        if precedence != list(DECISION_PRECEDENCE):
            errors.append("decision precedence must enumerate the controlled statuses exactly")
        statuses = matrix.get("statuses")
        if not isinstance(statuses, Mapping) or any(status not in statuses for status in SUPPORTED_FINAL_STATUSES):
            errors.append("decision matrix must describe every supported final status")

    if not isinstance(contract.get("equilibrium_policy"), Mapping):
        errors.append("equilibrium_policy is missing")
    if not isinstance(contract.get("replay_policy"), Mapping):
        errors.append("replay_policy is missing")
    if not isinstance(contract.get("reference_policy"), Mapping):
        errors.append("reference_policy is missing")
    if not isinstance(contract.get("negative_case_policy"), list):
        errors.append("negative_case_policy is missing")
    execution = contract.get("execution_policy_binding")
    if not isinstance(execution, Mapping) or execution.get("status") != "PENDING_GOVERNING_BRANCH_INTEGRATION":
        errors.append("execution policy binding must remain pending integration")
    return errors


def _normalise_evidence(evidence: Mapping[str, Any] | Sequence[Any]) -> dict[str, dict[str, Any]]:
    records: Iterable[Any]
    if isinstance(evidence, Mapping):
        source: Any = evidence.get("evidence", evidence.get("artifacts", evidence))
        if isinstance(source, Mapping):
            records = source.values()
        elif isinstance(source, Sequence) and not isinstance(source, (str, bytes, bytearray)):
            records = source
        else:
            records = []
    else:
        records = evidence
    result: dict[str, dict[str, Any]] = {}
    for record in records:
        if isinstance(record, Mapping):
            identifier = _artifact_id(record)
            if identifier:
                result[identifier] = dict(record)
    return result


def _validate_record(record: Mapping[str, Any], spec: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    identifier = _artifact_id(record)
    if identifier != spec.get("id"):
        errors.append(f"artifact ID {identifier!r} does not match {spec.get('id')!r}")
    for field in spec.get("required_fields", []):
        if not isinstance(field, str) or _get_path(record, field) is _MISSING:
            errors.append(f"{spec.get('id')}.{field} is missing")
    if record.get("gate") != "WP07":
        errors.append(f"{spec.get('id')}.gate must be WP07")
    if not isinstance(record.get("source_sha"), str) or not record["source_sha"]:
        errors.append(f"{spec.get('id')}.source_sha is missing")
    if not _is_finite_payload(record):
        errors.append(f"{spec.get('id')} contains a nonfinite value")
    role = spec.get("role")
    if role in {"runtime", "independent_reference"} and not isinstance(record.get("provenance"), Mapping):
        errors.append(f"{spec.get('id')}.provenance must be an object")
    provenance = record.get("provenance")
    if role in {"runtime", "independent_reference"} and isinstance(provenance, Mapping):
        for field in ("source_sha", "case_definition_digest", "command", "environment"):
            if field not in provenance:
                errors.append(f"{spec.get('id')}.provenance.{field} is missing")
    if role == "runtime":
        if record.get("status") not in {"EXECUTED", "COMPLETE", "PASS"}:
            errors.append(f"{spec.get('id')}.status must identify executed evidence")
        if record.get("qualification_campaign_executed") is not True:
            errors.append(f"{spec.get('id')} must record an executed runtime campaign")
        execution = record.get("execution_policy")
        if not isinstance(execution, Mapping):
            errors.append(f"{spec.get('id')}.execution_policy must be an object")
        else:
            for field in (
                "governing_policy_sha",
                "newton_convergence_contract",
                "floor_aware_convergence_if_approved",
                "linear_backend",
                "line_search_policy",
                "load_step_retry_policy",
            ):
                if field not in execution:
                    errors.append(f"{spec.get('id')}.execution_policy.{field} is missing")
        negative_cases = record.get("negative_cases")
        if isinstance(negative_cases, Mapping):
            case_ids = set(negative_cases)
        elif isinstance(negative_cases, Sequence) and not isinstance(negative_cases, (str, bytes, bytearray)):
            case_ids = {item.get("case") for item in negative_cases if isinstance(item, Mapping)}
        else:
            case_ids = set()
        missing_negative_cases = sorted(_REQUIRED_NEGATIVE_CASES - case_ids)
        if missing_negative_cases:
            errors.append(f"{spec.get('id')}.negative_cases missing: {', '.join(missing_negative_cases)}")
    if role == "independent_reference":
        if record.get("track") not in TRACK_IDS:
            errors.append(f"{spec.get('id')}.track must be ACTIVE_SET or PENALTY")
        if record.get("production_contact_routines_called") is not False:
            errors.append(f"{spec.get('id')} must prove production contact routines were not called")
    return errors


def _check_status(value: Any) -> tuple[str | None, str | None]:
    if isinstance(value, str):
        return (value, None) if value in REQUIRED_STATUS else (None, "unknown status")
    if isinstance(value, Mapping):
        status = value.get("status")
        reason = value.get("reason")
        if isinstance(status, str) and status in REQUIRED_STATUS:
            return status, reason if isinstance(reason, str) else None
    return None, "missing or malformed check status"


def _track_evaluation(
    track_id: str,
    track: Mapping[str, Any],
    runtime: Mapping[str, Any],
    references: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    entry = runtime.get("track_evidence")
    if not isinstance(entry, Mapping):
        return {"status": "INCOMPLETE", "reasons": ["track_evidence is missing"]}
    if entry.get("track_status") in {"NOT_COVERED", "NOT_APPLICABLE"}:
        reason = entry.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            return {"status": "INCOMPLETE", "reasons": ["not-covered track has no controlled reason"]}
        return {"status": "NOT_COVERED", "reasons": [reason], "observed": {}}
    if entry.get("formulation") not in {None, track.get("formulation")}:
        return {"status": "INCOMPLETE", "reasons": ["runtime formulation is outside the bounded track"]}
    if entry.get("updated_search") is True or entry.get("finite_sliding") is True:
        return {"status": "INCOMPLETE", "reasons": ["updated-search/finite-sliding evidence is excluded"]}
    if entry.get("governing_execution_policy_match") is not True:
        return {"status": "INCOMPLETE", "reasons": ["governing execution policy is not explicitly matched"]}

    required_checks = track.get("required_checks", [])
    checks = entry.get("checks")
    if not isinstance(checks, Mapping):
        return {"status": "INCOMPLETE", "reasons": ["required check map is missing"]}
    missing = [name for name in required_checks if name not in checks]
    if missing:
        return {"status": "INCOMPLETE", "reasons": [f"missing checks: {', '.join(missing)}"]}

    failures: dict[str, list[str]] = {"identity": [], "equilibrium": [], "replay": [], "structural": [], "reference": []}
    malformed: list[str] = []
    not_applicable: dict[str, str] = {}
    for name in required_checks:
        status, reason = _check_status(checks[name])
        if status is None:
            malformed.append(f"{name}: {reason}")
        elif status == "NOT_APPLICABLE":
            if not reason:
                malformed.append(f"{name}: NOT_APPLICABLE requires a reason")
            else:
                not_applicable[name] = reason
        elif status == "FAIL":
            if name in _IDENTITY_CHECKS[track_id]:
                failures["identity"].append(name)
            elif name in _EQUILIBRIUM_CHECKS:
                failures["equilibrium"].append(name)
            elif name in _REPLAY_CHECKS:
                failures["replay"].append(name)
            elif name in _STRUCTURAL_CHECKS:
                failures["structural"].append(name)
            elif name in _REFERENCE_CHECKS:
                failures["reference"].append(name)
            else:
                failures["identity"].append(name)

    reference_id = track.get("independent_reference_id")
    reference = references.get(reference_id) if isinstance(reference_id, str) else None
    if reference is None:
        failures["reference"].append("independent_reference_missing")
    else:
        if reference.get("status") not in {"COMPLETE", "PASS"}:
            failures["reference"].append("independent_reference_not_complete")
        if reference.get("formulation_match") is not True:
            failures["reference"].append("formulation_mismatch")
        if reference.get("track") != track_id:
            failures["reference"].append("reference_track_mismatch")

    if malformed:
        return {"status": "INCOMPLETE", "reasons": malformed, "observed": entry.get("results", {})}
    for category in ("identity", "equilibrium", "replay", "structural", "reference"):
        if failures[category]:
            return {
                "status": category.upper(),
                "reasons": failures[category],
                "observed": entry.get("results", {}),
                "not_applicable": not_applicable,
            }
    return {
        "status": "CLOSED",
        "reasons": [],
        "observed": entry.get("results", {}),
        "not_applicable": not_applicable,
        "runtime_artifact": _artifact_id(runtime),
    }


def _final_from_tracks(track_results: Mapping[str, Mapping[str, Any]]) -> tuple[str, list[str]]:
    # The order is deliberately identical to the contract's fail-closed order.
    if any(result.get("status") == "INCOMPLETE" for result in track_results.values()):
        return "WP07_INCOMPLETE_EVIDENCE", ["at least one track is incomplete"]
    if any(result.get("status") == "IDENTITY" for result in track_results.values()):
        return "WP07_FAIL_IDENTITY", ["a formulation identity or safety invariant failed"]
    if any(result.get("status") == "EQUILIBRIUM" for result in track_results.values()):
        return "WP07_FAIL_EQUILIBRIUM", ["a vector force or moment equilibrium gate failed"]
    if any(result.get("status") == "REPLAY" for result in track_results.values()):
        return "WP07_HOLD_REPLAY", ["a replay or restart gate failed"]
    if any(result.get("status") == "STRUCTURAL" for result in track_results.values()):
        return "WP07_HOLD_STRUCTURAL_CONVERGENCE", ["a structural or refinement gate failed"]
    if any(result.get("status") == "REFERENCE" for result in track_results.values()):
        return "WP07_HOLD_REFERENCE", ["an independent reference gate failed"]

    active = track_results.get(ACTIVE_SET_ID, {}).get("status")
    penalty = track_results.get(PENALTY_ID, {}).get("status")
    if active == "CLOSED" and penalty == "NOT_COVERED":
        return "WP07_PARTIAL_ACTIVE_SET_ONLY", ["penalty track is explicitly not covered"]
    if penalty == "CLOSED" and active == "NOT_COVERED":
        return "WP07_PARTIAL_PENALTY_ONLY", ["active-set track is explicitly not covered"]
    if active == penalty == "CLOSED":
        return "WP07_PASS_BOUNDED", []
    return "WP07_INCOMPLETE_EVIDENCE", ["neither track has a complete bounded closure"]


def evaluate_closure(
    evidence: Mapping[str, Any] | Sequence[Any],
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate supplied evidence and return a deterministic, fail-closed report."""

    contract_data = dict(contract) if contract is not None else load_contract()
    contract_errors = validate_contract(contract_data)
    records = _normalise_evidence(evidence)
    artifact_results: list[dict[str, Any]] = []
    missing: list[str] = []
    malformed: list[str] = []
    for spec in _required_artifacts(contract_data):
        identifier = spec.get("id")
        record = records.get(identifier) if isinstance(identifier, str) else None
        if record is None:
            missing.append(str(identifier))
            artifact_results.append({"id": identifier, "role": spec.get("role"), "status": "MISSING"})
            continue
        errors = _validate_record(record, spec)
        if errors:
            malformed.extend(errors)
        artifact_results.append({"id": identifier, "role": spec.get("role"), "status": "VALID" if not errors else "INVALID", "errors": errors})

    runtime_id = "QF-029-WP07-D-STRUCTURAL-EVIDENCE-001"
    runtime = records.get(runtime_id)
    references = {
        identifier: record
        for identifier, record in records.items()
        if record.get("work_package") == "WP07-D" and record.get("track") in TRACK_IDS
    }
    track_results: dict[str, dict[str, Any]] = {}
    if runtime is not None and not malformed and not missing:
        runtime_tracks = runtime.get("track_evidence")
        if isinstance(runtime_tracks, Mapping):
            for track_id in TRACK_IDS:
                track = contract_data["track_separation"][track_id]
                entry = runtime_tracks.get(track_id)
                track_results[track_id] = _track_evaluation(
                    track_id,
                    track,
                    {"artifact_id": runtime_id, "track_evidence": entry},
                    references,
                )
        else:
            for track_id in TRACK_IDS:
                track_results[track_id] = {"status": "INCOMPLETE", "reasons": ["runtime track_evidence is missing"]}
    else:
        for track_id in TRACK_IDS:
            track_results[track_id] = {"status": "INCOMPLETE", "reasons": ["required artifacts are not valid"]}

    if contract_errors or missing or malformed:
        final_status = "WP07_INCOMPLETE_EVIDENCE"
        decision_reasons = []
        if contract_errors:
            decision_reasons.extend(contract_errors)
        if missing:
            decision_reasons.append(f"missing artifacts: {', '.join(missing)}")
        if malformed:
            decision_reasons.extend(malformed)
    else:
        final_status, decision_reasons = _final_from_tracks(track_results)

    limitations: list[str] = []
    for result in track_results.values():
        limitations.extend(str(reason) for reason in result.get("reasons", []))
    return {
        "schema_version": 1,
        "gate": "WP07",
        "work_package": "WP07-E",
        "status": final_status,
        "decision_reasons": decision_reasons,
        "tracks": track_results,
        "required_artifacts": artifact_results,
        "missing_artifacts": missing,
        "malformed_evidence": malformed,
        "limitations": limitations,
        "point_recommendation": {"WP07-E": "0/2", "WP07-total": "0/10"},
        "integration_train_required": True,
        "fabricated_data": False,
    }


def _load_evidence_file(path: Path) -> Mapping[str, Any] | Sequence[Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, (dict, list)):
        raise ValueError("Evidence input must be a JSON object or array.")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a fail-closed WP07-E closure report from JSON evidence.")
    parser.add_argument("--evidence", type=Path, required=True, help="JSON evidence map/array; no defaults are fabricated")
    parser.add_argument("--output", type=Path, required=True, help="Output report JSON path")
    parser.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    args = parser.parse_args(argv)
    try:
        report = evaluate_closure(_load_evidence_file(args.evidence), load_contract(args.contract))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"WP07-E report build failed closed: {exc}", file=sys.stderr)
        return 2
    print(report["status"])
    return 0 if report["status"] in {"WP07_PASS_BOUNDED", "WP07_PARTIAL_ACTIVE_SET_ONLY", "WP07_PARTIAL_PENALTY_ONLY"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
