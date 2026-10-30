"""Synthetic tests for the prospective nine-case VV3D remainder only."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import threading
import time

import pytest

from scripts import wp12_vv3d_family_remainder_contract as contract_module
from scripts import wp12_vv3d_family_remainder_ledger as ledger_module
from scripts import development_autonomous as controller_module
from scripts.wp12_vv3d_ledger import RunBinding, RunnerCaseBinding


def contract_fixture() -> dict:
    cases = []
    for case_id in contract_module.CASE_IDS:
        family = case_id.split("-")[1]
        criteria_path, criteria_sha = contract_module.CRITERIA_BINDINGS[family]
        cases.append({
            "case_id": case_id,
            "nodeid": contract_module.expected_nodeid(case_id),
            "mesh_sha256": hashlib.sha256(f"mesh:{case_id}".encode()).hexdigest(),
            "selected_dofs": contract_module.SELECTED_DOFS[case_id],
            "timeout_seconds": 1200,
            "rss_soft_limit_mib": 4096,
            "archive_size_limit_mib": 256,
            "max_attempts": 1,
            "status": "PREPARED_NOT_AUTHORIZED",
            "criteria_path": criteria_path,
            "criteria_file_sha256": criteria_sha,
            "oracle_path": contract_module.ORACLE_BINDING[0],
            "oracle_sha256": contract_module.ORACLE_BINDING[1],
        })
    return {
        "schema": contract_module.CONTRACT_SCHEMA,
        "campaign_id": contract_module.CAMPAIGN_ID,
        "scope_id": contract_module.SCOPE_ID,
        "scientific_fingerprint": "1" * 64,
        "controller_fingerprint": "2" * 64,
        "predecessor_ledgers": contract_module.predecessor_contract_bindings(),
        "historical_tet4_review": copy.deepcopy(contract_module.HISTORICAL_TET4_REVIEW),
        "budget": dict(contract_module.BUDGET),
        "case_ids": list(contract_module.CASE_IDS),
        "excluded_case_ids": list(contract_module.EXCLUDED_CASE_IDS),
        "cases": cases,
        "excluded_routes": ["H1", "QLOAD", "QPOST"],
        "stop_policy": dict(contract_module.STOP_POLICY),
        "status": "PREPARED_NOT_AUTHORIZED",
    }


def _write_synthetic_predecessors(tmp_path: Path) -> tuple[dict, ...]:
    specs = []
    for spec_index, pinned in enumerate(contract_module.PREDECESSOR_LEDGER_BINDINGS):
        records = []
        for attempt_index, (status, elapsed) in enumerate(zip(
            pinned["statuses"], pinned["elapsed_seconds_by_attempt"], strict=True,
        ), 1):
            run_id = f"pred-{spec_index}-{attempt_index}"
            case_id = f"VV3D-PRED-{spec_index}-{attempt_index}"
            identity = {
                "campaign_id": pinned["campaign_id"],
                "ledger_scope_id": pinned["ledger_scope_id"],
                "run_id": run_id,
                "case_id": case_id,
            }
            records.extend([
                {"event": "ATTEMPT_STARTED", **identity},
                {"event": "ATTEMPT_FINISHED", **identity, "status": status, "elapsed_seconds": elapsed},
            ])
        raw = b"".join(
            json.dumps(record, sort_keys=True, separators=(",", ":")).encode() + b"\n"
            for record in records
        )
        scope_root = tmp_path / f"predecessor-{spec_index}"
        scope_root.mkdir()
        path = scope_root / "ledger.jsonl"
        path.write_bytes(raw)
        specs.append({**pinned, "path": str(path), "sha256": hashlib.sha256(raw).hexdigest()})
    return tuple(specs)


def make_ledger(tmp_path: Path, specs: tuple[dict, ...] | None = None) -> ledger_module.FamilyRemainderLedger:
    evidence_root = tmp_path / "family-remainder-evidence"
    evidence_root.mkdir(exist_ok=True)
    return ledger_module.FamilyRemainderLedger(
        evidence_root / "node-attempt-ledger.jsonl",
        allowed_root=evidence_root,
        _predecessor_specs=specs or _write_synthetic_predecessors(tmp_path),
    )


def runner_bindings(case_index: int, evidence_root: Path, label: str) -> tuple[RunBinding, RunnerCaseBinding]:
    case_id = contract_module.CASE_IDS[case_index]
    binding = RunBinding(
        contract_sha256="a" * 64,
        decision_id="owner-decision-2026-01",
        decision_sha256="b" * 64,
        manifest_sha256=hashlib.sha256(f"manifest:{label}".encode()).hexdigest(),
        preflight_sha256=hashlib.sha256(f"preflight:{label}".encode()).hexdigest(),
    )
    case = RunnerCaseBinding(
        case_id=case_id,
        nodeid=contract_module.CASE_NODEIDS[case_index],
        attempt_id=f"attempt-{case_id}",
        authorization_id="owner-auth-2026-01",
        source_fingerprint="1" * 64,
        controller_fingerprint="2" * 64,
        selected_dofs=contract_module.SELECTED_DOFS[case_id],
        timeout_seconds=1200,
        rss_soft_limit_mib=4096,
        archive_limit_mib=256,
        evidence_root=str(evidence_root),
    )
    return binding, case


def start_case(ledger: ledger_module.FamilyRemainderLedger, tmp_path: Path, index: int, label: str) -> str:
    binding, case = runner_bindings(index, ledger.allowed_root, label)
    receipt = tmp_path / "family-remainder-evidence" / "receipts" / f"{label}.json"
    result = ledger.start_runner_attempt(binding=binding, case=case, receipt_path=receipt)
    return result["reservation_id"]


def test_contract_accepts_exact_nine_case_scope_and_owner_decision() -> None:
    contract = contract_fixture()
    digest = contract_module.validate_contract(
        contract, scientific_fingerprint="1" * 64, controller_fingerprint="2" * 64,
    )
    assert digest == contract_module.canonical_sha256(contract)
    assert contract["case_ids"] == [
        "VV3D-TET10-L1", "VV3D-TET10-L2", "VV3D-TET10-L3",
        "VV3D-HEX8-L1", "VV3D-HEX8-L2", "VV3D-HEX8-L3",
        "VV3D-HEX20-L1", "VV3D-HEX20-L2", "VV3D-HEX20-L3",
    ]
    decision = {
        "schema": contract_module.DECISION_SCHEMA,
        "campaign_id": contract_module.CAMPAIGN_ID,
        "scope_id": contract_module.SCOPE_ID,
        "decision_id": "owner-decision-2026-01",
        "approved_by": "Owner",
        "approved_at_utc": "2026-10-30T12:00:00Z",
        "contract_sha256": digest,
        "case_ids": list(contract_module.CASE_IDS),
        "scientific_fingerprint": "1" * 64,
        "controller_fingerprint": "2" * 64,
        "budget": dict(contract_module.BUDGET),
        "status": "APPROVED",
    }
    assert contract_module.validate_owner_decision(
        decision, contract_sha256=digest,
        scientific_fingerprint="1" * 64, controller_fingerprint="2" * 64,
    ) == contract_module.canonical_sha256(decision)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value["case_ids"].pop(),
        lambda value: value["cases"].pop(0),
        lambda value: value["cases"][0].update(case_id="VV3D-TET4-L1"),
        lambda value: value["cases"][0].update(nodeid=value["cases"][1]["nodeid"]),
        lambda value: value["cases"][0].update(selected_dofs=30_001),
        lambda value: value["cases"][0].update(timeout_seconds=1201),
        lambda value: value["cases"][0].update(rss_soft_limit_mib=4095),
        lambda value: value["cases"][0].update(criteria_file_sha256="0" * 64),
        lambda value: value["budget"].update(implicit_retry=True),
        lambda value: value["budget"].update(concurrency=2),
        lambda value: value["predecessor_ledgers"][1].update(sha256="0" * 64),
        lambda value: value["historical_tet4_review"].update(proof_transfer_to_family_remainder=True),
        lambda value: value["historical_tet4_review"].update(l3_scalar_energy_verdict="PASS"),
        lambda value: value["stop_policy"].update(non_pass="CONTINUE"),
    ],
)
def test_contract_rejects_scope_budget_and_predecessor_mutations(mutate) -> None:
    contract = contract_fixture()
    mutate(contract)
    with pytest.raises(contract_module.FamilyRemainderContractError):
        contract_module.validate_contract(
            contract, scientific_fingerprint="1" * 64, controller_fingerprint="2" * 64,
        )


def test_owner_decision_must_bind_exact_contract_and_scope() -> None:
    contract = contract_fixture()
    digest = contract_module.validate_contract(
        contract, scientific_fingerprint="1" * 64, controller_fingerprint="2" * 64,
    )
    decision = {
        "schema": contract_module.DECISION_SCHEMA,
        "campaign_id": contract_module.CAMPAIGN_ID,
        "scope_id": contract_module.SCOPE_ID,
        "decision_id": "owner-decision-2026-01",
        "approved_by": "Owner",
        "approved_at_utc": "2026-10-30T12:00:00Z",
        "contract_sha256": digest,
        "case_ids": list(contract_module.CASE_IDS),
        "scientific_fingerprint": "1" * 64,
        "controller_fingerprint": "2" * 64,
        "budget": dict(contract_module.BUDGET),
        "status": "APPROVED",
    }
    for changed in (
        {**decision, "contract_sha256": "0" * 64},
        {**decision, "case_ids": list(reversed(decision["case_ids"]))},
        {**decision, "status": "PREPARED_NOT_AUTHORIZED"},
        {**decision, "approved_by": "other"},
    ):
        with pytest.raises(contract_module.FamilyRemainderContractError):
            contract_module.validate_owner_decision(
                changed, contract_sha256=digest,
                scientific_fingerprint="1" * 64, controller_fingerprint="2" * 64,
            )


def test_ledger_binds_all_predecessors_and_runs_exact_cases_sequentially(tmp_path: Path) -> None:
    specs = _write_synthetic_predecessors(tmp_path)
    ledger = make_ledger(tmp_path, specs)
    assert ledger.summary()["predecessor_attempts_charged"] == 7
    assert ledger.summary()["predecessor_elapsed_seconds_charged"] == 4069.326357999933

    first = start_case(ledger, tmp_path, 0, "first")
    with pytest.raises(ledger_module.FamilyRemainderLedgerError, match="open reservation|after STOP"):
        start_case(ledger, tmp_path, 1, "second-too-soon")
    ledger.finish_runner_attempt(run_id=first, status="PASS", elapsed_seconds=10.0)
    second = start_case(ledger, tmp_path, 1, "second")
    ledger.finish_runner_attempt(run_id=second, status="PASS", elapsed_seconds=20.0)

    records = ledger.verify()
    assert [record["case_id"] for record in records if record["event"] == "ATTEMPT_STARTED"] == list(
        contract_module.CASE_IDS[:2]
    )
    assert ledger.summary()["combined_attempts_used"] == 9
    assert ledger.summary()["combined_elapsed_seconds"] == 4099.326357999933


def test_family_reservation_receipt_matches_child_guard_bindings(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    binding, case = runner_bindings(0, ledger.allowed_root, "receipt-contract")
    receipt = ledger.start_runner_attempt(
        binding=binding,
        case=case,
        receipt_path=ledger.allowed_root / "receipts" / "child-guard.json",
    )

    assert receipt["campaign_id"] == contract_module.CAMPAIGN_ID
    assert receipt["ledger_scope_id"] == contract_module.SCOPE_ID
    assert Path(receipt["ledger_path"]).name == ledger.path.name
    assert receipt["campaign_attempts_used_after"] == 8
    assert receipt["campaign_seconds_reserved_after"] == 5269.326357999933


def test_ledger_refuses_out_of_order_retry_and_continuation_after_failure(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    with pytest.raises(ledger_module.FamilyRemainderLedgerError, match="outside the exact nine-case|frozen family/level order"):
        binding, case = runner_bindings(3, ledger.allowed_root, "out-of-scope")
        ledger.start_runner_attempt(
            binding=binding, case=case,
            receipt_path=tmp_path / "family-remainder-evidence" / "out-of-scope.json",
        )

    run_id = start_case(ledger, tmp_path, 0, "fails")
    ledger.finish_runner_attempt(run_id=run_id, status="TIMEOUT", elapsed_seconds=1200.0)
    with pytest.raises(ledger_module.FamilyRemainderLedgerError, match="non-PASS"):
        start_case(ledger, tmp_path, 1, "must-stop")
    with pytest.raises(ledger_module.FamilyRemainderLedgerError, match="unique attempt|non-PASS"):
        start_case(ledger, tmp_path, 0, "must-not-retry")


def test_ledger_refuses_if_predecessor_changes_or_budget_cannot_fit_scope(tmp_path: Path, monkeypatch) -> None:
    specs = _write_synthetic_predecessors(tmp_path)
    ledger = make_ledger(tmp_path, specs)
    predecessor_path = Path(specs[0]["path"])
    predecessor_path.write_bytes(predecessor_path.read_bytes() + b" ")
    with pytest.raises(ledger_module.FamilyRemainderLedgerError, match="SHA-256 changed"):
        ledger.summary()

    other = tmp_path / "other"
    other.mkdir()
    specs = _write_synthetic_predecessors(other)
    monkeypatch.setattr(
        ledger_module, "MAX_TOTAL_SECONDS", contract_module.PREDECESSOR_ELAPSED_SECONDS + 10_000,
    )
    with pytest.raises(ledger_module.FamilyRemainderLedgerError, match="cannot fit the cumulative seconds"):
        make_ledger(other, specs)


def test_receipt_setup_failure_closes_reserved_attempt_as_infra_error(tmp_path: Path, monkeypatch) -> None:
    ledger = make_ledger(tmp_path)
    binding, case = runner_bindings(0, ledger.allowed_root, "receipt-failure")

    def fail_receipt(*_args, **_kwargs):
        raise OSError("synthetic receipt setup failure")

    monkeypatch.setattr(ledger, "_write_reservation_receipt", fail_receipt)
    with pytest.raises(ledger_module.FamilyRemainderLedgerError, match="closed as INFRA_ERROR"):
        ledger.start_runner_attempt(
            binding=binding,
            case=case,
            receipt_path=ledger.allowed_root / "receipts" / "receipt-failure.json",
        )

    records = ledger.verify()
    starts = [record for record in records if record["event"] == "ATTEMPT_STARTED"]
    finishes = [record for record in records if record["event"] == "ATTEMPT_FINISHED"]
    assert len(starts) == len(finishes) == 1
    assert finishes[0]["run_id"] == starts[0]["run_id"]
    assert finishes[0]["status"] == "INFRA_ERROR"
    assert finishes[0]["elapsed_seconds"] >= 0.0
    assert ledger.summary()["stopped"] is True
    with pytest.raises(ledger_module.FamilyRemainderLedgerError, match="non-PASS"):
        start_case(ledger, tmp_path, 1, "after-receipt-failure")


def test_post_reservation_run_record_setup_error_writes_terminal_infra_record(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    run_id = start_case(ledger, tmp_path, 0, "record-failure")
    record_path = tmp_path / "family-remainder-evidence" / "record-failure" / "run.json"
    initial = {
        "schema": "qfsolver-development-vv3d-run-v1",
        "state": "RUNNING",
        "case_id": contract_module.CASE_IDS[0],
        "attempt_id": run_id,
        "attempt_reserved": True,
    }

    final = controller_module._finalize_vv3d_family_setup_error(
        ledger=ledger,
        run_id=run_id,
        record_path=record_path,
        initial_record=initial,
        error=OSError("synthetic post-reservation run-record setup failure"),
        reservation_started_monotonic=time.monotonic(),
    )

    records = ledger.verify()
    finished = [record for record in records if record["event"] == "ATTEMPT_FINISHED"]
    assert len(finished) == 1
    assert finished[0]["status"] == "INFRA_ERROR"
    assert final["state"] == "INFRA_ERROR"
    assert final["attempt_reserved"] is True
    assert json.loads(record_path.read_text(encoding="utf-8"))["state"] == "INFRA_ERROR"


def test_family_attempt_holds_predecessor_and_family_campaign_locks(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    family_lock = ledger.allowed_root / "locks" / "family-exclusive.lock"
    family_lock.parent.mkdir()
    predecessor_locks = ledger.predecessor_campaign_lock_paths()
    assert len(predecessor_locks) == 2  # R1 and R2; both diagnostics share R2's campaign lock.
    entered = threading.Event()
    release = threading.Event()
    failures: list[BaseException] = []

    def hold_locks() -> None:
        try:
            with controller_module._vv3d_family_remainder_attempt_locks(ledger, family_lock):
                entered.set()
                if not release.wait(timeout=10):
                    raise AssertionError("timed out waiting to release synthetic campaign locks")
        except BaseException as exc:  # surfaced in the joining test thread below
            failures.append(exc)

    worker = threading.Thread(target=hold_locks, daemon=True)
    worker.start()
    assert entered.wait(timeout=10)
    try:
        for lock_path in (*predecessor_locks, family_lock):
            with pytest.raises(controller_module.PolicyError, match="another authorized scenario is active"):
                with controller_module._exclusive_file_lock(lock_path):
                    pass
    finally:
        release.set()
        worker.join(timeout=10)
    assert not worker.is_alive()
    assert failures == []
