"""Pure validation for the Owner-frozen HEX8-SRI first-six criteria contract."""

from __future__ import annotations

from typing import Any, Mapping


CRITERIA_CONTRACT_SCHEMA = "qfsolver-hex8sri-criteria-contract-v1"
CRITERIA_FREEZE_SCHEMA = "qfsolver-hex8sri-criteria-freeze-v1"
CRITERIA_CONTRACT_REVISION = "first6-4x2x2-owner-criteria-2026-10-27-r1"
FIRST6_NODEIDS = (
    "tests/verification/test_hex8_sri_convergence.py::test_convergence_case[hex8_standard-nu_0p3-4x2x2]",
    "tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_historical-nu_0p3-4x2x2]",
    "tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_corrected-nu_0p3-4x2x2]",
    "tests/verification/test_hex8_sri_convergence.py::test_convergence_case[hex8_standard-nu_0p4999-4x2x2]",
    "tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_historical-nu_0p4999-4x2x2]",
    "tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_corrected-nu_0p4999-4x2x2]",
)
PROPOSED_CRITERIA = {
    "energy_identity_relative_max": 1e-8,
    "finest_level_independent_3d_energy_relative_error_max": 0.05,
    "finest_level_independent_3d_mean_UZ_relative_error_max": 0.05,
    "force_closure_relative_max": 1e-6,
    "free_residual_relative_max": 1e-7,
    "last_two_levels_energy_relative_change_max": 0.02,
    "last_two_levels_mean_UZ_relative_change_max": 0.02,
    "moment_closure_relative_max": 1e-6,
}
CASE_GATE_THRESHOLD_KEYS = (
    "free_residual_relative_max",
    "energy_identity_relative_max",
    "force_closure_relative_max",
    "moment_closure_relative_max",
)
FROZEN_CASE_GATE_CRITERIA = {key: PROPOSED_CRITERIA[key] for key in CASE_GATE_THRESHOLD_KEYS}
FROZEN_DISPOSITIONS = {
    "finite_state": {"classification": "CASE_GATE", "status": "OWNER_FROZEN"},
    "positive_sampled_jacobians_center_and_gauss": {"classification": "CASE_GATE", "status": "OWNER_FROZEN"},
    "free_residual_relative_max": {"classification": "CASE_GATE", "status": "OWNER_FROZEN"},
    "energy_identity_relative_max": {"classification": "CASE_GATE", "status": "OWNER_FROZEN"},
    "force_closure_relative_max": {"classification": "CASE_GATE", "status": "OWNER_FROZEN"},
    "moment_closure_relative_max": {"classification": "CASE_GATE", "status": "OWNER_FROZEN"},
    "negative_mean_loaded_face_uz": {"classification": "CASE_GATE", "status": "OWNER_FROZEN"},
    "stiffness_symmetry_relative_frobenius": {
        "classification": "CASE_DIAGNOSTIC",
        "status": "DESCRIPTIVE_ONLY",
    },
    "affine_jacobian_reproduction": {"classification": "CASE_DIAGNOSTIC", "status": "DESCRIPTIVE_ONLY"},
    "positive_internal_energy": {"classification": "CASE_DIAGNOSTIC", "status": "DESCRIPTIVE_ONLY"},
    "formulation_comparison": {"classification": "CASE_DIAGNOSTIC", "status": "DESCRIPTIVE_ONLY"},
    "condition_number_1_estimate_Kff": {"classification": "CASE_DIAGNOSTIC", "status": "DESCRIPTIVE_ONLY"},
    "timing_seconds": {"classification": "CASE_DIAGNOSTIC", "status": "DESCRIPTIVE_ONLY"},
    "rss_peak_bytes": {"classification": "CASE_DIAGNOSTIC", "status": "DESCRIPTIVE_ONLY"},
    "timoshenko_relative_difference": {"classification": "CASE_DIAGNOSTIC", "status": "DESCRIPTIVE_ONLY"},
    "last_two_levels_energy_relative_change_max": {
        "classification": "CAMPAIGN_GATE_DEFERRED",
        "status": "NOT_ASSESSED",
    },
    "last_two_levels_mean_UZ_relative_change_max": {
        "classification": "CAMPAIGN_GATE_DEFERRED",
        "status": "NOT_ASSESSED",
    },
    "finest_level_independent_3d_energy_relative_error_max": {
        "classification": "CAMPAIGN_GATE_DEFERRED",
        "status": "NOT_ASSESSED",
    },
    "finest_level_independent_3d_mean_UZ_relative_error_max": {
        "classification": "CAMPAIGN_GATE_DEFERRED",
        "status": "NOT_ASSESSED",
    },
    "single_case_convergence": {"classification": "CAMPAIGN_GATE_DEFERRED", "status": "NOT_ASSESSED"},
    "independent_3d_reference_error": {
        "classification": "CAMPAIGN_GATE_DEFERRED",
        "status": "NOT_ASSESSED",
    },
}
PROPOSED_DISPOSITIONS = {
    key: {
        "classification": value["classification"],
        "status": "OWNER_FREEZE_REQUIRED" if value["classification"] == "CASE_GATE" else value["status"],
    }
    for key, value in FROZEN_DISPOSITIONS.items()
}


def validate_frozen_case_criteria(
    case_manifest: Mapping[str, Any],
    owner_decision: Mapping[str, Any],
    *,
    target: str,
    case_registration_sha256: str,
) -> dict[str, float]:
    """Return only case-level numeric gates after the decision binds every first-six manifest."""
    criteria_contract = {
        "schema": CRITERIA_CONTRACT_SCHEMA,
        "revision": CRITERIA_CONTRACT_REVISION,
        "dispositions": PROPOSED_DISPOSITIONS,
    }
    criteria_freeze = owner_decision.get("criteria_freeze")
    registrations = (
        criteria_freeze.get("case_manifest_registration_sha256_by_nodeid")
        if isinstance(criteria_freeze, Mapping)
        else None
    )
    if (
        target not in FIRST6_NODEIDS
        or case_manifest.get("criteria_status") != "OWNER_FREEZE_REQUIRED"
        or case_manifest.get("criteria_contract") != criteria_contract
        or case_manifest.get("proposed_criteria") != PROPOSED_CRITERIA
        or case_manifest.get("frozen_criteria") is not None
        or not isinstance(criteria_freeze, Mapping)
        or criteria_freeze.get("schema") != CRITERIA_FREEZE_SCHEMA
        or criteria_freeze.get("revision") != CRITERIA_CONTRACT_REVISION
        or criteria_freeze.get("dispositions") != FROZEN_DISPOSITIONS
        or criteria_freeze.get("frozen_case_gate_criteria") != FROZEN_CASE_GATE_CRITERIA
        or not isinstance(registrations, Mapping)
        or set(registrations) != set(FIRST6_NODEIDS)
        or registrations.get(target) != case_registration_sha256
    ):
        raise ValueError("Owner criteria decision is absent, stale, or inconsistent with the registered proposal")
    return dict(FROZEN_CASE_GATE_CRITERIA)


def negative_mean_loaded_face_uz_verdict(value: float) -> str:
    """Check the approved sign convention for a negative-Z applied traction."""
    return "PASS" if isinstance(value, (int, float)) and value < 0.0 else "FAIL"
