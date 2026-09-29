from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from scripts.docs_publication import read_document_metadata
from scripts.validate_wp14_contract import CONTRACT_PATH, load_contract, validate_contract


def test_wp14_contract_is_valid_and_reaches_true_one_million_dof() -> None:
    contract = load_contract()
    assert validate_contract(contract) == []
    assert contract["reference_model"]["mesh"]["true_dof"] == 1_029_000
    assert contract["reference_model"]["mesh"]["element_count"] == 1_971_054


def test_wp14_contract_is_deterministic_json_and_has_no_implicit_fallback() -> None:
    first = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    second = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert first == second
    assert first["solver_contract"]["backend_selection"] == "explicit_only"
    assert first["solver_contract"]["fallback_policy"].startswith("none")
    assert first["solver_contract"]["random_seed"] == 0
    assert "timestamp_utc" in first["evidence_schema"]["required_fields"]
    assert first["acceptance_metrics"]["post_result_retuning"] is False


def test_wp14_validator_cli_passes() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/validate_wp14_contract.py"],
        cwd=Path(__file__).resolve().parents[2],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_wp14_g06_r22_policy_is_prospective_and_binds_its_evidence() -> None:
    root = Path(__file__).resolve().parents[2]
    policy_path = root / "qualification/0_2_9/wp14/wp14_g06_review_scope_r2_2_policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))

    assert policy["status"] == "OWNER_CONFIRMED_POLICY_AND_IDENTITY_PENDING_EXECUTION_FREEZE"
    assert policy["provenance"]["owner_policy_confirmation"]["signature_claimed"] is False
    assert policy["policy"]["owner_review_metadata_scope"]["exact_statuses"] == ["approved"]
    assert policy["policy"]["owner_review_metadata_scope"]["status_prefixes"] == [
        "accepted_for_release_",
        "owner_approved",
        "owner_accepted",
    ]
    assert policy["execution"]["commands_run"] is False
    assert policy["governance"]["wp14_closure"] is False
    assert policy["governance"]["official_points_awarded"] is False

    parent = root / policy["provenance"]["parent_contract"]["path"]
    assert hashlib.sha256(parent.read_bytes()).hexdigest() == policy["provenance"]["parent_contract"]["sha256"]
    for correction in policy["evidence_based_metadata_reconciliation"]:
        source = root / correction["direct_source"]["path"]
        assert hashlib.sha256(source.read_bytes()).hexdigest() == correction["direct_source"]["sha256"]

    incomplete = policy["preflight_observation_before_wp09_self_attestation"]["owner_review_metadata_incomplete"]
    assert [item["document_id"] for item in incomplete] == ["DOC-029-WP09-OWNER-R3"]

    attestation = policy["wp09_identity_self_attestation"]
    attestation_path = root / attestation["attestation_path"]
    assert hashlib.sha256(attestation_path.read_bytes()).hexdigest() == attestation["attestation_sha256"]
    assert attestation["decision_maker_role"] == "Owner"
    assert attestation["personal_name_supplied"] is False
    decision_path = root / attestation["decision_record_path"]
    assert hashlib.sha256(decision_path.read_bytes()).hexdigest() == attestation["decision_record_sha256"]
    assert policy["post_attestation_preflight_observation"]["owner_review_metadata_complete"] == 22
    assert policy["post_attestation_preflight_observation"]["owner_review_metadata_incomplete"] == []

    metadata = read_document_metadata(root / "docs/verification/0_2_9/wp09-owner-acceptance-r3.md")
    assert metadata["reviewer"] == "Owner"
    assert metadata["approver"] == "Owner"
    assert str(metadata["review_date"]) == "2026-09-20"
