"""Preparation-only contract for the nine remaining VV3D family cases.

This scope is separate from R2.  It references the closed R1/R2 and TET4-L3
diagnostic ledgers without reopening or changing any of them.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any


CAMPAIGN_ID = "WP12-VV3D-FAMILY-REMAINDER-20261030"
SCOPE_ID = "wp12_vv3d_family_remainder"
CONTRACT_SCHEMA = "qf-wp12-vv3d-family-remainder-contract-v1"
DECISION_SCHEMA = "qf-wp12-vv3d-family-remainder-owner-decision-v1"
NODEID_PREFIX = "tests/unit/test_wp12_vv3d_adaptive_prepared.py::test_prepared_fem_case["
CASE_IDS = tuple(
    f"VV3D-{family}-L{level}"
    for family in ("TET10", "HEX8", "HEX20")
    for level in (1, 2, 3)
)
CASE_NODEIDS = tuple(NODEID_PREFIX + case_id + "]" for case_id in CASE_IDS)
EXCLUDED_CASE_IDS = ("VV3D-TET4-L1", "VV3D-TET4-L2", "VV3D-TET4-L3")
SELECTED_DOFS = {
    "VV3D-TET10-L1": 375,
    "VV3D-TET10-L2": 2187,
    "VV3D-TET10-L3": 14739,
    "VV3D-HEX8-L1": 81,
    "VV3D-HEX8-L2": 375,
    "VV3D-HEX8-L3": 2187,
    "VV3D-HEX20-L1": 243,
    "VV3D-HEX20-L2": 1275,
    "VV3D-HEX20-L3": 8019,
}
CRITERIA_BINDINGS = {
    "TET10": (
        "criteria_proposals_20261029/criteria_tet10_draft.json",
        "cb5f4e329c3c614ae7458ea42316ca2a95593109e419485b96deb84ed89aa64f",
    ),
    "HEX8": (
        "criteria_proposals_20261029/criteria_hex8_draft.json",
        "b05ab349bf90c99aa487f8d546724dbe72f03cfecabc8974be559399fe83f20f",
    ),
    "HEX20": (
        "criteria_proposals_20261029/criteria_hex20_draft.json",
        "4fc7a4c7c8f3e965caab298686a39ee143bfc591c516126836c8f7ad9c88c3c5",
    ),
}
ORACLE_BINDING = (
    "oracle.py",
    "1f0cddc469ff32d6f60590e451fe7256e0c505dbf0abde75a76c202fb71fe496",
)
HISTORICAL_TET4_REVIEW = {
    "case_ids": ["VV3D-TET4-L1", "VV3D-TET4-L2", "VV3D-TET4-L3"],
    "qualification_state": "HISTORICAL_CROSS_CAMPAIGN_REVIEW_NOT_PASS",
    "reexecution_required_for_cross_campaign_order_estimate": False,
    "evidence_ledger_sha256s": [
        "2788619d097d148c74a3e71cef456ee52bc03642d680f9090360418b61d20bf8",
        "5e090e1351578803669af37f04d161a6c4608436763f87d71e03315978446bb5",
        "43b3a680acf30493d057bb58079ad6a9b3c4834e371314c7ec5a935834e49732",
    ],
    "observed_orders": {
        "displacement_relative_l2": [1.3965437952, 1.7536240627],
        "energy_error_relative": [0.7518374627, 0.9223895476],
        "stress_error_relative": [0.7602420526, 0.9158275419],
        "scalar_energy_relative_l2": [1.5036749255, 1.8447790952],
    },
    "l3_scalar_energy_relative": 0.0615360686,
    "l3_scalar_energy_threshold": 0.05,
    "l3_scalar_energy_verdict": "FAIL_THRESHOLD_NOT_MET",
    "proof_transfer_to_family_remainder": False,
}
PREDECESSOR_LEDGER_BINDINGS = (
    {
        "campaign_id": "WP12-VV3D-ADAPTIVE-20261029-R1",
        "ledger_scope_id": "wp12_vv3d_adaptive",
        "path": r"E:\QFSolverAgents\evidence\wp12-vv3d-adaptive"
        r"\node-attempt-ledger-wp12-vv3d-adaptive-r1.jsonl",
        "sha256": "2788619d097d148c74a3e71cef456ee52bc03642d680f9090360418b61d20bf8",
        "attempts": 2,
        "elapsed_seconds_by_attempt": (15.81295399996452, 2.8482145000016317),
        "statuses": ("PASS", "INFRA_ERROR"),
    },
    {
        "campaign_id": "WP12-VV3D-RECOVERY-20261030-R2",
        "ledger_scope_id": "wp12_vv3d_recovery_r2",
        "path": r"E:\QFSolverAgents\evidence\wp12-vv3d-recovery-r2"
        r"\node-attempt-ledger-wp12-vv3d-recovery-r2.jsonl",
        "sha256": "5e090e1351578803669af37f04d161a6c4608436763f87d71e03315978446bb5",
        "attempts": 3,
        "elapsed_seconds_by_attempt": (
            16.151189800002612, 120.16368090000469, 1200.1613600000273,
        ),
        "statuses": ("PASS", "PASS", "INFRA_ERROR"),
    },
    {
        "campaign_id": "WP12-VV3D-TET4-L3-DIAGNOSTIC-20261030",
        "ledger_scope_id": "wp12_vv3d_tet4_l3_diagnostic",
        "path": r"E:\QFSolverAgents\evidence\wp12-vv3d-tet4-l3-diagnostic"
        r"\node-attempt-ledger-vv3d-tet4-l3-diagnostic.jsonl",
        "sha256": "3dfab79fabd3ae5986b265ecdebf6a4ed1030f3806ab25ae12f0a9d4a1f5e6c4",
        "attempts": 1,
        "elapsed_seconds_by_attempt": (2400.2913701999933,),
        "statuses": ("DIAGNOSTIC_STOP",),
    },
    {
        "campaign_id": "WP12-VV3D-TET4-L3-OPTIMIZED-DIAGNOSTIC-20261030",
        "ledger_scope_id": "wp12_vv3d_tet4_l3_optimized_diagnostic",
        "path": r"E:\QFSolverAgents\evidence\wp12-vv3d-tet4-l3-optimized-diagnostic"
        r"\node-attempt-ledger-vv3d-tet4-l3-optimized-diagnostic.jsonl",
        "sha256": "43b3a680acf30493d057bb58079ad6a9b3c4834e371314c7ec5a935834e49732",
        "attempts": 1,
        "elapsed_seconds_by_attempt": (313.8975885999389,),
        "statuses": ("DIAGNOSTIC_COMPLETED",),
    },
)
PREDECESSOR_ATTEMPTS = sum(item["attempts"] for item in PREDECESSOR_LEDGER_BINDINGS)
PREDECESSOR_ELAPSED_SECONDS = sum(
    seconds
    for item in PREDECESSOR_LEDGER_BINDINGS
    for seconds in item["elapsed_seconds_by_attempt"]
)
BUDGET = {
    "scope_attempts_max": len(CASE_IDS),
    "combined_attempts_max": 24,
    "cumulative_seconds_max": 28_800,
    "timeout_seconds": 1_200,
    "rss_soft_limit_mib": 4_096,
    "selected_dofs_max": 30_000,
    "concurrency": 1,
    "implicit_retry": False,
    "predecessor_accounting": "CONSERVATIVE_ALL_LINKED_LEDGERS",
    "predecessor_attempts_charged": PREDECESSOR_ATTEMPTS,
    "predecessor_elapsed_seconds_charged": PREDECESSOR_ELAPSED_SECONDS,
}
STOP_POLICY = {
    "non_pass": "STOP",
    "provenance_or_ledger_error": "STOP",
    "budget_insufficient": "REFUSE_BEFORE_RESERVATION",
    "retry": "FORBIDDEN",
    "next_case": "AFTER_PASS_ONLY",
}
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class FamilyRemainderContractError(ValueError):
    """A nine-case family-remainder contract or decision is invalid."""


def canonical_sha256(value: Any) -> str:
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise FamilyRemainderContractError("binding is not finite canonical JSON") from exc
    return hashlib.sha256(raw).hexdigest()


def predecessor_contract_bindings() -> list[dict[str, Any]]:
    """Return the JSON-shaped immutable predecessor records for the contract."""
    return [
        {
            **item,
            "elapsed_seconds_by_attempt": list(item["elapsed_seconds_by_attempt"]),
            "statuses": list(item["statuses"]),
        }
        for item in PREDECESSOR_LEDGER_BINDINGS
    ]


def expected_nodeid(case_id: str) -> str:
    if case_id not in CASE_IDS:
        raise FamilyRemainderContractError("case is outside the exact nine-case family remainder")
    return NODEID_PREFIX + case_id + "]"


def validate_contract(
    contract: Mapping[str, Any],
    *,
    scientific_fingerprint: str,
    controller_fingerprint: str,
) -> str:
    """Validate exact scope, predecessor, case and resource bindings; return digest."""
    fields = {
        "schema", "campaign_id", "scope_id", "scientific_fingerprint", "controller_fingerprint",
        "predecessor_ledgers", "budget", "case_ids", "excluded_case_ids", "cases",
        "excluded_routes", "stop_policy", "historical_tet4_review", "status",
    }
    if not isinstance(contract, Mapping) or set(contract) != fields:
        raise FamilyRemainderContractError("contract has missing or unexpected fields")
    if (
        contract.get("schema") != CONTRACT_SCHEMA
        or contract.get("campaign_id") != CAMPAIGN_ID
        or contract.get("scope_id") != SCOPE_ID
        or contract.get("scientific_fingerprint") != scientific_fingerprint
        or contract.get("controller_fingerprint") != controller_fingerprint
        or not isinstance(scientific_fingerprint, str)
        or not _SHA256.fullmatch(scientific_fingerprint)
        or not isinstance(controller_fingerprint, str)
        or not _SHA256.fullmatch(controller_fingerprint)
        or contract.get("status") != "PREPARED_NOT_AUTHORIZED"
        or contract.get("budget") != BUDGET
        or contract.get("case_ids") != list(CASE_IDS)
        or contract.get("excluded_case_ids") != list(EXCLUDED_CASE_IDS)
        or contract.get("excluded_routes") != ["H1", "QLOAD", "QPOST"]
        or contract.get("stop_policy") != STOP_POLICY
        or contract.get("historical_tet4_review") != HISTORICAL_TET4_REVIEW
        or contract.get("predecessor_ledgers") != predecessor_contract_bindings()
    ):
        raise FamilyRemainderContractError("contract identity, predecessor, budget or STOP policy mismatch")
    cases = contract.get("cases")
    if not isinstance(cases, list) or len(cases) != len(CASE_IDS):
        raise FamilyRemainderContractError("contract must include exactly nine FEM cases")
    for case_id, case in zip(CASE_IDS, cases, strict=True):
        if not isinstance(case, Mapping) or set(case) != {
            "case_id", "nodeid", "mesh_sha256", "selected_dofs", "timeout_seconds",
            "rss_soft_limit_mib", "archive_size_limit_mib", "max_attempts", "status",
            "criteria_path", "criteria_file_sha256", "oracle_path", "oracle_sha256",
        }:
            raise FamilyRemainderContractError("case record has missing or unexpected fields")
        family = case_id.split("-")[1]
        criteria_path, criteria_sha = CRITERIA_BINDINGS[family]
        if (
            case.get("case_id") != case_id
            or case.get("nodeid") != expected_nodeid(case_id)
            or not isinstance(case.get("mesh_sha256"), str)
            or not _SHA256.fullmatch(case["mesh_sha256"])
            or type(case.get("selected_dofs")) is not int
            or case.get("selected_dofs") != SELECTED_DOFS[case_id]
            or type(case.get("timeout_seconds")) is not int
            or case.get("timeout_seconds") != BUDGET["timeout_seconds"]
            or type(case.get("rss_soft_limit_mib")) is not int
            or case.get("rss_soft_limit_mib") != BUDGET["rss_soft_limit_mib"]
            or type(case.get("archive_size_limit_mib")) is not int
            or case.get("archive_size_limit_mib") != 256
            or type(case.get("max_attempts")) is not int
            or case.get("max_attempts") != 1
            or case.get("status") != "PREPARED_NOT_AUTHORIZED"
            or case.get("criteria_path") != criteria_path
            or case.get("criteria_file_sha256") != criteria_sha
            or case.get("oracle_path") != ORACLE_BINDING[0]
            or case.get("oracle_sha256") != ORACLE_BINDING[1]
        ):
            raise FamilyRemainderContractError(f"case binding or limits mismatch for {case_id}")
    return canonical_sha256(contract)


def validate_owner_decision(
    decision: Mapping[str, Any],
    *,
    contract_sha256: str,
    scientific_fingerprint: str,
    controller_fingerprint: str,
) -> str:
    """Validate an Owner approval bound to this exact frozen contract."""
    fields = {
        "schema", "campaign_id", "scope_id", "decision_id", "approved_by", "approved_at_utc",
        "contract_sha256", "case_ids", "scientific_fingerprint", "controller_fingerprint",
        "budget", "status",
    }
    decision_id = decision.get("decision_id") if isinstance(decision, Mapping) else None
    if (
        not isinstance(decision, Mapping)
        or set(decision) != fields
        or decision.get("schema") != DECISION_SCHEMA
        or decision.get("campaign_id") != CAMPAIGN_ID
        or decision.get("scope_id") != SCOPE_ID
        or not isinstance(decision_id, str)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,63}", decision_id)
        or decision.get("approved_by") != "Owner"
        or not isinstance(decision.get("approved_at_utc"), str)
        or not decision["approved_at_utc"]
        or decision.get("contract_sha256") != contract_sha256
        or not _SHA256.fullmatch(str(contract_sha256))
        or decision.get("case_ids") != list(CASE_IDS)
        or decision.get("scientific_fingerprint") != scientific_fingerprint
        or decision.get("controller_fingerprint") != controller_fingerprint
        or decision.get("budget") != BUDGET
        or decision.get("status") != "APPROVED"
    ):
        raise FamilyRemainderContractError("Owner decision does not approve the exact nine-case contract")
    return canonical_sha256(decision)
