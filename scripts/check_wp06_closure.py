"""Preparation-only WP06-F closure checks for synthetic or future evidence."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "qualification" / "0_2_9" / "wp06f_closure_contract.json"
REQUIRED_PROVENANCE = (
    "repository",
    "branch",
    "source_sha",
    "contract_revision",
    "contract_digest",
    "case_definition_digest",
    "solver_policy_digest",
    "element_formulation_identity",
)
PHASE1_IDS = frozenset(
    {
        "WP06-D-RAW",
        "WP06-D-REFERENCE",
        "WP06-D-REPLAY",
        "WP06-E-RAW",
        "WP06-E-REFERENCE",
        "WP06-E-REPLAY",
    }
)


def load_contract() -> dict[str, Any]:
    """Load the machine-readable closure contract without executing mechanics."""
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def assert_preparation_only() -> None:
    """Fail closed if this preparation helper is asked to execute a solve."""
    contract = load_contract()
    guard = contract["execution_guard"]
    if any(bool(guard[key]) for key in guard if key.endswith("_run")):
        raise RuntimeError("WP06-F preparation guard forbids execution")


def _finite(value: Any) -> bool:
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return math.isfinite(float(value))
    if isinstance(value, Mapping):
        return all(_finite(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(_finite(item) for item in value)
    return True


def _all_equal(values: list[Any]) -> bool:
    return bool(values) and all(value == values[0] for value in values[1:])


def _close(a: Any, b: Any, *, relative: float = 1.0e-12, absolute: float = 1.0e-14) -> bool:
    if isinstance(a, Mapping) and isinstance(b, Mapping):
        return set(a) == set(b) and all(_close(a[key], b[key], relative=relative, absolute=absolute) for key in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(_close(x, y, relative=relative, absolute=absolute) for x, y in zip(a, b))
    if isinstance(a, bool) or isinstance(b, bool) or isinstance(a, str) or isinstance(b, str):
        return a == b
    try:
        left, right = float(a), float(b)
    except (TypeError, ValueError):
        return a == b
    return abs(left - right) <= max(absolute, relative * max(abs(left), abs(right)))


def _vector_norm(vector: list[float]) -> float:
    return math.sqrt(sum(float(component) ** 2 for component in vector))


def _equilibrium_error(left: list[float], right: list[float], scale: float, floor: float) -> float:
    return _vector_norm([a + b for a, b in zip(left, right)]) / max(_vector_norm(left), _vector_norm(right), scale, floor)


def _refinement_pass(raw: Mapping[str, Any], limits: Mapping[str, float]) -> bool:
    for name, threshold in limits.items():
        item = raw["refinement"][name]
        scale_floor = float(item["scale_floor"])
        delta = abs(float(item["m3"]) - float(item["m2"])) / max(abs(float(item["m2"])), abs(float(item["m3"])), scale_floor)
        if not math.isfinite(delta) or delta > float(threshold):
            return False
    return True


def _reference_pass(raw: Mapping[str, Any], limits: Mapping[str, float]) -> bool:
    for name, threshold in limits.items():
        item = raw["reference"][name]
        observed = float(item["qf"])
        reference = float(item["reference"])
        scale_floor = float(item["scale_floor"])
        error = abs(observed - reference) / max(abs(observed), abs(reference), scale_floor)
        if not math.isfinite(error) or error > float(threshold):
            return False
    return True


def _provenance_status(payload: Mapping[str, Any], contract: Mapping[str, Any]) -> str | None:
    artifacts = payload.get("artifacts", {})
    required = contract["required_artifact_manifest"]
    for item in required:
        record = artifacts.get(item["id"])
        if not isinstance(record, Mapping) or not record.get("present", False):
            return "WP06_INCOMPLETE_EVIDENCE"
    expected = payload.get("phase1_binding")
    if not isinstance(expected, Mapping) or not all(expected.get(key) for key in REQUIRED_PROVENANCE):
        return "WP06_INVALID_EVIDENCE"
    for item in required:
        record = artifacts[item["id"]]
        provenance = record.get("provenance")
        if not isinstance(provenance, Mapping) or not all(provenance.get(key) for key in REQUIRED_PROVENANCE):
            return "WP06_INCOMPLETE_EVIDENCE"
        if provenance.get("repository") != contract["source_repository"]:
            return "WP06_INVALID_EVIDENCE"
        if item["id"] in PHASE1_IDS and any(provenance.get(key) != expected.get(key) for key in REQUIRED_PROVENANCE):
            return "WP06_INVALID_EVIDENCE"
        if item["id"] in {"WP06-D-REFERENCE", "WP06-E-REFERENCE"} and not provenance.get("reference_implementation_digest"):
            return "WP06_INCOMPLETE_EVIDENCE"
    return None


def evaluate_closure(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Derive a fail-closed WP06 status from raw observations.

    This helper is intentionally not a solver runner. It accepts evidence
    already produced by a future Phase-1 campaign and never executes a
    structural or reference calculation.
    """
    contract = load_contract()
    assert_preparation_only()
    provenance_status = _provenance_status(payload, contract)
    if provenance_status:
        return {"status": provenance_status, "reason": "artifact/provenance validation"}
    if payload.get("production_mechanics_changed", False):
        return {"status": "WP06_INVALID_EVIDENCE", "reason": "production mechanics changed"}
    d_raw = payload.get("d_raw")
    e_raw = payload.get("e_raw")
    if not isinstance(d_raw, Mapping) or not isinstance(e_raw, Mapping):
        return {"status": "WP06_INCOMPLETE_EVIDENCE", "reason": "raw D/E evidence missing"}
    if not _finite(payload):
        return {"status": "WP06_INCOMPLETE_EVIDENCE", "reason": "nonfinite evidence"}
    if d_raw.get("benchmark_id") != contract["raw_evidence_schema"]["d"]["benchmark_id"]:
        return {"status": "WP06_INVALID_EVIDENCE", "reason": "wrong D benchmark"}
    if e_raw.get("benchmark_id") != contract["raw_evidence_schema"]["e"]["benchmark_id"]:
        return {"status": "WP06_INVALID_EVIDENCE", "reason": "wrong E benchmark"}
    if e_raw.get("alpha_over_l") != contract["raw_evidence_schema"]["e"]["alpha_over_l"]:
        return {"status": "WP06_INVALID_EVIDENCE", "reason": "wrong E imperfection amplitude"}
    if e_raw.get("mode_based_substitution") or e_raw.get("branch_switch_claim") or e_raw.get("bifurcation_detection_claim"):
        return {"status": "WP06_INVALID_EVIDENCE", "reason": "unsupported claim in E evidence"}
    if d_raw.get("load_rule") != contract["raw_evidence_schema"]["d"]["load_rule"]:
        return {"status": "WP06_INVALID_EVIDENCE", "reason": "wrong D load rule"}
    if d_raw.get("m4_declared") or d_raw.get("altered_physics_retry") or d_raw.get("result_dependent_threshold_change"):
        return {"status": "WP06_INVALID_EVIDENCE", "reason": "D evidence violates frozen contract"}
    if not d_raw.get("mesh_digests_match", False):
        return {"status": "WP06_INVALID_EVIDENCE", "reason": "D mesh digest mismatch"}
    d_limits = contract["thresholds"]["d_refinement"]
    e_limits = contract["thresholds"]["e_reference"]
    if not _refinement_pass(d_raw, d_limits) or not _refinement_pass(e_raw, d_limits):
        return {"status": "WP06_HOLD_STRUCTURAL", "reason": "derived refinement threshold failure"}
    force_limit = float(contract["thresholds"]["equilibrium_force"])
    moment_limit = float(contract["thresholds"]["equilibrium_moment"])
    for raw in (d_raw, e_raw):
        force_error = _equilibrium_error(raw["equilibrium"]["support_reaction"], raw["equilibrium"]["external_force"], raw["equilibrium"]["force_scale"], 1.0e-14)
        moment_error = _equilibrium_error(raw["equilibrium"]["reaction_moment"], raw["equilibrium"]["external_moment"], raw["equilibrium"]["moment_scale"], 1.0e-14)
        if force_error > force_limit or moment_error > moment_limit:
            return {"status": "WP06_FAIL_EQUILIBRIUM", "reason": "derived vector equilibrium failure"}
        if not raw.get("envelope_pass", False) or not raw.get("replay_pass", False) or not raw.get("required_observables_complete", True):
            return {"status": "WP06_HOLD_STRUCTURAL", "reason": "envelope/replay/observable gate failure"}
    for raw in (d_raw, e_raw):
        if not _reference_pass(raw, e_limits) or not raw.get("reference_independent", False) or raw.get("reference_production_routines_called", True):
            return {"status": "WP06_HOLD_REFERENCE", "reason": "derived reference gate failure"}
    reports = [payload.get("reported_status"), d_raw.get("reported_status"), e_raw.get("reported_status")]
    if any(status == "PASS" for status in reports) and not all(status is None or status == "PASS" for status in reports):
        return {"status": "WP06_STATUS_MISMATCH", "reason": "reported status contradicts derived evidence"}
    if not all(_close(payload["replay_a"], payload["replay_b"]) for _ in (0,)):
        return {"status": "WP06_HOLD_REPLAY", "reason": "derived replay mismatch"}
    return {"status": "WP06_PASS_BOUNDED", "reason": "all derived D/E closure gates pass"}


if __name__ == "__main__":
    assert_preparation_only()
    print("WP06-F preparation guard: no structural execution")
