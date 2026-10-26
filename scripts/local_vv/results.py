"""Pure classification of the strict WP12 V2 R1 structured result."""

from __future__ import annotations

from typing import Any

from .manifest import V2_NODEID, V2_RESULT_SCHEMA

SCIENTIFIC_STATUSES = {"PASS", "FAIL", "INCONCLUSIVE", "ERROR"}
ASSERTION_STATUSES = {"PASS", "FAIL", "NOT_REACHED"}
V2_MANDATORY_ASSERTIONS = (
    "all_finite",
    "exact_reference_symmetric",
    "scalar_global_accuracy",
    "batch_global_accuracy",
    "matrix_free_relative_accuracy",
    "direct_relative_accuracy",
    "matrix_free_per_column_accuracy",
    "matrix_free_vs_direct_accuracy",
    "matrix_free_archived_residual",
    "direct_archived_residual",
    "archived_energy_identity",
    "synthetic_negative_controls",
)
V2_GAMMA_ASSERTIONS = (
    "no_subnormal_values_for_gamma_profile",
    "scalar_and_batch_accumulation_bounds",
    "scalar_and_batch_componentwise_symmetry_bounds",
    "matrix_free_componentwise_error_bound",
)


def classify_v2_result(
    marker_status: str,
    payload: dict[str, Any] | None,
    *,
    case_id: str,
    pytest_execution_status: str,
    nodeid: str = V2_NODEID,
) -> dict[str, Any]:
    """Validate scientific/pytest status separation and derive fail-closed result.

    The return value is receipt-ready. A missing marker is INCOMPLETE, malformed
    or contradictory evidence is ERROR, and neither can become scientific PASS.
    """

    def invalid(reason: str) -> dict[str, Any]:
        return _error(reason, pytest_execution_status)

    if marker_status == "NOT_EXPOSED":
        return _incomplete("required structured scientific result marker is missing", pytest_execution_status)
    if marker_status != "EXPOSED_JSON" or not isinstance(payload, dict):
        return invalid("structured scientific result marker is malformed")
    if (
        payload.get("schema") != V2_RESULT_SCHEMA
        or payload.get("case_id") != case_id
        or payload.get("nodeid") != nodeid
        or nodeid != V2_NODEID
    ):
        return invalid("structured scientific result schema, case_id, or nodeid mismatch")

    required_booleans = ("rounding_assumptions_verified", "gamma_bound_evaluated")
    if any(type(payload.get(name)) is not bool for name in required_booleans):
        return invalid("rounding and gamma evaluation fields must be booleans")
    if "gamma_bound_satisfied" not in payload:
        return invalid("gamma_bound_satisfied field is required")
    satisfied = payload["gamma_bound_satisfied"]
    if satisfied is not None and type(satisfied) is not bool:
        return invalid("gamma_bound_satisfied must be boolean or null")
    gamma_status = payload.get("gamma_scientific_status")
    observed_pytest = payload.get("pytest_execution_status")
    overall_status = payload.get("overall_scientific_status")
    if (
        not isinstance(gamma_status, str)
        or gamma_status not in SCIENTIFIC_STATUSES
        or not isinstance(overall_status, str)
        or overall_status not in SCIENTIFIC_STATUSES
    ):
        return invalid("scientific status field has an unsupported value")
    if (
        not isinstance(observed_pytest, str)
        or observed_pytest not in ("PASS", "FAIL")
        or observed_pytest != pytest_execution_status
    ):
        return invalid("payload pytest_execution_status contradicts observed JUnit execution")

    rounding_verified = payload["rounding_assumptions_verified"]
    gamma_evaluated = payload["gamma_bound_evaluated"]
    if gamma_evaluated and type(satisfied) is not bool:
        return invalid("evaluated gamma bound must expose a boolean gamma_bound_satisfied")
    if not gamma_evaluated and satisfied is not None:
        return invalid("unevaluated gamma bound must expose null gamma_bound_satisfied")
    if not rounding_verified:
        if gamma_status != "INCONCLUSIVE":
            return invalid("unverified gamma assumptions must yield INCONCLUSIVE")
    elif not gamma_evaluated:
        if gamma_status != "INCONCLUSIVE":
            return invalid("unevaluated gamma bound must yield INCONCLUSIVE")
    elif gamma_status != ("PASS" if satisfied else "FAIL"):
        return invalid("gamma status contradicts the evaluated bound")

    records = payload.get("assertion_records")
    if not isinstance(records, list) or not records:
        return invalid("assertion_records must be a non-empty list")
    names: set[str] = set()
    ordered_names: list[str] = []
    mandatory: list[str] = []
    gamma_records: list[str] = []
    for record in records:
        if not isinstance(record, dict):
            return invalid("assertion record must be an object")
        name, status, role = record.get("name"), record.get("status"), record.get("acceptance_role")
        if not isinstance(name, str) or not name or name in names:
            return invalid("assertion names must be non-empty and unique")
        if (
            not isinstance(status, str)
            or status not in ASSERTION_STATUSES
            or not isinstance(role, str)
            or role not in ("mandatory", "gamma_conditional")
        ):
            return invalid("assertion record has an unsupported status or acceptance role")
        names.add(name)
        ordered_names.append(name)
        (mandatory if role == "mandatory" else gamma_records).append(status)

    if tuple(ordered_names) != V2_MANDATORY_ASSERTIONS + V2_GAMMA_ASSERTIONS:
        return invalid("assertion records do not match the complete ordered V2 acceptance contract")
    if any(record.get("acceptance_role") != "mandatory" for record in records[: len(V2_MANDATORY_ASSERTIONS)]) or any(
        record.get("acceptance_role") != "gamma_conditional" for record in records[len(V2_MANDATORY_ASSERTIONS) :]
    ):
        return invalid("assertion record roles contradict the V2 acceptance contract")
    prior_failure = False
    prior_not_reached = False
    for record in records:
        status = record["status"]
        if prior_failure and status != "NOT_REACHED":
            return invalid("assertions after the first failure must be NOT_REACHED")
        if prior_not_reached and status != "NOT_REACHED":
            return invalid("assertion records after NOT_REACHED must remain NOT_REACHED")
        if status == "NOT_REACHED":
            prior_not_reached = True
        if status == "FAIL":
            prior_failure = True
    if not gamma_evaluated or not rounding_verified:
        gamma_details = records[len(V2_MANDATORY_ASSERTIONS) :]
        if any(
            record.get("status") != "NOT_REACHED"
            or not isinstance(record.get("reason"), str)
            or not record["reason"].strip()
            for record in gamma_details
        ):
            return invalid("gamma-conditional assertions must be NOT_REACHED when gamma is inconclusive")
    else:
        mandatory_failed = "FAIL" in mandatory
        if (
            not mandatory_failed
            and "FAIL" not in gamma_records
            and any(status == "NOT_REACHED" for status in gamma_records)
        ):
            return invalid("evaluated gamma requires conditional assertions to be reached after mandatory checks")
        if not mandatory_failed and satisfied != all(status == "PASS" for status in gamma_records):
            return invalid("gamma_bound_satisfied contradicts gamma-conditional assertion records")
        if mandatory_failed and any(status != "NOT_REACHED" for status in gamma_records):
            return invalid("gamma-conditional assertions after a mandatory failure must be NOT_REACHED")

    expected_pytest = (
        "PASS"
        if all(status == "PASS" for status in mandatory)
        and (not rounding_verified or all(status == "PASS" for status in gamma_records))
        else "FAIL"
    )
    if observed_pytest != expected_pytest:
        return invalid("pytest_execution_status contradicts reached acceptance assertion records")

    if "FAIL" in mandatory or "FAIL" in gamma_records:
        derived_overall = "FAIL"
    elif "NOT_REACHED" in mandatory:
        derived_overall = "INCONCLUSIVE"
    elif gamma_status == "INCONCLUSIVE":
        derived_overall = "INCONCLUSIVE"
    elif gamma_status == "ERROR":
        derived_overall = "ERROR"
    else:
        derived_overall = gamma_status
    if overall_status != derived_overall:
        return invalid("overall scientific status contradicts completed assertion records")
    return {
        "status": overall_status,
        "gamma_scientific_status": gamma_status,
        "pytest_execution_status": observed_pytest,
        "rounding_assumptions_verified": rounding_verified,
        "gamma_bound_evaluated": gamma_evaluated,
        "gamma_bound_satisfied": satisfied,
        "assertion_records": records,
        "error": None,
    }


def _incomplete(reason: str, pytest_execution_status: str) -> dict[str, Any]:
    return {
        "status": "INCOMPLETE",
        "gamma_scientific_status": "INCONCLUSIVE",
        "pytest_execution_status": pytest_execution_status,
        "rounding_assumptions_verified": None,
        "gamma_bound_evaluated": None,
        "gamma_bound_satisfied": None,
        "assertion_records": [],
        "error": reason,
    }


def _error(reason: str, pytest_execution_status: str) -> dict[str, Any]:
    return {
        "status": "ERROR",
        "gamma_scientific_status": "ERROR",
        "pytest_execution_status": pytest_execution_status,
        "rounding_assumptions_verified": None,
        "gamma_bound_evaluated": None,
        "gamma_bound_satisfied": None,
        "assertion_records": [],
        "error": reason,
    }
