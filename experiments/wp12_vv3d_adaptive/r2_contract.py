"""Strict, preparation-only contract primitives for VV3D recovery R2.

This module defines the closed R2 case set and validates prospective
campaign/Owner-decision records. It does not authenticate an Owner, reserve a
ledger attempt, assemble an element, or invoke a solver.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any


CAMPAIGN_ID = "WP12-VV3D-RECOVERY-20261030-R2"
SCOPE_ID = "wp12_vv3d_recovery_r2"
CONTRACT_SCHEMA = "qf-wp12-vv3d-r2-campaign-contract-v1"
DECISION_SCHEMA = "qf-wp12-vv3d-r2-owner-decision-v1"
CASE_IDS = tuple(
    f"VV3D-{family}-L{level}"
    for family in ("TET4", "TET10", "HEX8", "HEX20")
    for level in (1, 2, 3)
)
NODEID_PREFIX = "tests/unit/test_wp12_vv3d_adaptive_prepared.py::test_prepared_fem_case["
R1_LEDGER_SHA256 = "2788619d097d148c74a3e71cef456ee52bc03642d680f9090360418b61d20bf8"
BUDGET = {
    "r2_attempts_max": 12,
    "combined_attempts_max": 24,
    "cumulative_seconds_max": 28_800,
    "timeout_max_seconds": 1_200,
    "rss_soft_limit_mib": 4_096,
    "dofs_max": 30_000,
    "concurrency": 1,
    "implicit_retry": False,
}
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class R2ContractError(ValueError):
    """A prospective R2 binding is incomplete, stale, or outside the closed set."""


def canonical_sha256(value: Any) -> str:
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise R2ContractError("R2 binding is not finite canonical JSON") from exc
    return hashlib.sha256(raw).hexdigest()


def expected_nodeid(case_id: str) -> str:
    if case_id not in CASE_IDS:
        raise R2ContractError("case is not in the twelve-case R2 initial tranche")
    return NODEID_PREFIX + case_id + "]"


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def validate_contract(
    contract: Mapping[str, Any],
    *,
    scientific_fingerprint: str,
    controller_fingerprint: str,
    r1_ledger_sha256: str,
) -> str:
    """Validate the frozen R2 contract, returning its canonical digest.

    The JSON record is a workflow binding, not cryptographic authentication of
    the human Owner. The official controller must separately validate and
    archive the Owner decision.
    """
    fields = {
        "schema", "campaign_id", "scope_id", "scientific_fingerprint",
        "controller_fingerprint", "r1_predecessor", "budget", "case_ids",
        "cases", "excluded_routes", "stop_policy", "status",
    }
    if not isinstance(contract, Mapping) or set(contract) != fields:
        raise R2ContractError("R2 contract has missing or unexpected fields")
    if (
        contract.get("schema") != CONTRACT_SCHEMA
        or contract.get("campaign_id") != CAMPAIGN_ID
        or contract.get("scope_id") != SCOPE_ID
        or contract.get("scientific_fingerprint") != scientific_fingerprint
        or contract.get("controller_fingerprint") != controller_fingerprint
        or not _is_sha256(scientific_fingerprint)
        or not _is_sha256(controller_fingerprint)
        or not _is_sha256(r1_ledger_sha256)
        or contract.get("status") != "PREPARED_NOT_AUTHORIZED"
        or contract.get("budget") != BUDGET
    ):
        raise R2ContractError("R2 identity, budget, or preparation-only status mismatch")
    predecessor = contract.get("r1_predecessor")
    if (
        not isinstance(predecessor, Mapping)
        or set(predecessor) != {"campaign_id", "ledger_scope_id", "ledger_sha256", "case_results"}
        or predecessor.get("campaign_id") != "WP12-VV3D-ADAPTIVE-20261029-R1"
        or predecessor.get("ledger_scope_id") != "wp12_vv3d_adaptive"
        or predecessor.get("ledger_sha256") != r1_ledger_sha256
        or r1_ledger_sha256 != R1_LEDGER_SHA256
        or predecessor.get("case_results") != [
            {"case_id": "VV3D-TET4-L1", "status": "PASS", "attempts": 1},
            {"case_id": "VV3D-TET4-L2", "status": "INFRA_ERROR", "attempts": 1},
        ]
    ):
        raise R2ContractError("R2 must bind the exact immutable two-attempt R1 predecessor")
    if contract.get("case_ids") != list(CASE_IDS):
        raise R2ContractError("R2 case IDs must be the exact ordered twelve initial FEM cases")
    cases = contract.get("cases")
    if not isinstance(cases, list) or len(cases) != len(CASE_IDS):
        raise R2ContractError("R2 contract must include exactly twelve cases")
    for case_id, case in zip(CASE_IDS, cases, strict=True):
        if not isinstance(case, Mapping) or set(case) != {
            "case_id", "nodeid", "mesh_sha256", "selected_dofs", "timeout_seconds",
            "rss_soft_limit_mib", "archive_size_limit_mib", "max_attempts", "status",
        }:
            raise R2ContractError("R2 case record has missing or unexpected fields")
        if (
            case.get("case_id") != case_id
            or case.get("nodeid") != expected_nodeid(case_id)
            or not _is_sha256(case.get("mesh_sha256"))
            or type(case.get("selected_dofs")) is not int
            or not 0 < case["selected_dofs"] <= BUDGET["dofs_max"]
            or type(case.get("timeout_seconds")) is not int
            or not 0 < case["timeout_seconds"] <= BUDGET["timeout_max_seconds"]
            or case.get("rss_soft_limit_mib") != BUDGET["rss_soft_limit_mib"]
            or case.get("archive_size_limit_mib") != 256
            or case.get("max_attempts") != 1
            or case.get("status") != "PREPARED_NOT_AUTHORIZED"
        ):
            raise R2ContractError(f"R2 case binding or limits mismatch for {case_id}")
    if contract.get("excluded_routes") != ["H1", "QLOAD", "QPOST"]:
        raise R2ContractError("R2 initial decision must explicitly exclude H1, QLOAD, and QPOST")
    if contract.get("stop_policy") != {
        "non_pass": "STOP",
        "provenance_or_ledger_error": "STOP",
        "budget_insufficient": "REFUSE_BEFORE_RESERVATION",
        "retry": "FORBIDDEN",
    }:
        raise R2ContractError("R2 STOP and retry policy differs from the approved recovery strategy")
    return canonical_sha256(contract)


def validate_owner_decision(
    decision: Mapping[str, Any],
    *,
    contract_sha256: str,
    scientific_fingerprint: str,
    controller_fingerprint: str,
) -> str:
    """Validate the Owner decision's exact contract/case/identity binding.

    This validates structure and hashes only; it does not cryptographically
    prove authorship. The controller's reviewed decision archive remains the
    authorization source.
    """
    fields = {
        "schema", "decision_id", "status", "approved_by", "campaign_id", "scope_id",
        "contract_sha256", "case_ids", "scientific_fingerprint", "controller_fingerprint",
        "budget", "created_at_utc",
    }
    if not isinstance(decision, Mapping) or set(decision) != fields:
        raise R2ContractError("R2 Owner decision has missing or unexpected fields")
    decision_id = decision.get("decision_id")
    if (
        decision.get("schema") != DECISION_SCHEMA
        or not isinstance(decision_id, str)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,63}", decision_id)
        or decision.get("status") != "APPROVED"
        or decision.get("approved_by") != "Owner"
        or decision.get("campaign_id") != CAMPAIGN_ID
        or decision.get("scope_id") != SCOPE_ID
        or decision.get("contract_sha256") != contract_sha256
        or not _is_sha256(contract_sha256)
        or decision.get("case_ids") != list(CASE_IDS)
        or decision.get("scientific_fingerprint") != scientific_fingerprint
        or decision.get("controller_fingerprint") != controller_fingerprint
        or decision.get("budget") != BUDGET
        or not isinstance(decision.get("created_at_utc"), str)
        or not decision["created_at_utc"]
    ):
        raise R2ContractError("R2 Owner decision does not bind the exact campaign contract")
    return canonical_sha256(decision)
