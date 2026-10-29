"""Closed, sequential WP12-A P0 batch contract support.

This module is called only by the fixed development controller. Its JSON
records are workflow evidence, not a cryptographic signature or OS sandbox.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


BATCH_CONTRACT_SCHEMA = "qfsolver-wp12a-p0-batch-contract-v1"
BATCH_DECISION_SCHEMA = "qfsolver-wp12a-p0-batch-owner-decision-v1"
BATCH_RECEIPT_SCHEMA = "qfsolver-wp12a-p0-batch-case-receipt-v1"
CASE_MANIFEST_SCHEMA = "qfsolver-wp12a-p0-scientific-case-v1"
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{7,63}$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_CONTINUABLE_OUTCOMES = {"PASS", "SCIENTIFIC_ASSERTION_FAILED"}
_STOP_CONDITIONS = [
    "source/controller/criteria/budget/nodeid/provenance mismatch",
    "ledger transition not attributable to this approved campaign",
    "infrastructure failure",
    "incomplete RESERVED attempt",
    "pytest failure is not one exact assertion failure or its JUnit report is unavailable",
]
_PROVENANCE_STOP_STATES = {
    "SOURCE_CHANGED_DURING_RUN",
    "PROVENANCE_MISMATCH",
    "PREFLIGHT_SOURCE_CHANGED",
    "PREFLIGHT_CONTROLLER_CHANGED",
    "PREFLIGHT_LEDGER_CHANGED",
}


def _canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> Any:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicates,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite JSON token {value}")),
    )


def _raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=True).relative_to(root.resolve(strict=True))
        return True
    except (OSError, ValueError):
        return False


def _expected_owner_cases(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "ordinal": case["ordinal"],
            "nodeid": case["nodeid"],
            "case_id": case["case_id"],
            "case_manifest_sha256": case["case_manifest"]["sha256"],
            "criteria_sha256": case["case_manifest"]["criteria_sha256"],
            "identity": case["identity"],
            "source_fingerprint": case["source_fingerprint"],
            "selected_dofs": case["selection"]["selected_dofs"],
            "selection": case["selection"],
            "budget": case["budget"],
            "criteria": case["criteria"],
            "conditions_of_stop": case["conditions_of_stop"],
            "continue_after": case["continue_after"],
            "max_attempts": case["max_attempts"],
        }
        for case in contract["ordered_cases"]
    ]


def _ledger_payload(
    controller: Any, path: Path, predecessor: Mapping[str, Any], *, allow_reserved: bool = False
) -> dict[str, Any]:
    if not path.is_file():
        return {
            "schema": "qfsolver-development-node-ledger-v2",
            "mandate_id": controller.WP12_OWNER_ENVELOPES["wp12_dynamics"]["development_mandate_id"],
            "predecessor": dict(predecessor),
            "entries": {},
        }
    payload = _read_json(path)
    if not isinstance(payload, dict):
        raise controller.PolicyError("WP12-A P0 batch ledger must be a JSON object")
    for attempts in payload.get("entries", {}).values():
        if not isinstance(attempts, list):
            raise controller.PolicyError("WP12-A P0 batch ledger contains a malformed attempt list")
        if any(not isinstance(item, Mapping) for item in attempts):
            raise controller.PolicyError("WP12-A P0 batch ledger contains a malformed attempt record")
        if not allow_reserved and any(item.get("state") == "RESERVED" for item in attempts):
            raise controller.PolicyError("WP12-A P0 batch cannot start or resume while a prior attempt is unfinished")
    return payload


def prepare_contract(
    controller: Any,
    campaign_id: str,
    case_manifest_paths: Sequence[Path],
) -> dict[str, Any]:
    """Freeze exact registered scientific case manifests and the current ledger baseline."""
    if not _ID_RE.fullmatch(campaign_id):
        raise controller.PolicyError("WP12-A P0 campaign ID must be 8 to 64 safe characters")
    if len(case_manifest_paths) < 2 or len(case_manifest_paths) > 18:
        raise controller.PolicyError("WP12-A P0 batch requires 2 to 18 ordered exact case manifests")

    policy = controller.load_policy()
    worktree_id = "wp12_dynamics"
    entry = policy["worktrees"][worktree_id]
    store = controller._run_root(policy, worktree_id)
    provenance = controller._controller_provenance()
    controller_fingerprint = controller._stable_fingerprint(provenance)
    cases: list[dict[str, Any]] = []
    seen: set[str] = set()
    common_identity: dict[str, Any] | None = None
    case_ids: set[str] = set()

    for ordinal, supplied_path in enumerate(case_manifest_paths, start=1):
        case_path = Path(supplied_path).resolve(strict=True)
        if not _within(case_path, controller.ROOT.resolve()):
            raise controller.PolicyError("P0 case manifest must remain inside the controller repository")
        manifest = _read_json(case_path)
        expected_case_fields = {
            "schema", "state", "case_id", "worktree_id", "mandate_id", "nodeid", "science", "identity",
            "source_fingerprint", "test_module_sha256", "selection", "criteria", "criteria_sha256",
            "max_attempts", "continue_after", "conditions_of_stop",
        }
        if (
            not isinstance(manifest, dict)
            or manifest.get("schema") != CASE_MANIFEST_SCHEMA
            or manifest.get("state") != "PROPOSED_NOT_AUTHORIZED"
            or set(manifest) != expected_case_fields
        ):
            raise controller.PolicyError("unsupported WP12-A P0 scientific case manifest")
        target = manifest.get("nodeid")
        if not isinstance(target, str) or target in seen:
            raise controller.PolicyError("WP12-A P0 batch nodeids must be exact and unique")
        case_id = manifest.get("case_id")
        if not isinstance(case_id, str) or not _ID_RE.fullmatch(case_id) or case_id in case_ids:
            raise controller.PolicyError("WP12-A P0 case IDs must be unique safe identifiers")
        seen.add(target)
        case_ids.add(case_id)
        targets = controller.resolve_targets("fem_exploratory", target, policy, worktree_id=worktree_id)
        if (
            targets != [target]
            or target not in controller.WP12_DYNAMICS_PREFLIGHT_NODEIDS
            or target not in controller.WP12_DYNAMICS_P0_BATCH_NODEIDS
        ):
            raise controller.PolicyError("P0 case is not in the exact reviewed P0 and Dynamics collect-only allowlists")
        active_entry, science_root, _source_root, identity, source_fingerprint = controller._registered_worktree(
            worktree_id, target, policy
        )
        if common_identity is None:
            common_identity = dict(identity)
        elif identity != common_identity:
            raise controller.PolicyError("all P0 case manifests must share one frozen scientific checkout identity")
        selection = controller._wp12_active_registration(worktree_id, target, active_entry, source_fingerprint)
        expected_selection = {
            "selected_dofs": selection["selected_dofs"],
            "timeout_seconds": selection["timeout_seconds"],
            "selection_basis": selection["selection_basis"],
            "timeout_reason": selection["timeout_reason"],
        }
        science = manifest.get("science")
        criteria = manifest.get("criteria")
        if (
            manifest.get("worktree_id") != worktree_id
            or manifest.get("mandate_id") != entry["development_mandate_id"]
            or manifest.get("identity") != identity
            or manifest.get("source_fingerprint") != source_fingerprint
            or manifest.get("selection") != expected_selection
            or manifest.get("criteria_sha256") != _canonical_sha256(criteria)
            or not isinstance(criteria, Mapping)
            or not isinstance(criteria.get("acceptance_source_sha256"), str)
            or not _SHA_RE.fullmatch(criteria["acceptance_source_sha256"])
            or manifest.get("test_module_sha256") != criteria.get("acceptance_source_sha256")
            or controller._sha256(science_root / target.split("::", maxsplit=1)[0])
            != criteria.get("acceptance_source_sha256")
            or science != {"head": identity["head"], "tree": identity["tree"], "branch": identity["branch"]}
        ):
            raise controller.PolicyError("P0 case manifest differs from its inspected source, criteria or DDL registration")
        if (
            manifest.get("max_attempts") != 1
            or manifest.get("continue_after") != ["PASS", "SCIENTIFIC_ASSERTION_FAILED"]
            or manifest.get("conditions_of_stop") != _STOP_CONDITIONS
            or set(criteria) != {"oracle", "oracle_independence", "acceptance", "acceptance_source_sha256"}
        ):
            raise controller.PolicyError("each WP12-A P0 case is limited to one attempt in a batch decision")
        cases.append(
            {
                "ordinal": ordinal,
                "nodeid": target,
                "case_id": case_id,
                "case_manifest": {
                    "path": str(case_path),
                    "sha256": _raw_sha256(case_path),
                    "criteria_sha256": manifest["criteria_sha256"],
                },
                "identity": identity,
                "source_fingerprint": source_fingerprint,
                "selection": expected_selection,
                "criteria": dict(criteria),
                "conditions_of_stop": list(manifest["conditions_of_stop"]),
                "budget": {
                    "timeout_seconds": selection["timeout_seconds"],
                    **{
                        key: value
                        for key, value in active_entry["budgets"].items()
                        if key != "timeout_seconds"
                    },
                },
                "max_attempts": 1,
                "continue_after": list(manifest.get("continue_after", [])),
            }
        )

    if [case["nodeid"] for case in cases] != list(controller.WP12_DYNAMICS_P0_BATCH_NODEIDS):
        raise controller.PolicyError("P0 batch preparation requires all six reviewed case manifests in frozen order")

    ledger_path, ledger_lock, mandate_id, predecessor = controller._node_ledger_context(policy, store, worktree_id)
    if predecessor is None or mandate_id != entry["development_mandate_id"]:
        raise controller.PolicyError("P0 batch requires the registered Dynamics v2 ledger and historical predecessor")
    with controller._node_attempt_locks(ledger_path, ledger_lock, worktree_id):
        # Read again while locked so the frozen digest and bytes are one snapshot.
        baseline_sha = _raw_sha256(ledger_path) if ledger_path.is_file() else None
        baseline_bytes = ledger_path.read_bytes() if ledger_path.is_file() else None
        predecessor_path = (store / predecessor["path"]).resolve()
        predecessor_sha = _raw_sha256(predecessor_path)
        if predecessor_sha != predecessor["sha256"]:
            raise controller.PolicyError("historical Dynamics ledger changed while preparing P0 batch")
        baseline = _ledger_payload(controller, ledger_path, predecessor)
        _predecessor_path, _historical, predecessor_counts, predecessor_total = controller._wp12_dynamics_predecessor_history(
            store, predecessor, allowed_nodeids=set(entry["allowed_nodeids"])
        )
        controller._validate_wp12_dynamics_ledger(
            baseline,
            mandate_id=mandate_id,
            predecessor=predecessor,
            allowed_nodeids=set(entry["allowed_nodeids"]),
            predecessor_counts=predecessor_counts,
            predecessor_total=predecessor_total,
            attempt_limit=int(entry["attempt_limit_per_nodeid"]),
            total_limit=int(entry["max_total_attempts"]),
        )
        if any(record.get("state") == "RESERVED" for records in baseline["entries"].values() for record in records):
            raise controller.PolicyError("cannot freeze a P0 batch while the Dynamics ledger has a RESERVED attempt")
        _validate_remaining_budget(controller, policy, store, baseline, cases[0]["nodeid"])
        prefix = f"{mandate_id}:wp12_dynamics:"
        current_attempts = sum(
            len(records)
            for key, records in baseline["entries"].items()
            if key.startswith(prefix) and isinstance(records, list)
        )
        if predecessor_total + current_attempts + len(cases) > int(entry["max_total_attempts"]):
            raise controller.PolicyError("P0 batch does not fit within the remaining Dynamics mission attempt budget")
        for case in cases:
            key = f"{prefix}{case['nodeid']}"
            prior = predecessor_counts.get(case["nodeid"], 0) + len(baseline["entries"].get(key, []))
            if prior + 1 > int(entry["attempt_limit_per_nodeid"]):
                raise controller.PolicyError(f"P0 batch has no remaining attempt for {case['nodeid']}")

    # Keep the final snapshot check and immutable contract publication under the
    # same lock used by Dynamics attempt writers. If the ledger changed while
    # the contract was being assembled, no stale Owner artifact is published.
    with controller._node_attempt_locks(ledger_path, ledger_lock, worktree_id):
        current_bytes = ledger_path.read_bytes() if ledger_path.is_file() else None
        current_sha = _raw_sha256(ledger_path) if current_bytes is not None else None
        if current_sha != baseline_sha or current_bytes != baseline_bytes:
            raise controller.PolicyError("Dynamics ledger changed while the P0 batch contract was being prepared")
        batch_dir = store / "authorizations" / worktree_id / "batches" / campaign_id
        snapshot_path = batch_dir / "ledger-baseline.json"
        contract_path = batch_dir / "contract.json"
        decision_path = batch_dir / "owner-decision.json"
        if batch_dir.exists():
            raise controller.PolicyError("WP12-A P0 campaign ID already exists; refusing to overwrite batch evidence")
        batch_dir.mkdir(parents=True)
        if baseline_bytes is not None:
            with snapshot_path.open("xb") as stream:
                stream.write(baseline_bytes)
                stream.flush()
            snapshot_sha = _raw_sha256(snapshot_path)
        else:
            snapshot_sha = None
        contract: dict[str, Any] = {
            "schema": BATCH_CONTRACT_SCHEMA,
            "state": "PREPARED_NOT_AUTHORIZED",
            "execution_authorized": False,
            "do_not_execute": True,
            "campaign_id": campaign_id,
            "worktree_id": worktree_id,
            "mandate_id": mandate_id,
            "controller": {"provenance": provenance, "fingerprint": controller_fingerprint},
            "ordered_cases": cases,
            "initial_ledger": {
                "path": str(ledger_path),
                "sha256": baseline_sha,
                "snapshot_path": str(snapshot_path) if baseline_bytes is not None else None,
                "snapshot_sha256": snapshot_sha,
                "historical_predecessor": dict(predecessor),
                "historical_predecessor_sha256": predecessor_sha,
            },
            "attempt_policy": {
                "one_attempt_per_case": True,
                "max_total_attempts": int(entry["max_total_attempts"]),
                "max_attempts_per_nodeid": int(entry["attempt_limit_per_nodeid"]),
                "implicit_retry": False,
            },
            "continuation_policy": {
                "continue_after_scientific_failure": True,
                "scientific_failure_classification": "one exact testcase with one AssertionError failure and no errors or skips in JUnit",
                "continuable_classifications": ["PASS", "SCIENTIFIC_ASSERTION_FAILED"],
                "stop_on_provenance_anomaly": True,
                "stop_on_infrastructure_failure": True,
                "stop_on_unfinished_reservation": True,
            },
            "decision_path": str(decision_path),
            "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        controller._atomic_json_new(contract_path, contract)
        decision_template = {
            "schema": BATCH_DECISION_SCHEMA,
            "state": "PREPARED_NOT_AUTHORIZED",
            "execution_authorized": False,
            "do_not_execute": True,
            "campaign_id": campaign_id,
            "contract_path": str(contract_path),
            "contract_sha256": _raw_sha256(contract_path),
            "decision_id": None,
            "approved_by": None,
            "approved_at_utc": None,
            "reason": None,
            "approved_cases": _expected_owner_cases(contract),
            "no_retry": True,
        }
        decision_template_path = batch_dir / "owner-decision-template.json"
        controller._atomic_json_new(decision_template_path, decision_template)
        return {
            "state": contract["state"],
            "contract_path": str(contract_path),
            "contract_sha256": _raw_sha256(contract_path),
            "decision_template_path": str(decision_template_path),
            "decision_template_sha256": _raw_sha256(decision_template_path),
            "case_count": len(cases),
            "initial_ledger_sha256": baseline_sha,
        }


def _validated_authorization(
    controller: Any,
    contract_path: Path,
    contract_sha256: str,
    decision_path: Path,
    decision_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], Path]:
    policy = controller.load_policy()
    entry = policy["worktrees"]["wp12_dynamics"]
    store = controller._run_root(policy, "wp12_dynamics")
    active_ledger_path, _ledger_lock, active_mandate, active_predecessor = controller._node_ledger_context(
        policy, store, "wp12_dynamics"
    )
    expected_dir = (store / "authorizations" / "wp12_dynamics" / "batches").resolve()
    contract_path = contract_path.resolve(strict=True)
    decision_path = decision_path.resolve(strict=True)
    if not _within(contract_path, expected_dir) or not _within(decision_path, expected_dir):
        raise controller.PolicyError("P0 batch authorization files must remain under the Dynamics evidence root")
    if not _SHA_RE.fullmatch(contract_sha256) or _raw_sha256(contract_path) != contract_sha256:
        raise controller.PolicyError("P0 batch contract SHA-256 mismatch")
    if not _SHA_RE.fullmatch(decision_sha256) or _raw_sha256(decision_path) != decision_sha256:
        raise controller.PolicyError("P0 batch Owner decision SHA-256 mismatch")
    contract = _read_json(contract_path)
    decision = _read_json(decision_path)
    if not isinstance(contract, dict) or not isinstance(decision, dict):
        raise controller.PolicyError("P0 batch contract and Owner decision must be JSON objects")
    contract_fields = {
        "schema", "state", "execution_authorized", "do_not_execute", "campaign_id", "worktree_id",
        "mandate_id", "controller", "ordered_cases", "initial_ledger", "attempt_policy",
        "continuation_policy", "decision_path", "prepared_at_utc",
    }
    if not isinstance(contract.get("attempt_policy"), Mapping) or set(contract["attempt_policy"]) != {
        "one_attempt_per_case", "max_total_attempts", "max_attempts_per_nodeid", "implicit_retry",
    }:
        raise controller.PolicyError("P0 batch attempt policy has unexpected or missing fields")
    try:
        prepared_at = datetime.fromisoformat(str(contract.get("prepared_at_utc", "")).replace("Z", "+00:00"))
    except ValueError as exc:
        raise controller.PolicyError("P0 batch preparation timestamp is invalid") from exc
    if prepared_at.tzinfo is None or prepared_at.utcoffset() != timezone.utc.utcoffset(prepared_at):
        raise controller.PolicyError("P0 batch preparation timestamp must use UTC")
    if (
        set(contract) != contract_fields
        or contract.get("schema") != BATCH_CONTRACT_SCHEMA
        or contract.get("state") != "PREPARED_NOT_AUTHORIZED"
        or contract.get("execution_authorized") is not False
        or contract.get("do_not_execute") is not True
        or contract.get("worktree_id") != "wp12_dynamics"
        or not isinstance(contract.get("campaign_id"), str)
        or not _ID_RE.fullmatch(contract.get("campaign_id", ""))
        or contract.get("mandate_id") != entry["development_mandate_id"]
        or contract.get("decision_path") != str(contract_path.parent / "owner-decision.json")
        or decision_path != contract_path.parent / "owner-decision.json"
        or not isinstance(contract.get("attempt_policy"), Mapping)
        or not isinstance(contract.get("continuation_policy"), Mapping)
        or contract.get("attempt_policy", {}).get("implicit_retry") is not False
        or contract.get("attempt_policy", {}).get("one_attempt_per_case") is not True
        or contract.get("attempt_policy", {}).get("max_total_attempts") != int(entry["max_total_attempts"])
        or contract.get("attempt_policy", {}).get("max_attempts_per_nodeid")
        != int(entry["attempt_limit_per_nodeid"])
        or contract.get("continuation_policy")
        != {
            "continue_after_scientific_failure": True,
            "scientific_failure_classification": "one exact testcase with one AssertionError failure and no errors or skips in JUnit",
            "continuable_classifications": ["PASS", "SCIENTIFIC_ASSERTION_FAILED"],
            "stop_on_provenance_anomaly": True,
            "stop_on_infrastructure_failure": True,
            "stop_on_unfinished_reservation": True,
        }
        or contract_path.name != "contract.json"
        or contract.get("campaign_id") != contract_path.parent.name
        or contract.get("decision_path") != str(decision_path)
    ):
        raise controller.PolicyError("P0 batch contract has an invalid schema or execution state")
    provenance = controller._controller_provenance()
    fingerprint = controller._stable_fingerprint(provenance)
    if contract.get("controller") != {"provenance": provenance, "fingerprint": fingerprint}:
        raise controller.PolicyError("P0 batch controller identity or fingerprint changed")
    cases = contract.get("ordered_cases")
    if (
        not isinstance(cases, list)
        or len(cases) != len(controller.WP12_DYNAMICS_P0_BATCH_NODEIDS)
        or len(cases) > int(entry["nodeid_registration"]["max_nodeids"])
    ):
        raise controller.PolicyError("P0 batch case list is empty or exceeds the active Dynamics registration cap")
    targets = [case.get("nodeid") for case in cases if isinstance(case, Mapping)]
    if (
        len(targets) != len(cases)
        or len(set(targets)) != len(targets)
        or targets != list(controller.WP12_DYNAMICS_P0_BATCH_NODEIDS)
    ):
        raise controller.PolicyError("P0 batch list must contain the six reviewed nodeids in frozen order")
    case_ids: set[str] = set()
    for index, case in enumerate(cases, start=1):
        if set(case) != {
            "ordinal", "nodeid", "case_id", "case_manifest", "identity", "source_fingerprint", "selection",
            "criteria", "conditions_of_stop", "budget", "max_attempts", "continue_after",
        }:
            raise controller.PolicyError("P0 batch case has unexpected or missing contract fields")
        if (
            not isinstance(case, Mapping)
            or case.get("ordinal") != index
            or case.get("max_attempts") != 1
            or case.get("continue_after") != ["PASS", "SCIENTIFIC_ASSERTION_FAILED"]
            or case.get("conditions_of_stop") != _STOP_CONDITIONS
            or not isinstance(case.get("criteria"), Mapping)
            or not isinstance(case.get("budget"), Mapping)
            or not isinstance(case.get("selection"), Mapping)
            or not isinstance(case.get("case_manifest"), Mapping)
        ):
            raise controller.PolicyError("P0 batch order or one-attempt-per-case contract is invalid")
        if not isinstance(case.get("case_id"), str) or not _ID_RE.fullmatch(case["case_id"]) or case["case_id"] in case_ids:
            raise controller.PolicyError("P0 batch case IDs must be unique safe identifiers")
        case_ids.add(case["case_id"])
        case_manifest_ref = case["case_manifest"]
        if set(case_manifest_ref) != {"path", "sha256", "criteria_sha256"}:
            raise controller.PolicyError("P0 case manifest reference is malformed")
        case_path = Path(case_manifest_ref["path"]).resolve(strict=True)
        if (
            not _within(case_path, controller.ROOT.resolve())
            or not _SHA_RE.fullmatch(str(case_manifest_ref.get("sha256", "")))
            or _raw_sha256(case_path) != case_manifest_ref["sha256"]
        ):
            raise controller.PolicyError("P0 case manifest changed after the batch contract was frozen")
        case_manifest = _read_json(case_path)
        if not isinstance(case_manifest, Mapping):
            raise controller.PolicyError("P0 scientific case manifest is malformed")
        if set(case_manifest) != {
            "schema", "state", "case_id", "worktree_id", "mandate_id", "nodeid", "science", "identity",
            "source_fingerprint", "test_module_sha256", "selection", "criteria", "criteria_sha256",
            "max_attempts", "continue_after", "conditions_of_stop",
        } or case_manifest.get("state") != "PROPOSED_NOT_AUTHORIZED":
            raise controller.PolicyError("P0 scientific case manifest has unexpected fields or state")
        target = case["nodeid"]
        controller.resolve_targets("fem_exploratory", target, policy, worktree_id="wp12_dynamics")
        if target not in controller.WP12_DYNAMICS_P0_BATCH_NODEIDS:
            raise controller.PolicyError("batch decision contains a nodeid outside the fixed WP12-A P0 candidate set")
        active_entry, science_root, _source_root, identity, source_fingerprint = controller._registered_worktree(
            "wp12_dynamics", target, policy
        )
        registration = controller._wp12_active_registration("wp12_dynamics", target, active_entry, source_fingerprint)
        expected_selection = {
            "selected_dofs": registration["selected_dofs"],
            "timeout_seconds": registration["timeout_seconds"],
            "selection_basis": registration["selection_basis"],
            "timeout_reason": registration["timeout_reason"],
        }
        expected_budget = {
            "timeout_seconds": registration["timeout_seconds"],
            **{key: value for key, value in active_entry["budgets"].items() if key != "timeout_seconds"},
        }
        acceptance_sha = controller._sha256(science_root / target.split("::", maxsplit=1)[0])
        if (
            case_manifest.get("worktree_id") != "wp12_dynamics"
            or case_manifest.get("mandate_id") != contract.get("mandate_id")
            or case_manifest.get("nodeid") != target
            or not isinstance(case_manifest.get("criteria"), Mapping)
            or case_manifest.get("identity") != identity
            or case_manifest.get("source_fingerprint") != source_fingerprint
            or case_manifest.get("test_module_sha256") != acceptance_sha
            or case_manifest.get("selection") != expected_selection
            or case_manifest.get("criteria", {}).get("acceptance_source_sha256") != acceptance_sha
            or case_manifest.get("criteria") != case.get("criteria")
            or set(case.get("criteria", {}))
            != {"oracle", "oracle_independence", "acceptance", "acceptance_source_sha256"}
            or case.get("criteria", {}).get("acceptance_source_sha256") != acceptance_sha
            or case_manifest.get("conditions_of_stop") != case.get("conditions_of_stop")
            or case_manifest.get("continue_after") != case.get("continue_after")
            or case_manifest.get("case_id") != case.get("case_id")
            or case.get("identity") != identity
            or case.get("source_fingerprint") != source_fingerprint
            or case.get("selection") != expected_selection
            or case.get("budget") != expected_budget
            or case_manifest.get("criteria_sha256") != _canonical_sha256(case_manifest.get("criteria"))
            or case.get("case_manifest", {}).get("criteria_sha256") != case_manifest.get("criteria_sha256")
            or case.get("continue_after") != case_manifest.get("continue_after")
            or not isinstance(case.get("continue_after"), list)
            or any(outcome not in _CONTINUABLE_OUTCOMES for outcome in case.get("continue_after", []))
        ):
            raise controller.PolicyError("P0 case source, nodeid, criteria or registered budget changed")
    ledger_info = contract.get("initial_ledger")
    if not isinstance(ledger_info, Mapping) or set(ledger_info) != {
        "path", "sha256", "snapshot_path", "snapshot_sha256", "historical_predecessor",
        "historical_predecessor_sha256",
    }:
        raise controller.PolicyError("P0 batch lacks its frozen initial ledger identity")
    if (
        Path(str(ledger_info.get("path", ""))).resolve() != active_ledger_path.resolve()
        or active_mandate != entry["development_mandate_id"]
        or active_predecessor is None
        or not isinstance(ledger_info.get("sha256"), (str, type(None)))
        or (ledger_info.get("sha256") is not None and not _SHA_RE.fullmatch(ledger_info["sha256"]))
    ):
        raise controller.PolicyError("P0 batch ledger path or mandate differs from the active Dynamics ledger")
    if ledger_info.get("historical_predecessor") != entry["node_attempt_ledger"]["predecessor"]:
        raise controller.PolicyError("P0 batch historical ledger predecessor differs from the active mandate")
    predecessor_path = store / ledger_info["historical_predecessor"]["path"]
    if _raw_sha256(predecessor_path) != ledger_info.get("historical_predecessor_sha256"):
        raise controller.PolicyError("immutable historical ledger predecessor changed")
    snapshot_path = ledger_info.get("snapshot_path")
    if ledger_info.get("sha256") is None:
        if snapshot_path is not None or ledger_info.get("snapshot_sha256") is not None:
            raise controller.PolicyError("empty initial ledger snapshot is malformed")
        baseline = _ledger_payload(controller, Path(ledger_info["path"]), ledger_info["historical_predecessor"])
    else:
        snapshot = Path(snapshot_path).resolve(strict=True)
        if not _within(snapshot, contract_path.parent) or _raw_sha256(snapshot) != ledger_info.get("snapshot_sha256"):
            raise controller.PolicyError("frozen initial ledger snapshot is missing or changed")
        if ledger_info.get("snapshot_sha256") != ledger_info.get("sha256"):
            raise controller.PolicyError("frozen initial ledger snapshot does not match its recorded identity")
        baseline = _read_json(snapshot)
    decision_fields = {
        "schema", "state", "execution_authorized", "do_not_execute", "campaign_id", "contract_path",
        "contract_sha256", "decision_id", "approved_by", "approved_at_utc", "reason", "approved_cases", "no_retry",
    }
    if (
        set(decision) != decision_fields
        or decision.get("schema") != BATCH_DECISION_SCHEMA
        or decision.get("state") != "OWNER_AUTHORIZED"
        or decision.get("execution_authorized") is not True
        or decision.get("do_not_execute") is not False
        or decision.get("campaign_id") != contract.get("campaign_id")
        or decision.get("contract_path") != str(contract_path)
        or decision.get("contract_sha256") != contract_sha256
        or decision.get("approved_cases") != _expected_owner_cases(contract)
        or decision.get("no_retry") is not True
        or decision.get("approved_by") != "Owner"
        or not isinstance(decision.get("decision_id"), str)
        or not _ID_RE.fullmatch(str(decision.get("decision_id", "")))
        or not isinstance(decision.get("reason"), str)
        or len(decision["reason"].strip()) < 20
    ):
        raise controller.PolicyError("P0 batch Owner decision does not authorize this exact closed contract")
    try:
        approved_at = datetime.fromisoformat(str(decision.get("approved_at_utc", "")).replace("Z", "+00:00"))
    except ValueError as exc:
        raise controller.PolicyError("P0 batch Owner decision timestamp is invalid") from exc
    if approved_at.tzinfo is None or approved_at.utcoffset() != timezone.utc.utcoffset(approved_at):
        raise controller.PolicyError("P0 batch Owner decision timestamp must use UTC")
    if (
        not isinstance(baseline, Mapping)
        or baseline.get("schema") != "qfsolver-development-node-ledger-v2"
        or baseline.get("mandate_id") != entry["development_mandate_id"]
    ):
        raise controller.PolicyError("frozen P0 baseline does not match the active Dynamics ledger contract")
    if baseline.get("predecessor") != entry["node_attempt_ledger"]["predecessor"]:
        raise controller.PolicyError("frozen P0 baseline is not linked to the active historical ledger")
    contract["_verified_path"] = str(contract_path)
    decision["_verified_path"] = str(decision_path)
    return contract, decision, baseline, store


def validate_ledger_transition(
    controller: Any,
    baseline: Mapping[str, Any],
    current: Mapping[str, Any],
    contract: Mapping[str, Any],
    decision: Mapping[str, Any],
    *,
    allow_reserved_ordinal: int | None = None,
) -> list[dict[str, Any] | None]:
    """Accept only the baseline plus one authorized ordered attempt per batch case."""
    mandate = contract["mandate_id"]
    prefix = f"{mandate}:wp12_dynamics:"
    targets = {case["nodeid"]: case for case in contract["ordered_cases"]}
    baseline_entries = baseline.get("entries", {})
    current_entries = current.get("entries", {})
    if not isinstance(baseline_entries, Mapping) or not isinstance(current_entries, Mapping):
        raise controller.PolicyError("P0 batch ledger entries are malformed")
    if current.get("schema") != "qfsolver-development-node-ledger-v2" or current.get("mandate_id") != mandate:
        raise controller.PolicyError("P0 batch ledger changed schema or mandate")
    if current.get("predecessor") != contract["initial_ledger"]["historical_predecessor"]:
        raise controller.PolicyError("P0 batch ledger predecessor changed")
    cases_by_key = {f"{prefix}{target}": case for target, case in targets.items()}
    for key in set(baseline_entries) | set(current_entries):
        old = baseline_entries.get(key, [])
        now = current_entries.get(key, [])
        if not isinstance(old, list) or not isinstance(now, list):
            raise controller.PolicyError("P0 batch ledger has a malformed entry")
        case = cases_by_key.get(key)
        if case is None:
            if now != old:
                raise controller.PolicyError("P0 batch detected a ledger mutation outside its exact case list")
            continue
        if now[: len(old)] != old or len(now) not in {len(old), len(old) + 1}:
            raise controller.PolicyError("P0 batch ledger contains a changed history, duplicate, or extra attempt")
        if len(now) == len(old):
            continue
        record = now[-1]
        ordinal = int(case["ordinal"])
        batch = record.get("batch") if isinstance(record, Mapping) else None
        if not isinstance(record, Mapping) or record.get("attempt") != len(old) + 1:
            raise controller.PolicyError("P0 batch attempt record has an invalid authorization identity")
        expected_batch_keys = {
            "campaign_id",
            "contract_path",
            "contract_sha256",
            "decision_path",
            "decision_id",
            "decision_sha256",
            "case_ordinal",
            "nodeid",
            "case_manifest_path",
            "case_manifest_sha256",
            "preflight_id",
            "preflight_receipt_sha256",
            "authorization_id",
            "prepared_manifest_path",
            "prepared_manifest_sha256",
        }
        if not isinstance(batch, Mapping) or set(batch) != expected_batch_keys:
            raise controller.PolicyError("P0 batch ledger attempt lacks complete campaign provenance")
        if (
            batch.get("campaign_id") != contract["campaign_id"]
            or batch.get("contract_path") != contract.get("_verified_path")
            or batch.get("contract_sha256") != contract.get("_verified_sha256")
            or batch.get("decision_path") != decision.get("_verified_path")
            or batch.get("decision_id") != decision["decision_id"]
            or batch.get("decision_sha256") != decision.get("_verified_sha256")
            or batch.get("case_ordinal") != ordinal
            or batch.get("nodeid") != case["nodeid"]
            or batch.get("case_manifest_sha256") != case["case_manifest"]["sha256"]
            or batch.get("case_manifest_path") != case["case_manifest"]["path"]
            or record.get("authorization_id") != batch.get("authorization_id")
            or not isinstance(batch.get("preflight_id"), str)
            or not _ID_RE.fullmatch(batch["preflight_id"])
            or not isinstance(batch.get("authorization_id"), str)
            or not _ID_RE.fullmatch(batch["authorization_id"])
            or not _SHA_RE.fullmatch(str(batch.get("contract_sha256", "")))
            or not _SHA_RE.fullmatch(str(batch.get("preflight_receipt_sha256", "")))
            or not _SHA_RE.fullmatch(str(batch.get("decision_sha256", "")))
            or not _SHA_RE.fullmatch(str(batch.get("prepared_manifest_sha256", "")))
            or not _SHA_RE.fullmatch(str(batch.get("case_manifest_sha256", "")))
            or batch.get("decision_sha256") != decision.get("_verified_sha256")
            or record.get("owner_decision_id") != decision["decision_id"]
            or record.get("source_fingerprint") != case["source_fingerprint"]
            or record.get("controller_fingerprint") != contract["controller"]["fingerprint"]
        ):
            raise controller.PolicyError("P0 batch ledger transition is not authorized by the frozen contract")
        if record.get("state") == "RESERVED":
            if allow_reserved_ordinal != ordinal:
                raise controller.PolicyError("P0 batch contains an unfinished consumed attempt; retry is forbidden")
        elif (
            not isinstance(record.get("state"), str)
            or not record.get("state")
            or not isinstance(record.get("finished_at_utc"), str)
            or not isinstance(record.get("post_source_fingerprint"), str)
        ):
            raise controller.PolicyError("P0 batch completed attempt lacks its terminal ledger fields")
    states: list[dict[str, Any] | None] = []
    found_gap = False
    for case in contract["ordered_cases"]:
        key = f"{prefix}{case['nodeid']}"
        old = baseline_entries.get(key, [])
        now = current_entries.get(key, [])
        record = now[-1] if len(now) == len(old) + 1 else None
        if record is None:
            found_gap = True
        elif found_gap:
            raise controller.PolicyError("P0 batch ledger contains an attempt after an unexecuted earlier case")
        states.append(record)
    return states


def _verify_archived_case(
    controller: Any,
    store: Path,
    batch_dir: Path,
    contract: Mapping[str, Any],
    decision: Mapping[str, Any],
    case: Mapping[str, Any],
    record: Mapping[str, Any],
    receipt_path: Path,
    receipt: Mapping[str, Any],
    expected_ledger_before: str | None,
) -> tuple[Path, str, str, Path | None]:
    """Recheck every file link needed to resume without reserving a second attempt."""
    receipt_fields = {
        "schema", "campaign_id", "contract_sha256", "decision_id", "decision_sha256", "ordinal", "nodeid",
        "case_manifest_sha256", "preflight_id", "preflight_receipt_path", "preflight_receipt_sha256",
        "prepared_manifest_path", "prepared_manifest_sha256", "authorized_manifest_path",
        "authorized_manifest_sha256", "run_record_path", "run_record_sha256", "ledger_sha256_before",
        "ledger_sha256_after", "attempt_state", "failure_classification", "batch_disposition",
        "junit_xml_path", "junit_xml_sha256", "exit_code",
    }
    ordinal = int(case["ordinal"])
    batch = record.get("batch")
    expected_receipt_path = batch_dir / "case-receipts" / f"case-{ordinal:02d}.json"
    if (
        receipt_path.resolve() != expected_receipt_path.resolve()
        or not _within(receipt_path, batch_dir)
        or not isinstance(receipt, Mapping)
        or set(receipt) != receipt_fields
        or receipt.get("schema") != BATCH_RECEIPT_SCHEMA
        or receipt.get("campaign_id") != contract["campaign_id"]
        or receipt.get("contract_sha256") != contract.get("_verified_sha256")
        or receipt.get("decision_id") != decision["decision_id"]
        or receipt.get("decision_sha256") != decision.get("_verified_sha256")
        or receipt.get("ordinal") != ordinal
        or receipt.get("nodeid") != case["nodeid"]
        or receipt.get("case_manifest_sha256") != case["case_manifest"]["sha256"]
        or receipt.get("ledger_sha256_before") != expected_ledger_before
        or receipt.get("attempt_state") != record.get("state")
        or not isinstance(batch, Mapping)
        or batch.get("campaign_id") != contract["campaign_id"]
        or batch.get("case_ordinal") != ordinal
        or batch.get("nodeid") != case["nodeid"]
        or batch.get("decision_id") != decision["decision_id"]
        or batch.get("case_manifest_sha256") != case["case_manifest"]["sha256"]
        or receipt.get("preflight_id") != batch.get("preflight_id")
        or receipt.get("preflight_receipt_sha256") != batch.get("preflight_receipt_sha256")
        or receipt.get("prepared_manifest_path") != batch.get("prepared_manifest_path")
        or receipt.get("prepared_manifest_sha256") != batch.get("prepared_manifest_sha256")
        or record.get("owner_decision_id") != decision["decision_id"]
        or record.get("authorization_id") != batch.get("authorization_id")
    ):
        raise controller.PolicyError("completed P0 batch receipt and ledger provenance do not agree")

    manifest_root = store / "authorizations" / "wp12_dynamics"
    auth_id = batch.get("authorization_id")
    if not isinstance(auth_id, str) or not _ID_RE.fullmatch(auth_id):
        raise controller.PolicyError("completed P0 batch attempt has an invalid authorization ID")
    prepared_path = manifest_root / f"{auth_id}.json"
    authorized_path = manifest_root / "owner-authorized" / f"{auth_id}.json"
    if (
        Path(str(receipt["prepared_manifest_path"])).resolve() != prepared_path.resolve()
        or Path(str(receipt["authorized_manifest_path"])).resolve() != authorized_path.resolve()
        or not _within(prepared_path, manifest_root)
        or not _within(authorized_path, manifest_root)
        or not prepared_path.is_file()
        or not authorized_path.is_file()
        or _raw_sha256(prepared_path) != receipt["prepared_manifest_sha256"]
        or _raw_sha256(authorized_path) != receipt["authorized_manifest_sha256"]
    ):
        raise controller.PolicyError("completed P0 batch prepared or authorized manifest changed")
    prepared_manifest = _read_json(prepared_path)
    authorized_manifest = _read_json(authorized_path)
    expected_preflight = {
        "preflight_id": receipt["preflight_id"],
        "receipt_path": receipt["preflight_receipt_path"],
        "receipt_sha256": receipt["preflight_receipt_sha256"],
    }
    if (
        not isinstance(prepared_manifest, Mapping)
        or prepared_manifest.get("state") != "PREPARED_NOT_AUTHORIZED"
        or prepared_manifest.get("execution_authorized") is not False
        or prepared_manifest.get("do_not_execute") is not True
        or prepared_manifest.get("authorization_id") != auth_id
        or prepared_manifest.get("target") != case["nodeid"]
        or prepared_manifest.get("preflight") != expected_preflight
        or not isinstance(authorized_manifest, Mapping)
        or authorized_manifest.get("state") != "OWNER_AUTHORIZED"
        or authorized_manifest.get("execution_authorized") is not True
        or authorized_manifest.get("do_not_execute") is not False
        or authorized_manifest.get("authorization_id") != auth_id
        or authorized_manifest.get("target") != case["nodeid"]
        or authorized_manifest.get("preflight") != expected_preflight
        or authorized_manifest.get("batch_authorization") != dict(batch)
        or not isinstance(authorized_manifest.get("owner_decision"), Mapping)
        or authorized_manifest["owner_decision"].get("decision_id") != decision["decision_id"]
    ):
        raise controller.PolicyError("completed P0 batch execution manifest no longer matches its receipt")

    preflight_id = receipt["preflight_id"]
    if not isinstance(preflight_id, str) or not re.fullmatch(r"pf-[0-9a-f]{12}", preflight_id):
        raise controller.PolicyError("completed P0 batch has an invalid preflight ID")
    preflight_dir = store / "worktrees" / "wp12_dynamics" / "preflight" / preflight_id
    preflight_path = preflight_dir / "preflight.json"
    preflight_sha_path = preflight_dir / "preflight.sha256.json"
    if (
        Path(str(receipt["preflight_receipt_path"])).resolve() != preflight_path.resolve()
        or not _within(preflight_path, store)
        or not preflight_path.is_file()
        or not preflight_sha_path.is_file()
        or _raw_sha256(preflight_path) != receipt["preflight_receipt_sha256"]
    ):
        raise controller.PolicyError("completed P0 batch collect-only preflight receipt changed")
    preflight = _read_json(preflight_path)
    sidecar = _read_json(preflight_sha_path)
    attempt_ledger = preflight.get("attempt_ledger") if isinstance(preflight, Mapping) else None
    registration = preflight.get("registration") if isinstance(preflight, Mapping) else None
    budgets = preflight.get("budgets") if isinstance(preflight, Mapping) else None
    historical_predecessor = contract["initial_ledger"]["historical_predecessor"]
    if (
        not isinstance(preflight, Mapping)
        or not isinstance(sidecar, Mapping)
        or sidecar.get("sha256") != receipt["preflight_receipt_sha256"]
        or preflight.get("schema") != "qfsolver-development-wp12-dynamics-preflight-v2"
        or preflight.get("state") != "PREFLIGHT_PASS"
        or preflight.get("mode") != "DEVELOPMENT_AUTONOMOUS"
        or preflight.get("mandate_id") != contract["mandate_id"]
        or preflight.get("worktree_id") != "wp12_dynamics"
        or preflight.get("target") != case["nodeid"]
        or preflight.get("preflight_id") != preflight_id
        or preflight.get("phase") != "PYTEST_COLLECT_ONLY"
        or preflight.get("bodies_executed") is not False
        or preflight.get("attempt_reserved") is not False
        or preflight.get("ledger_touched") is not False
        or preflight.get("identity") != case["identity"]
        or preflight.get("identity_after") != case["identity"]
        or preflight.get("source_fingerprint") != case["source_fingerprint"]
        or preflight.get("source_fingerprint_after") != case["source_fingerprint"]
        or preflight.get("controller_provenance") != contract["controller"]["provenance"]
        or preflight.get("controller_provenance_after") != contract["controller"]["provenance"]
        or preflight.get("solver_origin_observed") != preflight.get("solver_origin_expected")
        or preflight.get("collected_nodeids") != [case["nodeid"]]
        or preflight.get("skip_markers") != []
        or preflight.get("return_code") != 0
        or not isinstance(attempt_ledger, Mapping)
        or attempt_ledger.get("touched") is not False
        or attempt_ledger.get("path") != contract["initial_ledger"]["path"]
        or attempt_ledger.get("predecessor") != historical_predecessor
        or attempt_ledger.get("predecessor_sha256_before")
        != contract["initial_ledger"]["historical_predecessor_sha256"]
        or attempt_ledger.get("predecessor_sha256_after")
        != contract["initial_ledger"]["historical_predecessor_sha256"]
        or attempt_ledger.get("sha256_before") != expected_ledger_before
        or attempt_ledger.get("sha256_after") != expected_ledger_before
        or attempt_ledger.get("sha256_after") != receipt["ledger_sha256_before"]
        or not isinstance(registration, Mapping)
        or registration.get("target") != case["nodeid"]
        or registration.get("source_fingerprint") != case["source_fingerprint"]
        or registration.get("selected_dofs") != case["selection"]["selected_dofs"]
        or registration.get("timeout_seconds") != case["budget"]["timeout_seconds"]
        or not isinstance(budgets, Mapping)
        or budgets.get("timeout_seconds") != case["budget"]["timeout_seconds"]
    ):
        raise controller.PolicyError("completed P0 batch preflight no longer attests the ledger state before reservation")

    case_path = Path(case["case_manifest"]["path"]).resolve(strict=True)
    if not _within(case_path, controller.ROOT.resolve()) or _raw_sha256(case_path) != case["case_manifest"]["sha256"]:
        raise controller.PolicyError("completed P0 batch scientific case manifest changed")
    run_path = _run_record_path(controller, store, record)
    if (
        Path(str(receipt["run_record_path"])).resolve() != run_path.resolve()
        or not run_path.is_file()
        or _raw_sha256(run_path) != receipt["run_record_sha256"]
    ):
        raise controller.PolicyError("completed P0 batch run archive changed")
    run_record = _read_json(run_path)
    if (
        not isinstance(run_record, Mapping)
        or run_record.get("batch_context") != dict(batch)
        or run_record.get("state") != record.get("state")
        or run_record.get("target") != [case["nodeid"]]
        or run_record.get("identity") != case["identity"]
        or run_record.get("source_fingerprint") != case["source_fingerprint"]
        or run_record.get("controller_provenance") != contract["controller"]["provenance"]
        or not isinstance(run_record.get("execution_manifest"), Mapping)
        or run_record["execution_manifest"].get("path") != str(authorized_path.resolve())
        or run_record["execution_manifest"].get("sha256") != receipt["authorized_manifest_sha256"]
    ):
        raise controller.PolicyError("completed P0 batch run archive does not match its ledger record")
    classification, disposition, junit_path = _classify_batch_result(
        controller, run_record, run_path, case["nodeid"]
    )
    if (
        receipt.get("failure_classification") != classification
        or receipt.get("batch_disposition") != disposition
        or receipt.get("junit_xml_path") != (str(junit_path) if junit_path else None)
    ):
        raise controller.PolicyError("completed P0 batch result classification changed")
    junit_sha = receipt.get("junit_xml_sha256")
    if junit_path is not None:
        if (
            not _within(junit_path, run_path.parent)
            or not junit_path.is_file()
            or not _SHA_RE.fullmatch(str(junit_sha or ""))
            or _raw_sha256(junit_path) != junit_sha
        ):
            raise controller.PolicyError("completed P0 batch JUnit evidence is missing or changed")
    elif junit_sha is not None:
        raise controller.PolicyError("completed P0 batch receipt has an unbound JUnit digest")
    return run_path, classification, disposition, junit_path


def run_batch(
    controller: Any,
    contract_path: Path,
    contract_sha256: str,
    decision_path: Path,
    decision_sha256: str,
    *,
    resume: bool = False,
) -> dict[str, Any]:
    """Run each authorized node sequentially with a fresh exact collect-only preflight."""
    contract, decision, baseline, store = _validated_authorization(
        controller, contract_path, contract_sha256, decision_path, decision_sha256
    )
    policy = controller.load_policy()
    ledger_path, ledger_lock, _mandate, _predecessor = controller._node_ledger_context(
        policy, store, "wp12_dynamics"
    )
    batch_dir = Path(contract_path).resolve().parent
    progress_path = batch_dir / "progress.json"
    previous_progress = _read_json(progress_path) if progress_path.is_file() else None
    if previous_progress is not None:
        if not resume:
            raise controller.PolicyError("P0 batch progress exists; use controlled resume after verifying the ledger")
        if (
            not isinstance(previous_progress, Mapping)
                    or set(previous_progress) != {
                        "schema", "campaign_id", "contract_sha256", "decision_id", "decision_sha256",
                        "completed_cases", "ledger_sha256", "updated_at_utc",
                    }
            or previous_progress.get("schema") != "qfsolver-wp12a-p0-batch-progress-v1"
            or previous_progress.get("campaign_id") != contract["campaign_id"]
            or previous_progress.get("contract_sha256") != contract_sha256
            or previous_progress.get("decision_sha256") != decision_sha256
            or previous_progress.get("decision_id") != decision["decision_id"]
        ):
            raise controller.PolicyError("P0 batch resume identity differs from the frozen contract or decision")

    results: list[dict[str, Any]] = []
    batch_lock = ledger_path.with_suffix(".batch.lock")
    with controller._exclusive_file_lock(batch_lock):
        previous_batch_lock_state = getattr(controller._WP12A_BATCH_LOCK_LOCAL, "held", False)
        controller._WP12A_BATCH_LOCK_LOCAL.held = True
        try:
            current = _ledger_payload(controller, ledger_path, contract["initial_ledger"]["historical_predecessor"])
            contract["_verified_sha256"] = contract_sha256
            decision["_verified_sha256"] = decision_sha256
            states = validate_ledger_transition(controller, baseline, current, contract, decision)
            first_incomplete = next((i for i, state in enumerate(states) if state is None), len(states))
            progress_cases = previous_progress.get("completed_cases", []) if previous_progress is not None else []
            if not isinstance(progress_cases, list) or len(progress_cases) > first_incomplete:
                raise controller.PolicyError("P0 batch checkpoint is inconsistent with the consumed ledger prefix")
            current_ledger_sha = _raw_sha256(ledger_path) if ledger_path.is_file() else None
            if first_incomplete == 0 and current_ledger_sha != contract["initial_ledger"]["sha256"]:
                raise controller.PolicyError("Dynamics ledger raw identity changed before the first P0 batch attempt")
            if first_incomplete > 0 and not resume:
                raise controller.PolicyError("P0 batch has prior completed attempts; controlled resume must be explicit")

            # A reservation left unfinished by interruption is consumed. It is never retried.
            for index, state in enumerate(states):
                if state is not None and state.get("state") == "RESERVED":
                    raise controller.PolicyError(
                        f"P0 batch case {index + 1} has a consumed unfinished attempt; no retry or continuation is permitted"
                    )
            expected_ledger_before = contract["initial_ledger"]["sha256"]
            verified_classifications: list[str] = []
            for index in range(first_incomplete):
                case = contract["ordered_cases"][index]
                record = states[index]
                assert record is not None
                receipt_path = batch_dir / "case-receipts" / f"case-{index + 1:02d}.json"
                if not _within(receipt_path, batch_dir) or not receipt_path.is_file():
                    raise controller.PolicyError("completed P0 batch attempt has no immutable case receipt")
                receipt = _read_json(receipt_path)
                result_path, expected_classification, expected_disposition, _junit_path = _verify_archived_case(
                    controller,
                    store,
                    batch_dir,
                    contract,
                    decision,
                    case,
                    record,
                    receipt_path,
                    receipt,
                    expected_ledger_before,
                )
                verified_classifications.append(expected_classification)
                receipt_sha = _raw_sha256(receipt_path)
                if index < len(progress_cases):
                    progress_item = progress_cases[index]
                    if (
                        not isinstance(progress_item, Mapping)
                        or set(progress_item) != {"ordinal", "state", "receipt", "receipt_sha256"}
                        or progress_item.get("ordinal") != index + 1
                        or progress_item.get("state") != record.get("state")
                        or progress_item.get("receipt") != str(receipt_path)
                        or progress_item.get("receipt_sha256") != receipt_sha
                    ):
                        raise controller.PolicyError("P0 batch progress checkpoint differs from its immutable case receipt")
                expected_ledger_before = receipt["ledger_sha256_after"]
                if receipt["batch_disposition"] == "STOP":
                    if any(state is not None for state in states[index + 1 :]):
                        raise controller.PolicyError("P0 batch ledger contains an attempt after an approved stop condition")
                    if expected_ledger_before != (_raw_sha256(ledger_path) if ledger_path.is_file() else None):
                        raise controller.PolicyError("stopped P0 batch receipt does not terminate at the current ledger state")
                    if previous_progress is not None:
                        expected_progress_ledger = (
                            _read_json(
                                batch_dir / "case-receipts" / f"case-{len(progress_cases):02d}.json"
                            ).get("ledger_sha256_after")
                            if progress_cases
                            else contract["initial_ledger"]["sha256"]
                        )
                        if previous_progress.get("ledger_sha256") != expected_progress_ledger:
                            raise controller.PolicyError(
                                "P0 batch progress ledger checkpoint does not match its completed prefix"
                            )
                    return {
                        "state": "BATCH_STOPPED_BY_CASE_RESULT",
                        "results": [
                            {"ordinal": prior + 1, "state": states[prior]["state"], "receipt": str(
                                batch_dir / "case-receipts" / f"case-{prior + 1:02d}.json"
                            )}
                            for prior in range(index + 1)
                        ],
                    }
            if previous_progress is not None:
                expected_progress_ledger = (
                    json.loads((batch_dir / "case-receipts" / f"case-{len(progress_cases):02d}.json").read_text(
                        encoding="utf-8"
                    )).get("ledger_sha256_after")
                    if progress_cases
                    else contract["initial_ledger"]["sha256"]
                )
                if previous_progress.get("ledger_sha256") != expected_progress_ledger:
                    raise controller.PolicyError("P0 batch progress ledger checkpoint does not match its completed prefix")
            if first_incomplete and expected_ledger_before != (_raw_sha256(ledger_path) if ledger_path.is_file() else None):
                raise controller.PolicyError("completed P0 batch receipts do not terminate at the current ledger state")
            for index, case in enumerate(contract["ordered_cases"]):
                if index < first_incomplete:
                    record = states[index]
                    assert record is not None
                    receipt_path = batch_dir / "case-receipts" / f"case-{index + 1:02d}.json"
                    results.append(
                        {
                            "ordinal": index + 1,
                            "state": record["state"],
                            "receipt": str(receipt_path),
                            "receipt_sha256": _raw_sha256(receipt_path),
                        }
                    )
                    if verified_classifications[index] not in case["continue_after"]:
                        raise controller.PolicyError("prior P0 batch outcome does not permit continuation")
                    continue

                _validate_live_case(controller, policy, contract, case)
                latest = _ledger_payload(controller, ledger_path, contract["initial_ledger"]["historical_predecessor"])
                states = validate_ledger_transition(controller, baseline, latest, contract, decision)
                _validate_remaining_budget(controller, policy, store, latest, case["nodeid"])
                preflight = controller.preflight_wp12_dynamics_pytest(case["nodeid"], policy=policy)
                if preflight.get("state") != "PREFLIGHT_PASS" or preflight.get("bodies_executed") is not False:
                    raise controller.PolicyError("just-in-time collect-only preflight did not pass cleanly")
                preflight_id = preflight["preflight_id"]
                receipt_path, receipt_sha = controller._validate_wp12_dynamics_preflight_receipt(
                    store,
                    preflight_id,
                    target=case["nodeid"],
                    identity=case["identity"],
                    source_fingerprint=case["source_fingerprint"],
                    controller_provenance=contract["controller"]["provenance"],
                    policy=policy,
                )
                if receipt_sha != preflight.get("receipt_sha256"):
                    raise controller.PolicyError("JIT preflight result and archived receipt SHA-256 disagree")
                ledger_before = _raw_sha256(ledger_path) if ledger_path.is_file() else None
                receipt = _read_json(receipt_path)
                if receipt["attempt_ledger"]["sha256_after"] != ledger_before:
                    raise controller.PolicyError("ledger changed after JIT preflight; batch stopped before reservation")

                auth_id = f"wp12a-p0-{hashlib.sha256(contract['campaign_id'].encode()).hexdigest()[:8]}-{index + 1:02d}-{uuid.uuid4().hex[:6]}"
                prepared = controller.prepare_wp12_execution_manifest(
                    "wp12_dynamics", case["nodeid"], auth_id, preflight_id=preflight_id
                )
                prepared_path = Path(prepared["path"]).resolve(strict=True)
                prepared_sha = _raw_sha256(prepared_path)
                execution_manifest = _read_json(prepared_path)
                batch_binding = {
                    "campaign_id": contract["campaign_id"],
                    "contract_path": contract["_verified_path"],
                    "contract_sha256": contract_sha256,
                    "decision_path": decision["_verified_path"],
                    "decision_id": decision["decision_id"],
                    "decision_sha256": decision_sha256,
                    "case_ordinal": index + 1,
                    "nodeid": case["nodeid"],
                    "case_manifest_path": case["case_manifest"]["path"],
                    "case_manifest_sha256": case["case_manifest"]["sha256"],
                    "preflight_id": preflight_id,
                    "preflight_receipt_sha256": receipt_sha,
                    "authorization_id": auth_id,
                    "prepared_manifest_path": str(prepared_path),
                    "prepared_manifest_sha256": prepared_sha,
                }
                execution_manifest.update(
                    {
                        "state": "OWNER_AUTHORIZED",
                        "execution_authorized": True,
                        "do_not_execute": False,
                        "batch_authorization": batch_binding,
                        "owner_decision": {
                            "status": "APPROVED",
                            "decision_id": decision["decision_id"],
                            "approved_by": "Owner",
                            "approved_at_utc": decision["approved_at_utc"],
                            "reason": decision["reason"],
                        },
                    }
                )
                # The shared controller accepts execution manifests only below its
                # registered per-worktree authorization root. Keep that live gate
                # separate from the immutable batch archive and bind it by digest.
                authorization_root = (
                    Path(policy["worktrees"]["wp12_dynamics"]["evidence_root"]).resolve()
                    / "authorizations"
                    / "wp12_dynamics"
                )
                authorized_path = authorization_root / "owner-authorized" / f"{auth_id}.json"
                controller._atomic_json_new(authorized_path, execution_manifest)
                authorized_sha = _raw_sha256(authorized_path)
                series_id = f"dev-p0-{hashlib.sha256(contract['campaign_id'].encode()).hexdigest()[:8]}-{index + 1:02d}-{preflight_id[-6:]}"
                result, exit_code = controller.run_pytest(
                    "fem_exploratory",
                    case["nodeid"],
                    series_id,
                    worktree_id="wp12_dynamics",
                    reason=f"Owner-authorized WP12-A P0 batch {contract['campaign_id']} case {index + 1}.",
                    preflight_id=preflight_id,
                    execution_manifest=authorized_path,
                    batch_context=batch_binding,
                )
                run_path = Path(result.get("record", "")).resolve(strict=True)
                run_sha = _raw_sha256(run_path)
                failure_classification, batch_disposition, junit_path = _classify_batch_result(
                    controller, result, run_path, case["nodeid"]
                )
                after = _ledger_payload(
                    controller, ledger_path, contract["initial_ledger"]["historical_predecessor"], allow_reserved=True
                )
                contract["_verified_sha256"] = contract_sha256
                decision["_verified_sha256"] = decision_sha256
                resulting_states = validate_ledger_transition(controller, baseline, after, contract, decision)
                ledger_state = resulting_states[index]
                if ledger_state is None or ledger_state.get("batch") != batch_binding:
                    raise controller.PolicyError("P0 batch ledger did not record this exact authorized attempt")
                case_receipt = {
                    "schema": BATCH_RECEIPT_SCHEMA,
                    "campaign_id": contract["campaign_id"],
                    "contract_sha256": contract_sha256,
                    "decision_id": decision["decision_id"],
                    "decision_sha256": decision_sha256,
                    "ordinal": index + 1,
                    "nodeid": case["nodeid"],
                    "case_manifest_sha256": case["case_manifest"]["sha256"],
                    "preflight_id": preflight_id,
                    "preflight_receipt_path": str(receipt_path),
                    "preflight_receipt_sha256": receipt_sha,
                    "prepared_manifest_path": str(prepared_path),
                    "prepared_manifest_sha256": prepared_sha,
                    "authorized_manifest_path": str(authorized_path),
                    "authorized_manifest_sha256": authorized_sha,
                    "run_record_path": str(run_path),
                    "run_record_sha256": run_sha,
                    "ledger_sha256_before": ledger_before,
                    "ledger_sha256_after": _raw_sha256(ledger_path),
                    "attempt_state": result["state"],
                    "failure_classification": failure_classification,
                    "batch_disposition": batch_disposition,
                    "junit_xml_path": str(junit_path) if junit_path is not None else None,
                    "junit_xml_sha256": _raw_sha256(junit_path) if junit_path is not None else None,
                    "exit_code": exit_code,
                }
                case_receipt_path = batch_dir / "case-receipts" / f"case-{index + 1:02d}.json"
                controller._atomic_json_new(case_receipt_path, case_receipt)
                case_receipt_sha = _raw_sha256(case_receipt_path)
                results.append(
                    {
                        "ordinal": index + 1,
                        "state": result["state"],
                        "receipt": str(case_receipt_path),
                        "receipt_sha256": case_receipt_sha,
                    }
                )
                progress = {
                    "schema": "qfsolver-wp12a-p0-batch-progress-v1",
                    "campaign_id": contract["campaign_id"],
                    "contract_sha256": contract_sha256,
                    "decision_id": decision["decision_id"],
                    "decision_sha256": decision_sha256,
                    "completed_cases": results,
                    "ledger_sha256": _raw_sha256(ledger_path),
                    "updated_at_utc": datetime.now(timezone.utc).isoformat(),
                }
                controller._atomic_json(progress_path, progress)
                if batch_disposition == "STOP":
                    return {"state": "BATCH_STOPPED_BY_CASE_RESULT", "results": results}
            return {"state": "BATCH_COMPLETED", "results": results}
        finally:
            controller._WP12A_BATCH_LOCK_LOCAL.held = previous_batch_lock_state


def _validate_live_case(controller: Any, policy: Mapping[str, Any], contract: Mapping[str, Any], case: Mapping[str, Any]) -> None:
    target = case["nodeid"]
    controller.resolve_targets("fem_exploratory", target, policy, worktree_id="wp12_dynamics")
    entry, _root, _source_root, identity, source_fingerprint = controller._registered_worktree(
        "wp12_dynamics", target, policy
    )
    registration = controller._wp12_active_registration("wp12_dynamics", target, entry, source_fingerprint)
    if identity != case["identity"] or source_fingerprint != case["source_fingerprint"]:
        raise controller.PolicyError("P0 batch stopped because source identity changed after Owner authorization")
    if target not in controller.WP12_DYNAMICS_P0_BATCH_NODEIDS:
        raise controller.PolicyError("P0 batch case is outside the fixed scientific candidate list")
    case_path = Path(case["case_manifest"]["path"]).resolve(strict=True)
    if not _within(case_path, controller.ROOT.resolve()) or _raw_sha256(case_path) != case["case_manifest"]["sha256"]:
        raise controller.PolicyError("P0 case manifest changed after Owner authorization")
    expected_selection = {
        "selected_dofs": registration["selected_dofs"],
        "timeout_seconds": registration["timeout_seconds"],
        "selection_basis": registration["selection_basis"],
        "timeout_reason": registration["timeout_reason"],
    }
    expected_budget = {
        "timeout_seconds": registration["timeout_seconds"],
        **{key: value for key, value in entry["budgets"].items() if key != "timeout_seconds"},
    }
    if case.get("selection") != expected_selection or case.get("budget") != expected_budget:
        raise controller.PolicyError("P0 batch stopped because the registered DDL or resource budget changed")
    if controller._stable_fingerprint(controller._controller_provenance()) != contract["controller"]["fingerprint"]:
        raise controller.PolicyError("P0 batch stopped because controller provenance changed")


def _validate_remaining_budget(
    controller: Any,
    policy: Mapping[str, Any],
    store: Path,
    current: Mapping[str, Any],
    target: str,
) -> None:
    entry = policy["worktrees"]["wp12_dynamics"]
    _ledger_path, _ledger_lock, mandate_id, predecessor = controller._node_ledger_context(
        policy, store, "wp12_dynamics"
    )
    if predecessor is None:
        raise controller.PolicyError("P0 batch lost its historical ledger predecessor")
    _predecessor_path, _historical, inherited_counts, inherited_total = controller._wp12_dynamics_predecessor_history(
        store, predecessor, allowed_nodeids=set(entry["allowed_nodeids"])
    )
    controller._validate_wp12_dynamics_ledger(
        current,
        mandate_id=mandate_id,
        predecessor=predecessor,
        allowed_nodeids=set(entry["allowed_nodeids"]),
        predecessor_counts=inherited_counts,
        predecessor_total=inherited_total,
        attempt_limit=int(entry["attempt_limit_per_nodeid"]),
        total_limit=int(entry["max_total_attempts"]),
    )
    prefix = f"{mandate_id}:wp12_dynamics:"
    attempts = sum(
        len(items)
        for key, items in current.get("entries", {}).items()
        if key.startswith(prefix) and isinstance(items, list)
    )
    if inherited_total + attempts >= int(entry["max_total_attempts"]):
        raise controller.PolicyError("WP12-A P0 batch mission attempt budget is exhausted")
    key = f"{mandate_id}:wp12_dynamics:{target}"
    current_attempts = current.get("entries", {}).get(key, [])
    if inherited_counts.get(target, 0) + len(current_attempts) >= int(entry["attempt_limit_per_nodeid"]):
        raise controller.PolicyError("WP12-A P0 batch case attempt budget is exhausted")


def _run_record_path(controller: Any, store: Path, record: Mapping[str, Any]) -> Path:
    series_id = record.get("series_id")
    if not isinstance(series_id, str) or not controller.SERIES_RE.fullmatch(series_id):
        raise controller.PolicyError("P0 batch ledger has an invalid series identity")
    return controller._series_root(store, "fem_exploratory", "wp12_dynamics") / series_id / "attempt-0001" / "run.json"


def _classify_batch_result(controller: Any, result: Mapping[str, Any], run_path: Path, target: str) -> tuple[str, str, Path | None]:
    """Only a single assertion failure for the exact collected test is continuable."""
    state = result.get("state")
    if state not in {"PASS", "PYTEST_FAILED"}:
        return "UNCLASSIFIED_OR_INFRASTRUCTURE_FAILURE", "STOP", None
    junit_path = run_path.parent / "output" / "pytest-results.xml"
    if not junit_path.is_file():
        return "UNCLASSIFIED_OR_INFRASTRUCTURE_FAILURE", "STOP", None
    try:
        root = controller.ET.parse(junit_path).getroot()
        testcases = root.findall(".//testcase")
    except (OSError, controller.ET.ParseError):
        return "UNCLASSIFIED_OR_INFRASTRUCTURE_FAILURE", "STOP", junit_path
    expected_name = target.split("::", maxsplit=1)[1]
    if len(testcases) != 1 or testcases[0].get("name") != expected_name:
        return "UNCLASSIFIED_OR_INFRASTRUCTURE_FAILURE", "STOP", junit_path
    testcase = testcases[0]
    if testcase.find("skipped") is not None or testcase.find("error") is not None:
        return "UNCLASSIFIED_OR_INFRASTRUCTURE_FAILURE", "STOP", junit_path
    failures = testcase.findall("failure")
    if state == "PASS" and not failures:
        return "PASS", "CONTINUE", junit_path
    if (
        state == "PYTEST_FAILED"
        and len(failures) == 1
        and failures[0].get("type") == "AssertionError"
        and testcase.find("error") is None
    ):
        return "SCIENTIFIC_ASSERTION_FAILED", "CONTINUE", junit_path
    return "UNCLASSIFIED_OR_INFRASTRUCTURE_FAILURE", "STOP", junit_path
