"""Fail-closed WP07-E evidence evaluator and report builder.

The builder consumes already-produced JSON evidence. It derives qualification
gates from raw observations and the checked-in contract; reported PASS/FAIL
labels are retained for audit only and never supply a gate result.
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
REPORTED_STATUS = {"PASS", "FAIL", "INCOMPLETE", "NOT_COVERED"}
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

_IDENTITY_GATE_NAMES = {
    "open_zero_force",
    "closed_gap",
    "wrong_sign_pressure",
    "complementarity",
    "energy_gradient",
    "tangent_frobenius",
    "tangent_max_column",
    "tangent_fd",
    "tangent_symmetry",
    "no_ghost_force_after_reopen",
    "negative_cases",
    "finite",
    "no_silent_pass",
}
_EQUILIBRIUM_GATE_NAMES = {"equilibrium_force", "equilibrium_moment"}
_REPLAY_GATE_NAMES = {"replay", "rollback"}
_STRUCTURAL_GATE_NAMES = {"refinement", "accepted_load_path"}

_REQUIRED_NEGATIVE_CASES = {
    "reversed_orientation",
    "open_no_contact",
    "excessive_penetration",
    "unsupported_combination",
    "nonfinite_observable",
    "incompatible_restart_metadata",
}


class _Missing:
    pass


_MISSING = _Missing()


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
        "revision": "R1",
        "status": "PREPARATION_ONLY",
        "owner_correction": "OWNER_CORRECTION_R1",
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
    if len(ids) != len(set(ids)) or any(not isinstance(item_id, str) or not item_id for item_id in ids):
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
            raw_checks = track.get("required_checks")
            if not isinstance(raw_checks, list) or not raw_checks:
                errors.append(f"track {track_id} has no declared closure checks")
            if track.get("independent_reference_id") not in ids:
                errors.append(f"track {track_id} references an undeclared independent reference")
        updated = tracks.get("UPDATED_SEARCH_FINITE_SLIDING")
        if not isinstance(updated, Mapping) or updated.get("qualified") is not False:
            errors.append("updated-search must remain explicitly unqualified")

    raw_schema = contract.get("raw_evidence_schema")
    if not isinstance(raw_schema, Mapping) or any(track_id not in raw_schema for track_id in TRACK_IDS):
        errors.append("raw_evidence_schema must define both formulation tracks")
    identity_thresholds = contract.get("identity_thresholds")
    if not isinstance(identity_thresholds, Mapping) or any(track_id not in identity_thresholds for track_id in TRACK_IDS):
        errors.append("identity_thresholds must define both formulation tracks")

    matrix = contract.get("decision_matrix")
    if not isinstance(matrix, Mapping):
        errors.append("decision_matrix is missing")
    else:
        if matrix.get("precedence_high_to_low") != list(DECISION_PRECEDENCE):
            errors.append("decision precedence must enumerate the controlled statuses exactly")
        statuses = matrix.get("statuses")
        if not isinstance(statuses, Mapping) or any(status not in statuses for status in SUPPORTED_FINAL_STATUSES):
            errors.append("decision matrix must describe every supported final status")

    for field in ("equilibrium_policy", "replay_policy", "reference_policy", "negative_case_policy"):
        if not isinstance(contract.get(field), (Mapping, list)):
            errors.append(f"{field} is missing")
    execution = contract.get("execution_policy_binding")
    if not isinstance(execution, Mapping) or execution.get("status") != "PENDING_GOVERNING_BRANCH_INTEGRATION":
        errors.append("execution policy binding must remain pending integration")
    governing = contract.get("governing_execution_policy")
    if not isinstance(governing, Mapping) or not isinstance(governing.get("expected"), Mapping):
        errors.append("governing execution policy expected identity is missing")
    provenance = contract.get("provenance_contract")
    if not isinstance(provenance, Mapping):
        errors.append("provenance_contract is missing")
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
        for field in ("integrated_source_sha", "case_definition_digest", "contract_revision", "contract_digest", "environment"):
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
            expected_fields = (
                "governing_policy_sha",
                "newton_convergence_contract",
                "floor_aware_convergence_if_approved",
                "linear_backend",
                "line_search_policy",
                "load_step_retry_policy",
                "newton_iteration_counts_required",
            )
            for field in expected_fields:
                if field not in execution:
                    errors.append(f"{spec.get('id')}.execution_policy.{field} is missing")
        negative_cases = record.get("negative_cases")
        if not isinstance(negative_cases, Sequence) or isinstance(negative_cases, (str, bytes, bytearray)):
            errors.append(f"{spec.get('id')}.negative_cases must be an array")
    if role == "independent_reference":
        if not isinstance(record.get("independent_implementation"), bool):
            errors.append(f"{spec.get('id')}.independent_implementation must be boolean")
        if not isinstance(record.get("production_contact_routines_called"), bool):
            errors.append(f"{spec.get('id')}.production_contact_routines_called must be boolean")
        if not isinstance(record.get("formulation_match"), bool):
            errors.append(f"{spec.get('id')}.formulation_match must be boolean")
        if record.get("track") not in TRACK_IDS:
            errors.append(f"{spec.get('id')}.track must be ACTIVE_SET or PENALTY")
        reference_provenance = record.get("provenance")
        if isinstance(reference_provenance, Mapping) and not isinstance(reference_provenance.get("reference_implementation_sha"), str):
            errors.append(f"{spec.get('id')}.provenance.reference_implementation_sha is missing")
    return errors


def _number(value: Any, path: str, errors: list[str]) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"{path} must be a finite number")
        return None
    number = float(value)
    if not math.isfinite(number):
        errors.append(f"{path} must be finite")
        return None
    return number


def _vector(value: Any, path: str, errors: list[str]) -> list[float] | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)) or len(value) != 3:
        errors.append(f"{path} must be a 3-vector")
        return None
    result: list[float] = []
    for index, component in enumerate(value):
        number = _number(component, f"{path}[{index}]", errors)
        if number is None:
            return None
        result.append(number)
    return result


def _magnitude(value: Any, path: str, errors: list[str]) -> float | None:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        if not value:
            errors.append(f"{path} must not be empty")
            return None
        components = [_number(item, f"{path}[{index}]", errors) for index, item in enumerate(value)]
        if any(item is None for item in components):
            return None
        return math.sqrt(sum(float(item) ** 2 for item in components if item is not None))
    return _number(value, path, errors)


def _positive_scale(scales: Mapping[str, Any], name: str, path: str, errors: list[str]) -> float | None:
    value = _number(scales.get(name), f"{path}.{name}", errors)
    if value is not None and value <= 0.0:
        errors.append(f"{path}.{name} must be positive")
        return None
    return value


def _gate(name: str, observed: Any, threshold: Any, passed: bool, source: str, reason: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "observed": observed,
        "threshold": threshold,
        "derived_status": "PASS" if passed else "FAIL",
        "source": source,
    }
    if reason:
        result["reason"] = reason
    return result


def _na_gate(reason: str, source: str) -> dict[str, Any]:
    return {"observed": None, "threshold": None, "derived_status": "NOT_APPLICABLE", "source": source, "reason": reason}


def _relative_delta(value_m2: Any, value_m3: Any, scale: float, path: str, errors: list[str]) -> float | None:
    m2 = _magnitude(value_m2, f"{path}.M2", errors)
    m3 = _magnitude(value_m3, f"{path}.M3", errors)
    if m2 is None or m3 is None:
        return None
    scale_floor = max(1.0e-14, 64.0 * sys.float_info.epsilon * scale)
    return abs(m3 - m2) / max(abs(m2), abs(m3), scale_floor)


def _derive_refinement(track_id: str, entry: Mapping[str, Any], contract: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    levels = entry.get("structural_levels")
    if not isinstance(levels, Mapping):
        return {}, ["structural_levels is missing"]
    level_m2 = levels.get("M2")
    level_m3 = levels.get("M3")
    if not isinstance(level_m2, Mapping) or not isinstance(level_m3, Mapping):
        return {}, ["both M2 and M3 structural observations are required"]
    scales_m2 = level_m2.get("scales")
    scales_m3 = level_m3.get("scales")
    if not isinstance(scales_m2, Mapping) or not isinstance(scales_m3, Mapping):
        return {}, ["M2 and M3 declared physical scales are required"]

    threshold_data = contract["refinement_policy"]["thresholds"][track_id]
    result: dict[str, Any] = {}
    metric_specs = [
        ("selected_displacement", "selected_displacement", "U_char"),
        ("reaction_resultant", "support_reaction_vector", "F_char"),
        ("reaction_moment", "reaction_moment_vector", "M_char"),
        ("contact_resultant", "contact_resultant_vector", "F_char"),
    ]
    if track_id == ACTIVE_SET_ID:
        metric_specs.append(("contact_region_measure", "contact_region_measure", "dimensionless"))
    else:
        metric_specs.extend(
            [
                ("normalized_penetration", "maximum_penetration", "penetration_scale"),
                ("contact_energy", "contact_energy", "E_char"),
            ]
        )

    for metric_name, field_name, scale_name in metric_specs:
        threshold = threshold_data.get(metric_name)
        if threshold is None:
            errors.append(f"refinement threshold for {metric_name} is missing")
            continue
        if track_id == PENALTY_ID and metric_name == "contact_energy":
            applicable_m2 = level_m2.get("contact_energy_applicable")
            applicable_m3 = level_m3.get("contact_energy_applicable")
            if not isinstance(applicable_m2, bool) or not isinstance(applicable_m3, bool):
                errors.append("contact_energy_applicable must be boolean at M2 and M3")
                continue
            if not applicable_m2 and not applicable_m3:
                reason_m2 = level_m2.get("contact_energy_na_reason")
                reason_m3 = level_m3.get("contact_energy_na_reason")
                if not isinstance(reason_m2, str) or not reason_m2.strip() or reason_m2 != reason_m3:
                    errors.append("both contact-energy N/A reasons must be equal and nonempty")
                else:
                    result[metric_name] = _na_gate(reason_m2, "closure_raw")
                continue
            if applicable_m2 != applicable_m3:
                errors.append("contact_energy_applicable must agree between M2 and M3")
                continue
        if field_name not in level_m2 or field_name not in level_m3:
            errors.append(f"refinement raw field {field_name} is missing at M2 or M3")
            continue
        if track_id == PENALTY_ID and metric_name == "normalized_penetration":
            penetration_m2 = _number(level_m2.get(field_name), "structural_levels.M2.maximum_penetration", errors)
            penetration_m3 = _number(level_m3.get(field_name), "structural_levels.M3.maximum_penetration", errors)
            scale_pen_m2 = _positive_scale(scales_m2, "penetration_scale", "structural_levels.M2.scales", errors)
            scale_pen_m3 = _positive_scale(scales_m3, "penetration_scale", "structural_levels.M3.scales", errors)
            if None in (penetration_m2, penetration_m3, scale_pen_m2, scale_pen_m3):
                continue
            assert penetration_m2 is not None and penetration_m3 is not None
            assert scale_pen_m2 is not None and scale_pen_m3 is not None
            value_m2 = float(penetration_m2) / float(scale_pen_m2)
            value_m3 = float(penetration_m3) / float(scale_pen_m3)
            delta = _relative_delta(value_m2, value_m3, 1.0, metric_name, errors)
            observed = {"M2": value_m2, "M3": value_m3, "normalization": "penetration_scale"}
        elif track_id == PENALTY_ID and metric_name == "contact_energy":
            observed = None
            delta = None
        else:
            observed = None
            delta = None
        scale_m2 = 1.0 if scale_name == "dimensionless" else _positive_scale(scales_m2, scale_name, "structural_levels.M2.scales", errors)
        scale_m3 = 1.0 if scale_name == "dimensionless" else _positive_scale(scales_m3, scale_name, "structural_levels.M3.scales", errors)
        if scale_m2 is None or scale_m3 is None:
            continue
        if metric_name != "normalized_penetration":
            delta = _relative_delta(level_m2.get(field_name), level_m3.get(field_name), max(scale_m2, scale_m3), metric_name, errors)
            observed = {"M2": level_m2.get(field_name), "M3": level_m3.get(field_name)}
        threshold_value = float(threshold)
        result[metric_name] = _gate(metric_name, {"delta": delta, **(observed or {})}, threshold_value, delta is not None and delta <= threshold_value, "closure_raw")
    failed = any(gate.get("derived_status") == "FAIL" for gate in result.values())
    result["refinement"] = _gate(
        "refinement",
        {name: gate.get("observed") for name, gate in result.items() if name != "refinement"},
        "all declared M2->M3 limits",
        not errors and not failed,
        "closure_raw",
    )
    return result, errors


def _derive_equilibrium(entry: Mapping[str, Any], contract: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    equilibrium = entry.get("equilibrium")
    if not isinstance(equilibrium, Mapping):
        return {}, ["equilibrium raw observations are missing"]
    support_force = _vector(equilibrium.get("support_reaction_vector"), "equilibrium.support_reaction_vector", errors)
    external_force = _vector(equilibrium.get("external_force_vector"), "equilibrium.external_force_vector", errors)
    reaction_moment = _vector(equilibrium.get("reaction_moment_vector"), "equilibrium.reaction_moment_vector", errors)
    external_moment = _vector(equilibrium.get("external_moment_vector"), "equilibrium.external_moment_vector", errors)
    f_char = _positive_scale(equilibrium, "F_char", "equilibrium", errors)
    m_char = _positive_scale(equilibrium, "M_char", "equilibrium", errors)
    if any(value is None for value in (support_force, external_force, reaction_moment, external_moment, f_char, m_char)):
        return {}, errors
    assert support_force is not None and external_force is not None
    assert reaction_moment is not None and external_moment is not None
    assert f_char is not None and m_char is not None
    force_balance = [support_force[index] + external_force[index] for index in range(3)]
    moment_balance = [reaction_moment[index] + external_moment[index] for index in range(3)]
    force_error = math.sqrt(sum(value * value for value in force_balance)) / max(
        math.sqrt(sum(value * value for value in support_force)),
        math.sqrt(sum(value * value for value in external_force)),
        f_char,
        1.0e-14,
    )
    moment_error = math.sqrt(sum(value * value for value in moment_balance)) / max(
        math.sqrt(sum(value * value for value in reaction_moment)),
        math.sqrt(sum(value * value for value in external_moment)),
        m_char,
        1.0e-14,
    )
    policy = contract["equilibrium_policy"]
    return {
        "equilibrium_force": _gate("equilibrium_force", {"error": force_error, "balance": force_balance}, policy["force"]["threshold"], force_error <= float(policy["force"]["threshold"]), "closure_raw"),
        "equilibrium_moment": _gate("equilibrium_moment", {"error": moment_error, "balance": moment_balance, "origin": policy["moment"]["origin"]}, policy["moment"]["threshold"], moment_error <= float(policy["moment"]["threshold"]), "closure_raw"),
    }, errors


def _derive_active_identities(entry: Mapping[str, Any], contract: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    identity = entry.get("identity")
    if not isinstance(identity, Mapping):
        return {}, ["active-set identity observations are missing"]
    open_force = _vector(identity.get("open_contact_force_vector"), "identity.open_contact_force_vector", errors)
    gap = _number(identity.get("closed_gap"), "identity.closed_gap", errors)
    pressure = _number(identity.get("pressure"), "identity.pressure", errors)
    l_char = _positive_scale(identity, "L_char", "identity", errors)
    f_char = _positive_scale(identity, "F_char", "identity", errors)
    p_char = _positive_scale(identity, "P_char", "identity", errors)
    if any(value is None for value in (open_force, gap, pressure, l_char, f_char, p_char)):
        return {}, errors
    assert open_force is not None and gap is not None and pressure is not None
    assert l_char is not None and f_char is not None and p_char is not None
    open_error = math.sqrt(sum(value * value for value in open_force)) / f_char
    gap_error = abs(gap) / l_char
    wrong_sign = max(-pressure / p_char, 0.0)
    complementarity = abs(gap * pressure) / (l_char * p_char)
    thresholds = contract["identity_thresholds"][ACTIVE_SET_ID]
    return {
        "open_zero_force": _gate("open_zero_force", open_error, thresholds["open_force"], open_error <= float(thresholds["open_force"]), "closure_raw"),
        "closed_gap": _gate("closed_gap", gap_error, thresholds["closed_gap"], gap_error <= float(thresholds["closed_gap"]), "closure_raw"),
        "wrong_sign_pressure": _gate("wrong_sign_pressure", wrong_sign, thresholds["wrong_sign_pressure"], wrong_sign <= float(thresholds["wrong_sign_pressure"]), "closure_raw"),
        "complementarity": _gate("complementarity", complementarity, thresholds["complementarity"], complementarity <= float(thresholds["complementarity"]), "closure_raw"),
    }, errors


def _derive_penalty_identities(entry: Mapping[str, Any], contract: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    identity = entry.get("identity")
    if not isinstance(identity, Mapping):
        return {}, ["penalty identity observations are missing"]
    numeric_fields = (
        "energy_gradient_error",
        "tangent_frobenius_error",
        "tangent_max_column_error",
        "tangent_symmetry_error",
    )
    observed: dict[str, float] = {}
    for field in numeric_fields:
        value = _number(identity.get(field), f"identity.{field}", errors)
        if value is not None:
            observed[field] = value
    open_force = _vector(identity.get("open_contact_force_vector"), "identity.open_contact_force_vector", errors)
    reopen_force = _vector(identity.get("reopen_ghost_force_vector"), "identity.reopen_ghost_force_vector", errors)
    open_scale = _positive_scale(identity, "open_force_scale", "identity", errors)
    reopen_scale = _positive_scale(identity, "reopen_force_scale", "identity", errors)
    if open_force is None or reopen_force is None or open_scale is None or reopen_scale is None:
        return {}, errors
    open_error = math.sqrt(sum(value * value for value in open_force)) / open_scale
    reopen_error = math.sqrt(sum(value * value for value in reopen_force)) / reopen_scale
    thresholds = contract["identity_thresholds"][PENALTY_ID]
    gates: dict[str, Any] = {
        "energy_gradient": _gate("energy_gradient", observed.get("energy_gradient_error"), thresholds["energy_gradient"], "energy_gradient_error" in observed and observed["energy_gradient_error"] <= float(thresholds["energy_gradient"]), "closure_raw"),
        "tangent_frobenius": _gate("tangent_frobenius", observed.get("tangent_frobenius_error"), thresholds["tangent_frobenius"], "tangent_frobenius_error" in observed and observed["tangent_frobenius_error"] <= float(thresholds["tangent_frobenius"]), "closure_raw"),
        "tangent_max_column": _gate("tangent_max_column", observed.get("tangent_max_column_error"), thresholds["tangent_max_column"], "tangent_max_column_error" in observed and observed["tangent_max_column_error"] <= float(thresholds["tangent_max_column"]), "closure_raw"),
        "tangent_symmetry": _gate("tangent_symmetry", observed.get("tangent_symmetry_error"), thresholds["tangent_symmetry"], "tangent_symmetry_error" in observed and observed["tangent_symmetry_error"] <= float(thresholds["tangent_symmetry"]), "closure_raw"),
        "open_zero_force": _gate("open_zero_force", open_error, thresholds["open_force"], open_error <= float(thresholds["open_force"]), "closure_raw"),
        "no_ghost_force_after_reopen": _gate("no_ghost_force_after_reopen", reopen_error, thresholds["open_force"], reopen_error <= float(thresholds["open_force"]), "closure_raw"),
    }
    tangent_gates = (gates["tangent_frobenius"], gates["tangent_max_column"], gates["tangent_symmetry"])
    gates["tangent_fd"] = _gate(
        "tangent_fd",
        {name: gates[name]["observed"] for name in ("tangent_frobenius", "tangent_max_column", "tangent_symmetry")},
        "all frozen tangent limits",
        all(gate["derived_status"] == "PASS" for gate in tangent_gates),
        "closure_raw",
    )
    return gates, errors


def _derive_wp07c_support(c_record: Mapping[str, Any], contract: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    observed_results = c_record.get("observed_results")
    if not isinstance(observed_results, Mapping):
        return {}, ["WP07-C observed_results are missing"]
    thresholds = contract["identity_thresholds"][PENALTY_ID]
    fields = (
        ("penalty_energy_gradient_relative_error", "energy_gradient", thresholds["energy_gradient"]),
        ("penalty_tangent_frobenius_relative_error", "tangent_frobenius", thresholds["tangent_frobenius"]),
        ("penalty_tangent_max_column_relative_error", "tangent_max_column", thresholds["tangent_max_column"]),
        ("penalty_tangent_symmetry_relative_error", "tangent_symmetry", thresholds["tangent_symmetry"]),
        ("penalty_open_force_normalized", "open_zero_force", thresholds["open_force"]),
    )
    gates: dict[str, Any] = {}
    for field, gate_name, threshold in fields:
        value = _number(observed_results.get(field), f"WP07-C.observed_results.{field}", errors)
        if value is not None:
            gates[f"wp07c_{gate_name}"] = _gate(gate_name, value, threshold, value <= float(threshold), "WP07-C.observed_results")
    return gates, errors


def _derive_rollback(entry: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    rollback = entry.get("rollback")
    if not isinstance(rollback, Mapping):
        return {}, ["rollback raw observations are missing"]
    before = rollback.get("state_before_digest")
    trial = rollback.get("trial_state_digest")
    after = rollback.get("state_after_reject_digest")
    if not all(isinstance(value, str) and value for value in (before, trial, after)):
        return {}, ["rollback state digests must be nonempty strings"]
    preserved = before == after
    return {"rollback": _gate("rollback", {"before": before, "trial": trial, "after_reject": after}, True, preserved, "closure_raw")}, errors


def _derive_load_path(entry: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    load_path = entry.get("load_path")
    if not isinstance(load_path, Mapping) or not isinstance(load_path.get("step_statuses"), list):
        return {}, ["accepted load path step_statuses are missing"]
    statuses = load_path["step_statuses"]
    accepted = bool(statuses) and all(status == "ACCEPTED" for status in statuses)
    return {"accepted_load_path": _gate("accepted_load_path", statuses, "all steps ACCEPTED", accepted, "closure_raw")}, errors


def _compare_values(first: Any, second: Any, path: str, errors: list[str], relative_errors: list[float]) -> None:
    if isinstance(first, bool) or isinstance(second, bool):
        if first is not second:
            errors.append(f"{path}: boolean mismatch")
        return
    if isinstance(first, (int, float)) and isinstance(second, (int, float)):
        if isinstance(first, int) and isinstance(second, int):
            if first != second:
                errors.append(f"{path}: exact integer mismatch")
            return
        a = float(first)
        b = float(second)
        if not math.isfinite(a) or not math.isfinite(b):
            errors.append(f"{path}: nonfinite replay value")
            return
        difference = abs(a - b)
        relative = difference / max(abs(a), abs(b), 1.0e-14)
        relative_errors.append(relative)
        if difference > max(1.0e-14, 1.0e-12 * max(abs(a), abs(b))):
            errors.append(f"{path}: numeric mismatch")
        return
    if isinstance(first, str) or isinstance(second, str):
        if first != second:
            errors.append(f"{path}: exact value mismatch")
        return
    if isinstance(first, Mapping) and isinstance(second, Mapping):
        if set(first) != set(second):
            errors.append(f"{path}: mapping keys mismatch")
            return
        for key in sorted(first):
            _compare_values(first[key], second[key], f"{path}.{key}", errors, relative_errors)
        return
    if isinstance(first, Sequence) and isinstance(second, Sequence) and not isinstance(first, (str, bytes, bytearray)) and not isinstance(second, (str, bytes, bytearray)):
        if len(first) != len(second):
            errors.append(f"{path}: sequence length mismatch")
            return
        for index, (left, right) in enumerate(zip(first, second)):
            _compare_values(left, right, f"{path}[{index}]", errors, relative_errors)
        return
    if first != second:
        errors.append(f"{path}: value mismatch")


def _derive_replay(track_id: str, entry: Mapping[str, Any], execution_policy: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    replay = entry.get("replay")
    if not isinstance(replay, Mapping):
        return {}, ["replay raw observations are missing"]
    run_a = replay.get("run_a")
    run_b = replay.get("run_b")
    if not isinstance(run_a, Mapping) or not isinstance(run_b, Mapping):
        return {}, ["replay requires run_a and run_b raw observations"]
    required = [
        "final_displacement",
        "reaction_vector",
        "moment_vector",
        "contact_resultant",
        "active_contact_qualitative_status",
        "active_contact_count",
        "load_factor_history",
        "terminal_classification",
    ]
    if track_id == PENALTY_ID:
        required.extend(["contact_topology_digest", "model_signature", "accepted_state_digest"])
    for field in required:
        if field not in run_a or field not in run_b:
            errors.append(f"replay.{field} is required in both runs")
    if errors:
        return {}, errors
    comparison_errors: list[str] = []
    relative_errors: list[float] = []
    exact_fields = {"active_contact_qualitative_status", "active_contact_count", "terminal_classification"}
    for field in required:
        if field in exact_fields or field.endswith("_digest") or field == "model_signature":
            if run_a[field] != run_b[field]:
                comparison_errors.append(f"replay.{field}: exact value mismatch")
        else:
            _compare_values(run_a[field], run_b[field], f"replay.{field}", comparison_errors, relative_errors)
    newton_required = execution_policy.get("newton_iteration_counts_required")
    if not isinstance(newton_required, bool):
        errors.append("execution_policy.newton_iteration_counts_required must be boolean")
    elif newton_required:
        if "newton_iteration_counts" not in run_a or "newton_iteration_counts" not in run_b:
            errors.append("replay.newton_iteration_counts is required by governing policy")
        elif run_a["newton_iteration_counts"] != run_b["newton_iteration_counts"]:
            comparison_errors.append("replay.newton_iteration_counts: exact sequence mismatch")
    if errors:
        return {}, errors
    observed = {
        "mismatches": comparison_errors,
        "max_relative_error": max(relative_errors, default=0.0),
        "load_history_length": [len(run_a["load_factor_history"]), len(run_b["load_factor_history"])],
        "newton_iteration_counts_required": newton_required,
    }
    return {"replay": _gate("replay", observed, {"relative": 1.0e-12, "absolute_floor": 1.0e-14}, not comparison_errors, "closure_raw")}, []


def _reference_metrics(track_id: str) -> dict[str, str]:
    if track_id == ACTIVE_SET_ID:
        return {
            "selected_displacement": "selected_displacement",
            "reaction_resultant": "reaction_resultant",
            "reaction_moment": "reaction_moment",
            "contact_resultant": "contact_resultant",
            "contact_region_measure": "contact_region_measure",
        }
    return {
        "selected_displacement": "selected_displacement",
        "reaction_resultant": "reaction_resultant",
        "reaction_moment": "reaction_moment",
        "contact_resultant": "contact_resultant",
        "normalized_penetration": "penetration",
    }


def _derive_reference(track_id: str, reference: Mapping[str, Any], contract: Mapping[str, Any]) -> tuple[dict[str, Any], list[str], bool]:
    errors: list[str] = []
    raw = reference.get("raw_comparisons")
    if not isinstance(raw, Mapping):
        return {}, ["reference.raw_comparisons is missing"], False
    if reference.get("independent_implementation") is not True or reference.get("production_contact_routines_called") is not False or reference.get("formulation_match") is not True or reference.get("track") != track_id:
        return {}, [], True
    policy = contract["reference_policy"]["active_set" if track_id == ACTIVE_SET_ID else "penalty"]
    gates: dict[str, Any] = {}
    for result_name, raw_name in _reference_metrics(track_id).items():
        comparison = raw.get(raw_name)
        if not isinstance(comparison, Mapping):
            errors.append(f"reference.raw_comparisons.{raw_name} is missing")
            continue
        scale = _number(comparison.get("scale"), f"reference.{raw_name}.scale", errors)
        qf_mag = _magnitude(comparison.get("qf"), f"reference.{raw_name}.qf", errors)
        ref_mag = _magnitude(comparison.get("reference"), f"reference.{raw_name}.reference", errors)
        if scale is None or scale <= 0.0 or qf_mag is None or ref_mag is None:
            continue
        floor = max(1.0e-14, 64.0 * sys.float_info.epsilon * scale)
        delta = abs(qf_mag - ref_mag) / max(abs(qf_mag), abs(ref_mag), floor)
        threshold_name = {
            "selected_displacement": "displacement",
            "contact_region_measure": "active_region_measure",
            "normalized_penetration": "penetration",
        }.get(result_name, result_name)
        threshold = policy[threshold_name]
        gate_name = f"reference_{result_name}"
        gates[gate_name] = _gate(gate_name, {"qf": comparison["qf"], "reference": comparison["reference"], "delta": delta}, threshold, delta <= float(threshold), "reference_raw")
    failed = any(gate.get("derived_status") == "FAIL" for gate in gates.values())
    if errors:
        return gates, errors, False
    derived_status = "FAIL" if failed else "PASS"
    reported_status = reference.get("reported_status")
    status_mismatch = reported_status is not None and reported_status != derived_status
    gates["reference"] = _gate("reference", {name: gate.get("observed") for name, gate in gates.items()}, "all frozen reference limits", not failed, "reference_raw")
    return gates, [], status_mismatch


def _derive_negative_cases(runtime: Mapping[str, Any], contract: Mapping[str, Any]) -> tuple[dict[str, Any], list[str], bool]:
    negative_cases = runtime.get("negative_cases")
    if not isinstance(negative_cases, Sequence) or isinstance(negative_cases, (str, bytes, bytearray)):
        return {}, ["negative_cases must be an array"], False
    expected: dict[str, set[str]] = {}
    for item in contract["negative_case_policy"]:
        if isinstance(item, Mapping) and isinstance(item.get("case"), str):
            accepted = item.get("accepted_classifications")
            if isinstance(accepted, list) and all(isinstance(value, str) for value in accepted):
                expected[item["case"]] = set(accepted)
    observed: dict[str, str] = {}
    wrong: list[str] = []
    for item in negative_cases:
        if not isinstance(item, Mapping) or not isinstance(item.get("case"), str):
            wrong.append("malformed negative case")
            continue
        case_id = item["case"]
        classification = item.get("observed_classification", item.get("classification"))
        if not isinstance(classification, str):
            wrong.append(f"{case_id}: classification missing")
            continue
        if case_id in observed:
            wrong.append(f"{case_id}: duplicate case")
        observed[case_id] = classification
        if case_id not in expected or classification not in expected[case_id]:
            wrong.append(f"{case_id}: unexpected classification {classification}")
    missing = sorted(_REQUIRED_NEGATIVE_CASES - set(observed))
    if missing:
        return {"negative_cases": {"observed": observed, "missing": missing}}, [f"negative cases missing: {', '.join(missing)}"], False
    gate = _gate("negative_cases", observed, "declared classifications", not wrong, "closure_raw")
    return {"negative_cases": gate}, [], bool(wrong)


def _validate_execution_policy(runtime: Mapping[str, Any], contract: Mapping[str, Any]) -> list[str]:
    execution = runtime.get("execution_policy")
    expected_section = contract.get("governing_execution_policy")
    if not isinstance(execution, Mapping) or not isinstance(expected_section, Mapping) or not isinstance(expected_section.get("expected"), Mapping):
        return ["governing execution policy identity is missing"]
    errors: list[str] = []
    for field, expected in expected_section["expected"].items():
        if execution.get(field) != expected:
            errors.append(f"execution_policy.{field} does not match governing identity")
    return errors


def _validate_cross_provenance(runtime: Mapping[str, Any], references: Mapping[str, Mapping[str, Any]], contract: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    runtime_provenance = runtime.get("provenance")
    provenance_contract = contract["provenance_contract"]
    if not isinstance(runtime_provenance, Mapping):
        return ["runtime provenance is missing"]
    expected_revision = provenance_contract["expected_contract_revision"]
    expected_digest = provenance_contract["expected_contract_digest"]
    for field, expected in (("contract_revision", expected_revision), ("contract_digest", expected_digest)):
        if runtime_provenance.get(field) != expected:
            errors.append(f"runtime.provenance.{field} does not match closure contract")
    integrated_sha = runtime_provenance.get("integrated_source_sha")
    case_digest = runtime_provenance.get("case_definition_digest")
    if not isinstance(integrated_sha, str) or not integrated_sha or not isinstance(case_digest, str) or not case_digest:
        errors.append("runtime provenance integrated source and case digest are required")
    runtime_tracks = runtime.get("track_evidence")
    if isinstance(runtime_tracks, Mapping) and isinstance(case_digest, str):
        for track_id in TRACK_IDS:
            entry = runtime_tracks.get(track_id)
            if not isinstance(entry, Mapping):
                continue
            levels = entry.get("structural_levels")
            if isinstance(levels, Mapping):
                for level_id in ("M2", "M3"):
                    level = levels.get(level_id)
                    if isinstance(level, Mapping) and level.get("case_definition_digest") != case_digest:
                        errors.append(f"{track_id}.{level_id}.case_definition_digest is stale or mixed")
    for identifier, reference in references.items():
        ref_provenance = reference.get("provenance")
        if not isinstance(ref_provenance, Mapping):
            errors.append(f"{identifier}.provenance is missing")
            continue
        if ref_provenance.get("integrated_source_sha") != integrated_sha:
            errors.append(f"{identifier}.provenance.integrated_source_sha does not match runtime")
        if ref_provenance.get("case_definition_digest") != case_digest:
            errors.append(f"{identifier}.provenance.case_definition_digest does not match runtime")
        if ref_provenance.get("contract_revision") != expected_revision:
            errors.append(f"{identifier}.provenance.contract_revision does not match closure contract")
        if ref_provenance.get("contract_digest") != expected_digest:
            errors.append(f"{identifier}.provenance.contract_digest is stale")
    return errors


def _track_evaluation(
    track_id: str,
    track_contract: Mapping[str, Any],
    entry: Any,
    runtime: Mapping[str, Any],
    c_record: Mapping[str, Any],
    reference: Mapping[str, Any],
    contract: Mapping[str, Any],
    negative_gate: Mapping[str, Any],
    negative_errors: list[str],
    negative_wrong: bool,
) -> dict[str, Any]:
    if not isinstance(entry, Mapping):
        return {"status": "INCOMPLETE", "derived_status": "INCOMPLETE", "reasons": ["track raw evidence is missing"], "gates": {}}
    explicit_status = entry.get("track_status")
    if explicit_status in {"NOT_COVERED", "NOT_APPLICABLE"}:
        reason = entry.get("reason")
        if entry.get("owner_authorized_exclusion") is not True or not isinstance(reason, str) or not reason.strip():
            return {"status": "INCOMPLETE", "derived_status": "INCOMPLETE", "reasons": ["not-covered track requires Owner authorization and reason"], "gates": {}}
        if entry.get("reported_status") not in {None, "NOT_COVERED"}:
            return {"status": "INCOMPLETE", "derived_status": "INCOMPLETE", "reasons": ["a not-covered track cannot report a failing generated result"], "gates": {}}
        raw_keys = {"structural_levels", "identity", "equilibrium", "replay", "rollback", "load_path"}
        if raw_keys.intersection(entry):
            return {"status": "INCOMPLETE", "derived_status": "INCOMPLETE", "reasons": ["failing/generated raw evidence cannot be converted to NOT_COVERED partial"], "gates": {}}
        return {"status": "NOT_COVERED", "derived_status": "NOT_COVERED", "reported_status": entry.get("reported_status"), "reasons": [reason], "gates": {}}
    if explicit_status not in {None, "COMPLETE"}:
        return {"status": "INCOMPLETE", "derived_status": "INCOMPLETE", "reasons": ["unknown track_status"], "gates": {}}
    if entry.get("formulation") != track_contract.get("formulation"):
        return {"status": "INCOMPLETE", "derived_status": "INCOMPLETE", "reasons": ["runtime formulation is outside bounded track"], "gates": {}}
    if entry.get("updated_search") is True or entry.get("finite_sliding") is True:
        return {"status": "INCOMPLETE", "derived_status": "INCOMPLETE", "reasons": ["updated-search/finite-sliding evidence is excluded"], "gates": {}}

    gates: dict[str, Any] = {}
    errors: list[str] = []
    if track_id == ACTIVE_SET_ID:
        identity_gates, identity_errors = _derive_active_identities(entry, contract)
        gates.update(identity_gates)
        errors.extend(identity_errors)
    else:
        identity_gates, identity_errors = _derive_penalty_identities(entry, contract)
        gates.update(identity_gates)
        errors.extend(identity_errors)
        support_gates, support_errors = _derive_wp07c_support(c_record, contract)
        gates.update(support_gates)
        errors.extend(support_errors)
        rollback_gates, rollback_errors = _derive_rollback(entry)
        gates.update(rollback_gates)
        errors.extend(rollback_errors)
        load_gates, load_errors = _derive_load_path(entry)
        gates.update(load_gates)
        errors.extend(load_errors)

    refinement_gates, refinement_errors = _derive_refinement(track_id, entry, contract)
    gates.update(refinement_gates)
    errors.extend(refinement_errors)
    equilibrium_gates, equilibrium_errors = _derive_equilibrium(entry, contract)
    gates.update(equilibrium_gates)
    errors.extend(equilibrium_errors)
    replay_gates, replay_errors = _derive_replay(track_id, entry, runtime["execution_policy"])
    gates.update(replay_gates)
    errors.extend(replay_errors)
    reference_gates, reference_errors, reference_status_mismatch = _derive_reference(track_id, reference, contract)
    gates.update(reference_gates)
    errors.extend(reference_errors)
    gates.update(negative_gate)
    errors.extend(negative_errors)
    gates["finite"] = _gate("finite", True, True, not errors, "closure_validation")
    gates["no_silent_pass"] = _gate("no_silent_pass", not negative_wrong, True, not negative_wrong and not negative_errors, "closure_raw")

    if errors:
        return {
            "status": "INCOMPLETE",
            "derived_status": "INCOMPLETE",
            "reported_status": entry.get("reported_status"),
            "status_mismatch": False,
            "reasons": errors,
            "gates": gates,
        }
    failed_names = [name for name, gate in gates.items() if gate.get("derived_status") == "FAIL"]
    derived_status = "FAIL" if failed_names else "PASS"
    reported_status = entry.get("reported_status")
    if reported_status is not None and reported_status not in REPORTED_STATUS:
        return {
            "status": "INCOMPLETE",
            "derived_status": derived_status,
            "reported_status": reported_status,
            "status_mismatch": True,
            "reasons": ["reported_status is not a controlled value"],
            "gates": gates,
        }
    status_mismatch = reference_status_mismatch or (reported_status is not None and reported_status != derived_status)
    if failed_names:
        if any(name in _IDENTITY_GATE_NAMES or name.startswith("wp07c_") for name in failed_names):
            status = "IDENTITY"
        elif any(name in _EQUILIBRIUM_GATE_NAMES for name in failed_names):
            status = "EQUILIBRIUM"
        elif any(name in _REPLAY_GATE_NAMES for name in failed_names):
            status = "REPLAY"
        elif any(name.startswith("reference_") or name == "reference" for name in failed_names):
            status = "REFERENCE"
        elif any(name in _STRUCTURAL_GATE_NAMES or name in {"selected_displacement", "reaction_resultant", "reaction_moment", "contact_resultant", "contact_region_measure", "normalized_penetration", "contact_energy", "refinement"} for name in failed_names):
            status = "STRUCTURAL"
        else:
            status = "REFERENCE"
    elif status_mismatch:
        status = "STATUS_MISMATCH"
    else:
        status = "CLOSED"
    return {
        "status": status,
        "derived_status": derived_status,
        "reported_status": reported_status,
        "status_mismatch": status_mismatch,
        "reasons": failed_names,
        "gates": gates,
        "observed": entry.get("observed", {}),
    }


def _final_from_tracks(track_results: Mapping[str, Mapping[str, Any]]) -> tuple[str, list[str]]:
    if any(result.get("status") in {"INCOMPLETE", "STATUS_MISMATCH"} for result in track_results.values()):
        return "WP07_INCOMPLETE_EVIDENCE", ["required raw evidence or reported/derived status consistency is incomplete"]
    if any(result.get("status") == "IDENTITY" for result in track_results.values()):
        return "WP07_FAIL_IDENTITY", ["a derived formulation identity or safety invariant failed"]
    if any(result.get("status") == "EQUILIBRIUM" for result in track_results.values()):
        return "WP07_FAIL_EQUILIBRIUM", ["a derived vector force or moment equilibrium gate failed"]
    if any(result.get("status") == "REPLAY" for result in track_results.values()):
        return "WP07_HOLD_REPLAY", ["a derived replay or restart gate failed"]
    if any(result.get("status") == "STRUCTURAL" for result in track_results.values()):
        return "WP07_HOLD_STRUCTURAL_CONVERGENCE", ["a derived structural or refinement gate failed"]
    if any(result.get("status") == "REFERENCE" for result in track_results.values()):
        return "WP07_HOLD_REFERENCE", ["a derived independent reference gate failed"]
    active = track_results.get(ACTIVE_SET_ID, {}).get("status")
    penalty = track_results.get(PENALTY_ID, {}).get("status")
    if active == "CLOSED" and penalty == "NOT_COVERED":
        return "WP07_PARTIAL_ACTIVE_SET_ONLY", ["penalty track is explicitly Owner-authorized as not covered"]
    if penalty == "CLOSED" and active == "NOT_COVERED":
        return "WP07_PARTIAL_PENALTY_ONLY", ["active-set track is explicitly Owner-authorized as not covered"]
    if active == penalty == "CLOSED":
        return "WP07_PASS_BOUNDED", []
    return "WP07_INCOMPLETE_EVIDENCE", ["neither track has a complete bounded closure"]


def evaluate_closure(evidence: Mapping[str, Any] | Sequence[Any], contract: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Derive WP07-E closure status from raw supplied evidence only."""

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
    active_reference_id = "QF-029-WP07-D-REFERENCE-ACTIVE-SET-001"
    penalty_reference_id = "QF-029-WP07-D-REFERENCE-PENALTY-001"
    runtime = records.get(runtime_id)
    c_record = records.get("QF-029-WP07-C-CONTACT-IDENTITIES-001", {})
    references = {
        ACTIVE_SET_ID: records.get(active_reference_id, {}),
        PENALTY_ID: records.get(penalty_reference_id, {}),
    }
    global_errors = list(contract_errors)
    if runtime is not None and not missing and not malformed:
        global_errors.extend(_validate_execution_policy(runtime, contract_data))
        global_errors.extend(_validate_cross_provenance(runtime, {identifier: records[identifier] for identifier in (active_reference_id, penalty_reference_id) if identifier in records}, contract_data))

    track_results: dict[str, dict[str, Any]] = {}
    if runtime is not None and not missing and not malformed and not global_errors:
        runtime_tracks = runtime.get("track_evidence")
        negative_gate, negative_errors, negative_wrong = _derive_negative_cases(runtime, contract_data)
        if not isinstance(runtime_tracks, Mapping):
            global_errors.append("runtime.track_evidence is missing")
            for track_id in TRACK_IDS:
                track_results[track_id] = {"status": "INCOMPLETE", "derived_status": "INCOMPLETE", "reasons": ["runtime.track_evidence is missing"], "gates": {}}
        else:
            for track_id in TRACK_IDS:
                track_contract = contract_data["track_separation"][track_id]
                track_results[track_id] = _track_evaluation(
                    track_id,
                    track_contract,
                    runtime_tracks.get(track_id),
                    runtime,
                    c_record,
                    references[track_id],
                    contract_data,
                    negative_gate,
                    negative_errors,
                    negative_wrong,
                )
    else:
        for track_id in TRACK_IDS:
            track_results[track_id] = {"status": "INCOMPLETE", "derived_status": "INCOMPLETE", "reasons": ["required artifacts, provenance or governing policy are invalid"], "gates": {}}

    if global_errors or missing or malformed:
        final_status = "WP07_INCOMPLETE_EVIDENCE"
        reasons = list(global_errors)
        if missing:
            reasons.append(f"missing artifacts: {', '.join(missing)}")
        reasons.extend(malformed)
    else:
        final_status, reasons = _final_from_tracks(track_results)
    status_mismatches = [track_id for track_id, result in track_results.items() if result.get("status_mismatch")]
    limitations = [
        str(reason)
        for result in track_results.values()
        for reason in result.get("reasons", [])
    ]
    return {
        "schema_version": 1,
        "gate": "WP07",
        "work_package": "WP07-E",
        "status": final_status,
        "decision_reasons": reasons,
        "tracks": track_results,
        "status_mismatches": status_mismatches,
        "required_artifacts": artifact_results,
        "missing_artifacts": missing,
        "malformed_evidence": malformed,
        "global_validation_errors": global_errors,
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
    parser = argparse.ArgumentParser(description="Build a fail-closed WP07-E closure report from raw JSON evidence.")
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
