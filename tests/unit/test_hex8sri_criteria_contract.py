from __future__ import annotations

from copy import deepcopy
import hashlib
from typing import Any

import pytest

from experiments.hex8_sri_equilibrium import criteria_contract as contract


def _owner_frozen_case() -> tuple[dict[str, Any], dict[str, Any], str]:
    registration_sha256 = hashlib.sha256(b"synthetic first-six case registration").hexdigest()
    case_manifest = {
        "criteria_status": "OWNER_FREEZE_REQUIRED",
        "criteria_contract": {
            "schema": contract.CRITERIA_CONTRACT_SCHEMA,
            "revision": contract.CRITERIA_CONTRACT_REVISION,
            "dispositions": contract.PROPOSED_DISPOSITIONS,
        },
        "proposed_criteria": contract.PROPOSED_CRITERIA,
        "frozen_criteria": None,
    }
    owner_decision = {
        "criteria_freeze": {
            "schema": contract.CRITERIA_FREEZE_SCHEMA,
            "revision": contract.CRITERIA_CONTRACT_REVISION,
            "dispositions": contract.FROZEN_DISPOSITIONS,
            "frozen_case_gate_criteria": contract.FROZEN_CASE_GATE_CRITERIA,
            "case_manifest_registration_sha256_by_nodeid": {
                nodeid: registration_sha256 for nodeid in contract.FIRST6_NODEIDS
            },
        }
    }
    return case_manifest, owner_decision, registration_sha256


def test_frozen_contract_returns_only_case_gate_thresholds_and_keeps_deferred_not_assessed() -> None:
    case_manifest, owner_decision, registration_sha256 = _owner_frozen_case()
    frozen = contract.validate_frozen_case_criteria(
        case_manifest,
        owner_decision,
        target=contract.FIRST6_NODEIDS[0],
        case_registration_sha256=registration_sha256,
    )

    assert frozen == contract.FROZEN_CASE_GATE_CRITERIA
    assert set(frozen) == set(contract.CASE_GATE_THRESHOLD_KEYS)
    deferred = {
        name: record
        for name, record in contract.FROZEN_DISPOSITIONS.items()
        if record["classification"] == "CAMPAIGN_GATE_DEFERRED"
    }
    assert deferred
    assert all(record["status"] == "NOT_ASSESSED" for record in deferred.values())
    assert not set(deferred).intersection(frozen)


@pytest.mark.parametrize(
    ("mean_uz_m", "expected"),
    [(-1.0e-3, "PASS"), (0.0, "FAIL"), (1.0e-3, "FAIL"), (float("nan"), "FAIL")],
)
def test_negative_z_load_sign_gate_is_pure_and_deterministic(mean_uz_m: float, expected: str) -> None:
    assert contract.negative_mean_loaded_face_uz_verdict(mean_uz_m) == expected


@pytest.mark.parametrize("mutation", ["unfrozen", "threshold", "classification", "stale_manifest", "old_revision"])
def test_frozen_contract_rejects_unfrozen_or_stale_criteria(
    mutation: str,
) -> None:
    case_manifest, owner_decision, registration_sha256 = _owner_frozen_case()
    case_manifest = deepcopy(case_manifest)
    owner_decision = deepcopy(owner_decision)
    freeze = owner_decision["criteria_freeze"]
    if mutation == "unfrozen":
        case_manifest["criteria_status"] = "PROPOSED_REQUIRES_OWNER_FREEZE"
    elif mutation == "threshold":
        freeze["frozen_case_gate_criteria"]["free_residual_relative_max"] = 1e-6
    elif mutation == "classification":
        freeze["dispositions"]["single_case_convergence"] = {
            "classification": "CASE_DIAGNOSTIC",
            "status": "DESCRIPTIVE_ONLY",
        }
    elif mutation == "stale_manifest":
        freeze["case_manifest_registration_sha256_by_nodeid"][contract.FIRST6_NODEIDS[0]] = "f" * 64
    else:
        freeze["revision"] = "obsolete-criteria-revision"

    with pytest.raises(ValueError, match="absent, stale, or inconsistent"):
        contract.validate_frozen_case_criteria(
            case_manifest,
            owner_decision,
            target=contract.FIRST6_NODEIDS[0],
            case_registration_sha256=registration_sha256,
        )
