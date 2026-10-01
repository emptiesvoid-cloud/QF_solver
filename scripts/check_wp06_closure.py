"""Preparation-only WP06-F closure checks for synthetic or future evidence."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "qualification" / "0_2_9" / "wp06f_closure_contract.json"
CONTROLLED_PATHS = {
    "a": ROOT / "qualification" / "0_2_9" / "wp06a_arc_length_formulation_contract.json",
    "b": ROOT / "qualification" / "0_2_9" / "wp06b_continuation_state_rollback.json",
    "c": ROOT / "qualification" / "0_2_9" / "wp06c_arc_length_predictor_corrector_identities.json",
    "d": ROOT / "qualification" / "0_2_9" / "wp06d_structural_limit_point_contract.json",
    "e": ROOT / "qualification" / "0_2_9" / "wp06e_postbuckling_imperfection_contract.json",
}
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
SHARED_PHASE1_PROVENANCE = ("repository", "branch", "source_sha", "solver_policy_digest")
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
TRACK_ARTIFACTS = {
    "d": frozenset({"WP06-D-RAW", "WP06-D-REFERENCE", "WP06-D-REPLAY"}),
    "e": frozenset({"WP06-E-RAW", "WP06-E-REFERENCE", "WP06-E-REPLAY"}),
}
REPLAY_FIELDS = (
    "accepted_displacement_path",
    "lambda_path",
    "radius_history",
    "orientation_history",
    "accepted_rejected_steps",
    "newton_counts",
    "terminal_classification",
)
POLICY_IDENTITY_FIELDS = (
    "governing_policy_sha",
    "formulation_label",
    "residual_form",
    "orientation_policy",
    "newton_convergence_contract",
    "floor_aware_convergence_policy",
    "linear_backend",
    "line_search_policy",
    "load_step_retry_policy",
    "arc_length_termination_policy",
    "policy_digest",
)
EXPECTED_FORMULATION = "SPHERICAL_ARC_LENGTH_CUSTOM"
EXPECTED_D_LOAD_RULE = "MESH_INDEPENDENT_GEOMETRIC_POINT_LOAD"
EXPECTED_E_ROUTE = "nonlinear_static / arc_length"
EXPECTED_E_ELEMENT_FORMULATION = "TET4 Total-Lagrangian StVK"
EXPECTED_E_IMPERFECTION_FORMULA = "Z_imperfect = Z0 + alpha*(1-cos(0.5*pi*X/L))"
EXPECTED_E_ALPHA_OVER_L = 0.005


def load_contract() -> dict[str, Any]:
    """Load the machine-readable closure contract without executing mechanics."""
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _load_controlled(name: str) -> dict[str, Any]:
    return json.loads(CONTROLLED_PATHS[name].read_text(encoding="utf-8"))


def _canonical_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def controlled_anchors() -> dict[str, Any]:
    """Derive closure identities from the controlled A/B/C/D/E contracts."""
    a, b, c, d, e = (_load_controlled(name) for name in ("a", "b", "c", "d", "e"))
    d_benchmark = d["benchmark"]
    e_benchmark = e["benchmark"]
    if c["formulation_label"] != a["formulation_label"]:
        raise ValueError("WP06-A/C formulation identity mismatch")
    if a["formulation_label"] != EXPECTED_FORMULATION:
        raise ValueError("WP06 formulation identity is not the frozen spherical arc-length route")
    if d["continuation_policy"]["formulation"] != a["formulation_label"]:
        raise ValueError("WP06-A/D formulation identity mismatch")
    if d_benchmark["formulation_scope"]["formulation"] != a["formulation_label"]:
        raise ValueError("WP06-A/D benchmark identity mismatch")
    if d_benchmark["element_family"] != "TET4" or e_benchmark["element_family"] != "TET4":
        raise ValueError("WP06 D/E element identity mismatch")
    if f'{e_benchmark["route"]} / {e_benchmark["method"]}' != EXPECTED_E_ROUTE:
        raise ValueError("WP06-E route identity mismatch")
    if d["load_assembly_contract"]["rule"] != EXPECTED_D_LOAD_RULE:
        raise ValueError("WP06-D load rule is not frozen")
    if e_benchmark["imperfection"]["formula"] != EXPECTED_E_IMPERFECTION_FORMULA:
        raise ValueError("WP06-E imperfection formula is not frozen")
    if e_benchmark["imperfection"]["primary_alpha_over_L"] != EXPECTED_E_ALPHA_OVER_L:
        raise ValueError("WP06-E imperfection amplitude is not frozen")
    d_orientation = d["continuation_policy"]["orientation_policy"]
    c_orientation = c["orientation"]["policy"]
    if not isinstance(c_orientation, list) or not all(isinstance(item, str) for item in c_orientation):
        raise ValueError("WP06-C orientation identity is invalid")
    orientation_concepts = (
        "target-load",
        "previous displacement",
        "previous load",
        "displacement branch",
        "lambda reversal",
    )
    if not all(concept in d_orientation.lower() for concept in orientation_concepts):
        raise ValueError("WP06-C/D orientation identity mismatch")
    return {
        "formulation_label": a["formulation_label"],
        "residual_form": a["residual_form"],
        "constraint_form": a["constraint_form"],
        "orientation_policy": c["orientation"]["policy"],
        "orientation_root_enumeration": c["orientation"]["root_enumeration"],
        "state_owner": b["state_owner"],
        "state_schema_digest": _canonical_digest(b["state_schema"]),
        "rollback_contract_digest": _canonical_digest(b["rollback_contract"]),
        "element_formulation": EXPECTED_E_ELEMENT_FORMULATION,
        "d_benchmark_id": d_benchmark["id"],
        "d_load_rule": d["load_assembly_contract"]["rule"],
        "d_continuation_formulation": d["continuation_policy"]["formulation"],
        "d_orientation_policy": d["continuation_policy"]["orientation_policy"],
        "d_retry_policy": d["continuation_policy"]["retry_policy"],
        "d_termination_policy": d["continuation_policy"]["termination"],
        "d_linear_backend": d["linear_solver_policy"]["corrector_backend"],
        "d_mesh_levels": tuple(level["level"] for level in d["mesh_series"]),
        "d_contract_digest": _file_digest(CONTROLLED_PATHS["d"]),
        "d_case_definition_digest": _canonical_digest(d_benchmark),
        "e_benchmark_id": e_benchmark["id"],
        "e_route": f'{e_benchmark["route"]} / {e_benchmark["method"]}',
        "e_imperfection_formula": e_benchmark["imperfection"]["formula"],
        "e_alpha_over_l": e_benchmark["imperfection"]["primary_alpha_over_L"],
        "e_contract_digest": _file_digest(CONTROLLED_PATHS["e"]),
        "e_case_definition_digest": _canonical_digest(e_benchmark),
        "e_excluded_claims": tuple(e_benchmark["excluded_claims"]),
        "e_required_policy_fields": tuple(e["execution_policy"]["required_binding"]),
    }


def assert_preparation_only() -> None:
    """Fail closed if this preparation helper is asked to execute a solve."""
    guard = load_contract()["execution_guard"]
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
    return _vector_norm([a + b for a, b in zip(left, right)]) / max(
        _vector_norm(left), _vector_norm(right), scale, floor
    )


def _equilibrium_pass(raw: Mapping[str, Any], contract: Mapping[str, Any]) -> bool | None:
    try:
        equilibrium = raw["equilibrium"]
        force_error = _equilibrium_error(
            equilibrium["support_reaction"],
            equilibrium["external_force"],
            float(equilibrium["force_scale"]),
            1.0e-14,
        )
        moment_error = _equilibrium_error(
            equilibrium["reaction_moment"],
            equilibrium["external_moment"],
            float(equilibrium["moment_scale"]),
            1.0e-14,
        )
    except (KeyError, TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(force_error) or not math.isfinite(moment_error):
        return None
    return force_error <= float(contract["thresholds"]["equilibrium_force"]) and moment_error <= float(
        contract["thresholds"]["equilibrium_moment"]
    )


def _refinement_pass(raw: Mapping[str, Any], limits: Mapping[str, float]) -> bool | None:
    """Derive D-only M2-to-M3 deltas from raw observations."""
    try:
        refinement = raw["refinement"]
        for name, threshold in limits.items():
            item = refinement[name]
            scale_floor = float(item["scale_floor"])
            delta = abs(float(item["m3"]) - float(item["m2"])) / max(
                abs(float(item["m2"])), abs(float(item["m3"])), scale_floor
            )
            if not math.isfinite(delta) or delta > float(threshold):
                return False
    except (KeyError, TypeError, ValueError, OverflowError):
        return None
    return True


def _reference_pass(raw: Mapping[str, Any], limits: Mapping[str, float]) -> bool | None:
    """Derive reference errors from one track's raw QF/reference values."""
    try:
        for name, threshold in limits.items():
            item = raw["observations"][name]
            observed = float(item["qf"])
            reference = float(item["reference"])
            scale_floor = float(item["scale_floor"])
            error = abs(observed - reference) / max(abs(observed), abs(reference), scale_floor)
            if not math.isfinite(error) or error > float(threshold):
                return False
    except (KeyError, TypeError, ValueError, OverflowError):
        return None
    return True


def _required_status(raw: Mapping[str, Any], required: tuple[str, ...]) -> str | None:
    if any(key not in raw or raw[key] is None for key in required):
        return "WP06_INCOMPLETE_EVIDENCE"
    if not _finite(raw):
        return "WP06_INCOMPLETE_EVIDENCE"
    return None


def _track_for_artifact(artifact_id: str) -> str | None:
    for track, ids in TRACK_ARTIFACTS.items():
        if artifact_id in ids:
            return track
    return None


def _provenance_status(payload: Mapping[str, Any], contract: Mapping[str, Any], anchors: Mapping[str, Any]) -> str | None:
    artifacts = payload.get("artifacts", {})
    required = contract["required_artifact_manifest"]
    for item in required:
        record = artifacts.get(item["id"])
        if not isinstance(record, Mapping) or not record.get("present", False):
            return "WP06_INCOMPLETE_EVIDENCE"
    binding = payload.get("phase1_binding")
    if not isinstance(binding, Mapping):
        return "WP06_INCOMPLETE_EVIDENCE"
    if binding.get("repository") != contract["source_repository"]:
        return "WP06_INVALID_EVIDENCE"
    if any(not binding.get(key) for key in SHARED_PHASE1_PROVENANCE[1:]):
        return "WP06_INCOMPLETE_EVIDENCE"
    policy_identity = binding.get("governing_policy_identity")
    if not isinstance(policy_identity, Mapping):
        return "WP06_INCOMPLETE_EVIDENCE"
    required_policy_fields = tuple(contract["provenance_binding"]["governing_policy_required_fields"])
    if set(required_policy_fields) != set(POLICY_IDENTITY_FIELDS):
        return "WP06_INVALID_EVIDENCE"
    for field in required_policy_fields:
        if field not in policy_identity or policy_identity[field] is None or policy_identity[field] == "":
            return "WP06_INCOMPLETE_EVIDENCE"
    expected_policy = {
        "formulation_label": anchors["formulation_label"],
        "residual_form": anchors["residual_form"],
        "orientation_policy": anchors["d_orientation_policy"],
        "load_step_retry_policy": anchors["d_retry_policy"],
        "linear_backend": anchors["d_linear_backend"],
        "arc_length_termination_policy": anchors["d_termination_policy"],
        "policy_digest": binding["solver_policy_digest"],
    }
    if policy_identity.get("governing_policy_sha") != binding.get("source_sha"):
        return "WP06_INVALID_EVIDENCE"
    if any(policy_identity.get(key) != value for key, value in expected_policy.items()):
        return "WP06_INVALID_EVIDENCE"
    phase1_values: dict[str, tuple[Any, ...]] = {field: () for field in SHARED_PHASE1_PROVENANCE}
    track_case_digests: dict[str, set[str]] = {"d": set(), "e": set()}
    track_contract_digests: dict[str, set[str]] = {"d": set(), "e": set()}
    track_mesh_digests: dict[str, set[str]] = {"d": set(), "e": set()}
    for item in required:
        artifact_id = item["id"]
        record = artifacts[artifact_id]
        provenance = record.get("provenance")
        if not isinstance(provenance, Mapping) or any(not provenance.get(key) for key in REQUIRED_PROVENANCE):
            return "WP06_INCOMPLETE_EVIDENCE"
        if provenance.get("repository") != contract["source_repository"]:
            return "WP06_INVALID_EVIDENCE"
        track = _track_for_artifact(artifact_id)
        if track is not None:
            for field in SHARED_PHASE1_PROVENANCE:
                phase1_values[field] = (*phase1_values[field], provenance.get(field))
            expected_contract_digest = anchors[f"{track}_contract_digest"]
            expected_case_digest = anchors[f"{track}_case_definition_digest"]
            if provenance.get("contract_digest") != expected_contract_digest:
                return "WP06_INVALID_EVIDENCE"
            if provenance.get("case_definition_digest") != expected_case_digest:
                return "WP06_INVALID_EVIDENCE"
            if provenance.get("element_formulation_identity") != anchors["element_formulation"]:
                return "WP06_INVALID_EVIDENCE"
            raw = record.get("raw")
            if track == "d":
                if not isinstance(raw, Mapping) or "mesh_digests" not in raw:
                    return "WP06_INCOMPLETE_EVIDENCE"
                mesh_digests = raw["mesh_digests"]
                if not isinstance(mesh_digests, Mapping) or set(mesh_digests) != set(anchors["d_mesh_levels"]):
                    return "WP06_INVALID_EVIDENCE"
                if any(not _is_sha256(value) for value in mesh_digests.values()):
                    return "WP06_INVALID_EVIDENCE"
                track_mesh_digests[track].add(_canonical_digest(mesh_digests))
            track_case_digests[track].add(str(provenance["case_definition_digest"]))
            track_contract_digests[track].add(str(provenance["contract_digest"]))
            if artifact_id in {"WP06-D-REFERENCE", "WP06-E-REFERENCE"} and not provenance.get("reference_implementation_digest"):
                return "WP06_INCOMPLETE_EVIDENCE"
    for field, values in phase1_values.items():
        if values and not all(value == values[0] for value in values):
            return "WP06_INVALID_EVIDENCE"
        if values and values[0] != binding.get(field):
            return "WP06_INVALID_EVIDENCE"
    if any(len(values) != 1 for values in track_case_digests.values()) or any(
        len(values) != 1 for values in track_contract_digests.values()
    ):
        return "WP06_INVALID_EVIDENCE"
    if len(track_mesh_digests["d"]) != 1:
        return "WP06_INVALID_EVIDENCE"
    return None


def _replay_pass(record: Mapping[str, Any]) -> bool | None:
    raw = record.get("raw")
    if not isinstance(raw, Mapping):
        return None
    if not _finite(raw):
        return None
    first, second = raw.get("run_a"), raw.get("run_b")
    if not isinstance(first, Mapping) or not isinstance(second, Mapping):
        return None
    if any(field not in first or field not in second for field in REPLAY_FIELDS):
        return None
    return _close(first, second)


def _identity_status(d_raw: Mapping[str, Any], e_raw: Mapping[str, Any], anchors: Mapping[str, Any]) -> str | None:
    if d_raw.get("benchmark_id") != anchors["d_benchmark_id"]:
        return "WP06_INVALID_EVIDENCE"
    if d_raw.get("element_formulation") != anchors["element_formulation"]:
        return "WP06_INVALID_EVIDENCE"
    if d_raw.get("formulation_label") != anchors["formulation_label"]:
        return "WP06_INVALID_EVIDENCE"
    if d_raw.get("residual_form") != anchors["residual_form"] or d_raw.get("constraint_form") != anchors["constraint_form"]:
        return "WP06_INVALID_EVIDENCE"
    if d_raw.get("orientation_policy") != anchors["d_orientation_policy"]:
        return "WP06_INVALID_EVIDENCE"
    if d_raw.get("load_rule") != anchors["d_load_rule"]:
        return "WP06_INVALID_EVIDENCE"
    if d_raw.get("state_owner") != anchors["state_owner"]:
        return "WP06_INVALID_EVIDENCE"
    if d_raw.get("state_schema_digest") != anchors["state_schema_digest"]:
        return "WP06_INVALID_EVIDENCE"
    if d_raw.get("rollback_contract_digest") != anchors["rollback_contract_digest"]:
        return "WP06_INVALID_EVIDENCE"
    mesh_digests = d_raw.get("mesh_digests")
    if not isinstance(mesh_digests, Mapping) or set(mesh_digests) != set(anchors["d_mesh_levels"]):
        return "WP06_INCOMPLETE_EVIDENCE"
    if d_raw.get("case_definition_digest") != anchors["d_case_definition_digest"]:
        return "WP06_INVALID_EVIDENCE"
    if d_raw.get("continuation_formulation") != anchors["d_continuation_formulation"]:
        return "WP06_INVALID_EVIDENCE"
    if d_raw.get("retry_policy") != anchors["d_retry_policy"]:
        return "WP06_INVALID_EVIDENCE"
    if d_raw.get("linear_backend") != anchors["d_linear_backend"]:
        return "WP06_INVALID_EVIDENCE"
    if d_raw.get("termination_policy") != anchors["d_termination_policy"]:
        return "WP06_INVALID_EVIDENCE"
    if d_raw.get("altered_physics_retry") or d_raw.get("undeclared_m4") or d_raw.get("result_dependent_threshold_change"):
        return "WP06_INVALID_EVIDENCE"
    if e_raw.get("benchmark_id") != anchors["e_benchmark_id"]:
        return "WP06_INVALID_EVIDENCE"
    if e_raw.get("route") != anchors["e_route"]:
        return "WP06_INVALID_EVIDENCE"
    if e_raw.get("element_formulation") != anchors["element_formulation"]:
        return "WP06_INVALID_EVIDENCE"
    if e_raw.get("formulation_label") != anchors["formulation_label"]:
        return "WP06_INVALID_EVIDENCE"
    if e_raw.get("residual_form") != anchors["residual_form"] or e_raw.get("constraint_form") != anchors["constraint_form"]:
        return "WP06_INVALID_EVIDENCE"
    if e_raw.get("orientation_policy") != anchors["d_orientation_policy"]:
        return "WP06_INVALID_EVIDENCE"
    if e_raw.get("state_owner") != anchors["state_owner"]:
        return "WP06_INVALID_EVIDENCE"
    if e_raw.get("state_schema_digest") != anchors["state_schema_digest"]:
        return "WP06_INVALID_EVIDENCE"
    if e_raw.get("rollback_contract_digest") != anchors["rollback_contract_digest"]:
        return "WP06_INVALID_EVIDENCE"
    if e_raw.get("linear_backend") != anchors["d_linear_backend"]:
        return "WP06_INVALID_EVIDENCE"
    if e_raw.get("termination_policy") != anchors["d_termination_policy"]:
        return "WP06_INVALID_EVIDENCE"
    if e_raw.get("imperfection_formula") != anchors["e_imperfection_formula"]:
        return "WP06_INVALID_EVIDENCE"
    if e_raw.get("alpha_over_l") != anchors["e_alpha_over_l"]:
        return "WP06_INVALID_EVIDENCE"
    if e_raw.get("mode_based_substitution") or e_raw.get("branch_switch_claim") or e_raw.get("bifurcation_detection_claim"):
        return "WP06_INVALID_EVIDENCE"
    if e_raw.get("case_definition_digest") != anchors["e_case_definition_digest"]:
        return "WP06_INVALID_EVIDENCE"
    if tuple(e_raw.get("claim_exclusions", ())) != anchors["e_excluded_claims"]:
        return "WP06_INVALID_EVIDENCE"
    return None


def _report_status_check(payload: Mapping[str, Any], d_raw: Mapping[str, Any], e_raw: Mapping[str, Any], derived: str) -> dict[str, Any] | None:
    reported = [payload.get("reported_status"), d_raw.get("reported_status"), e_raw.get("reported_status")]
    reported = [value for value in reported if value is not None]
    if reported and any(value != "PASS" for value in reported):
        return {"status": "WP06_STATUS_MISMATCH", "derived_status": derived, "reason": "reported status disagrees with raw-derived status"}
    if derived != "WP06_PASS_BOUNDED" and any(value == "PASS" for value in reported):
        return {"status": "WP06_STATUS_MISMATCH", "derived_status": derived, "reason": "reported PASS contradicts raw evidence"}
    return None


def evaluate_closure(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Derive a fail-closed WP06 status from raw D/E observations.

    Replay and reference decisions come from the dedicated D/E artifacts in
    the manifest. This helper never executes structural or reference work.
    """
    contract = load_contract()
    assert_preparation_only()
    try:
        anchors = controlled_anchors()
    except (KeyError, OSError, ValueError, json.JSONDecodeError):
        return {"status": "WP06_INVALID_EVIDENCE", "reason": "controlled A-E contract identity is invalid"}
    provenance_status = _provenance_status(payload, contract, anchors)
    if provenance_status:
        return {"status": provenance_status, "reason": "artifact/provenance validation"}
    if payload.get("production_mechanics_changed", False):
        return {"status": "WP06_INVALID_EVIDENCE", "reason": "production mechanics changed"}
    artifacts = payload["artifacts"]
    for record in artifacts.values():
        if isinstance(record, Mapping) and "raw" in record and record["raw"] is not None and not _finite(record["raw"]):
            return {"status": "WP06_INCOMPLETE_EVIDENCE", "reason": "nonfinite authoritative raw evidence"}
    d_raw = artifacts["WP06-D-RAW"].get("raw")
    e_raw = artifacts["WP06-E-RAW"].get("raw")
    if not isinstance(d_raw, Mapping) or not isinstance(e_raw, Mapping):
        return {"status": "WP06_INCOMPLETE_EVIDENCE", "reason": "raw D/E evidence missing"}
    d_required = (
        "benchmark_id", "element_formulation", "formulation_label", "residual_form", "constraint_form",
        "orientation_policy", "load_rule", "mesh_digests", "case_definition_digest", "state_owner",
        "state_schema_digest", "rollback_contract_digest", "continuation_formulation", "retry_policy",
        "linear_backend", "termination_policy", "refinement", "limit_point_observed",
        "path_continues_beyond_limit", "equilibrium", "envelope_pass", "required_observables_complete",
        "altered_physics_retry", "undeclared_m4", "result_dependent_threshold_change",
    )
    e_required = (
        "benchmark_id", "route", "element_formulation", "formulation_label", "residual_form", "constraint_form",
        "orientation_policy", "imperfection_formula", "alpha_over_l", "mode_based_substitution",
        "state_owner", "state_schema_digest", "rollback_contract_digest", "linear_backend", "termination_policy",
        "branch_switch_claim", "bifurcation_detection_claim", "case_definition_digest", "equilibrium",
        "envelope_pass", "required_observables_complete",
    )
    for raw, required in ((d_raw, d_required), (e_raw, e_required)):
        missing_status = _required_status(raw, required)
        if missing_status:
            return {"status": missing_status, "reason": "required raw observation missing or nonfinite"}
    identity_status = _identity_status(d_raw, e_raw, anchors)
    if identity_status:
        return {"status": identity_status, "reason": "controlled A-E identity mismatch"}

    def decision(status: str, reason: str) -> dict[str, Any]:
        return _report_status_check(payload, d_raw, e_raw, status) or {"status": status, "reason": reason}

    if not d_raw["limit_point_observed"] or not d_raw["path_continues_beyond_limit"]:
        return decision("WP06_HOLD_STRUCTURAL", "limit-point/path gate failed")
    d_refinement = _refinement_pass(d_raw, contract["thresholds"]["d_refinement"])
    if d_refinement is None:
        return decision("WP06_INCOMPLETE_EVIDENCE", "D refinement raw fields missing or invalid")
    if not d_refinement:
        return decision("WP06_HOLD_STRUCTURAL", "derived D refinement threshold failure")
    for raw in (d_raw, e_raw):
        equilibrium_pass = _equilibrium_pass(raw, contract)
        if equilibrium_pass is None:
            return decision("WP06_INCOMPLETE_EVIDENCE", "equilibrium vector observations missing or invalid")
        if not equilibrium_pass:
            return decision("WP06_FAIL_EQUILIBRIUM", "derived vector equilibrium failure")
        if not raw["envelope_pass"] or not raw["required_observables_complete"]:
            return decision("WP06_HOLD_STRUCTURAL", "envelope or required-observable gate failure")
    d_replay = _replay_pass(artifacts["WP06-D-REPLAY"])
    e_replay = _replay_pass(artifacts["WP06-E-REPLAY"])
    if d_replay is None or e_replay is None:
        return decision("WP06_INCOMPLETE_EVIDENCE", "dedicated D/E replay raw fields missing")
    if not d_replay or not e_replay:
        return decision("WP06_HOLD_REPLAY", "derived D/E replay mismatch")
    d_reference = artifacts["WP06-D-REFERENCE"].get("raw")
    e_reference = artifacts["WP06-E-REFERENCE"].get("raw")
    if not isinstance(d_reference, Mapping) or not isinstance(e_reference, Mapping):
        return decision("WP06_HOLD_REFERENCE", "dedicated D/E reference raw fields missing")
    reference_required = (
        "benchmark_id",
        "formulation_match",
        "independent_implementation",
        "element_formulation",
        "formulation_label",
        "observations",
    )
    forbidden = contract["reference_requirements"]["forbidden_production_flags"]
    for reference, expected_id in ((d_reference, anchors["d_benchmark_id"]), (e_reference, anchors["e_benchmark_id"])):
        if any(key not in reference for key in reference_required):
            return decision("WP06_HOLD_REFERENCE", "reference raw field missing")
        if (
            reference["benchmark_id"] != expected_id
            or reference["element_formulation"] != anchors["element_formulation"]
            or reference["formulation_label"] != anchors["formulation_label"]
            or not reference["formulation_match"]
            or not reference["independent_implementation"]
        ):
            return decision("WP06_HOLD_REFERENCE", "reference identity mismatch")
        if any(reference.get(flag, True) for flag in forbidden):
            return decision("WP06_HOLD_REFERENCE", "reference called a prohibited production helper")
    d_reference_pass = _reference_pass(d_reference, contract["thresholds"]["d_reference"])
    if d_reference_pass is None:
        return decision("WP06_HOLD_REFERENCE", "D reference observations missing or invalid")
    if not d_reference_pass:
        return decision("WP06_HOLD_REFERENCE", "derived D reference threshold failure")
    e_reference_pass = _reference_pass(e_reference, contract["thresholds"]["e_reference"])
    if e_reference_pass is None:
        return decision("WP06_HOLD_REFERENCE", "E reference observations missing or invalid")
    if not e_reference_pass:
        return decision("WP06_HOLD_REFERENCE", "derived E reference threshold failure")
    reported_check = _report_status_check(payload, d_raw, e_raw, "WP06_PASS_BOUNDED")
    if reported_check:
        return reported_check
    return {"status": "WP06_PASS_BOUNDED", "reason": "all derived D/E closure gates pass"}


if __name__ == "__main__":
    assert_preparation_only()
    print("WP06-F preparation guard: no structural execution")
