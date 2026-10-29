"""Synthetic-only tests for the prospective VV3D budget ledger draft."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path

import pytest

from scripts.wp12_vv3d_ledger import (
    MAX_ATTEMPTS,
    MAX_ATTEMPT_SECONDS,
    MAX_TOTAL_SECONDS,
    QPOST_JOB_IDS,
    BudgetLedger,
    LedgerError,
    RunBinding,
    RunnerCaseBinding,
)


def make_ledger(tmp_path: Path) -> BudgetLedger:
    return BudgetLedger(tmp_path / "ledger.jsonl", allowed_root=tmp_path)


def make_binding(label: str, *, manifest_sha256: str | None = None) -> RunBinding:
    return RunBinding(
        contract_sha256="1" * 64,
        decision_id="synthetic-decision-1",
        decision_sha256="2" * 64,
        manifest_sha256=manifest_sha256 or hashlib.sha256(f"manifest:{label}".encode()).hexdigest(),
        preflight_sha256=hashlib.sha256(f"preflight:{label}".encode()).hexdigest(),
    )


def start_fem(ledger: BudgetLedger, case_id: str) -> str:
    return ledger.start_synthetic_attempt(case_id=case_id, binding=make_binding(case_id))


def make_runner_case(case_id: str) -> RunnerCaseBinding:
    return RunnerCaseBinding(
        case_id=case_id,
        nodeid=f"tests/unit/test_vv3d.py::test_case[{case_id}]",
        attempt_id=f"attempt-{case_id}",
        authorization_id="synthetic-auth-1",
        source_fingerprint="3" * 64,
        controller_fingerprint="4" * 64,
        selected_dofs=100,
        timeout_seconds=1200,
        rss_soft_limit_mib=4096,
        archive_limit_mib=256,
        evidence_root="E:/synthetic-vv3d-evidence",
    )


def make_qpost_binding(label: str, source_case_id: str, job_id: str, manifest_sha256: str) -> RunBinding:
    base = make_binding(label, manifest_sha256=manifest_sha256)
    return RunBinding(
        base.contract_sha256, base.decision_id, base.decision_sha256, base.manifest_sha256,
        base.preflight_sha256, hashlib.sha256(f"transition:{source_case_id}:{job_id}".encode()).hexdigest(),
        source_case_id, job_id,
    )


def pass_source(ledger: BudgetLedger, case_id: str) -> RunBinding:
    binding = make_binding(case_id)
    run_id = ledger.start_synthetic_attempt(case_id=case_id, binding=binding)
    ledger.finish_synthetic_attempt(run_id=run_id, status="PASS", elapsed_seconds=1)
    return binding


def test_failed_attempt_charges_observed_time_and_stops_campaign(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    run_id = start_fem(ledger, "case-1")
    ledger.finish_synthetic_attempt(run_id=run_id, status="FAIL", elapsed_seconds=19)

    assert ledger.summary() == {
        "attempts_used": 1,
        "attempts_remaining": MAX_ATTEMPTS - 1,
        "elapsed_seconds_actual": 19,
        "seconds_reserved": 0,
        "seconds_remaining_after_reservation": MAX_TOTAL_SECONDS - 19,
        "attempt_open": False,
        "crash_blocked": False,
        "postprocess_jobs_used": 0,
        "postprocess_jobs_remaining": len(QPOST_JOB_IDS),
    }
    with pytest.raises(LedgerError, match="non-PASS"):
        start_fem(ledger, "case-2")


def test_runner_reservation_receipt_is_immutable_and_binds_full_identity(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    receipt_file = tmp_path / "receipts" / "case-1.reservation.json"
    binding = make_binding("case-1")
    receipt = ledger.start_runner_attempt(
        binding=binding, case=make_runner_case("case-1"), receipt_path=receipt_file,
    )
    import json

    raw = receipt_file.read_bytes()
    parsed = json.loads(raw)
    checksum = json.loads(receipt_file.with_suffix(receipt_file.suffix + ".sha256.json").read_bytes())
    assert hashlib.sha256(raw).hexdigest() == checksum["sha256"] == receipt["receipt_sha256"]
    assert parsed["schema"] == "qf-wp12-vv3d-runner-reservation-v1"
    assert parsed["nodeid"] == make_runner_case("case-1").nodeid
    assert parsed["preflight_receipt_sha256"] == binding.preflight_sha256
    assert parsed["decision_id"] == binding.decision_id
    assert parsed["decision_sha256"] == binding.decision_sha256
    assert parsed["authorization_id"] == make_runner_case("case-1").authorization_id
    assert parsed["evidence_root"] == make_runner_case("case-1").evidence_root
    assert parsed["scientific_fingerprint"] == "3" * 64
    assert parsed["controller_fingerprint"] == "4" * 64
    assert parsed["selected_dofs"] == 100
    assert parsed["timeout_seconds"] == 1200
    assert parsed["rss_soft_limit_mib"] == 4096
    assert parsed["archive_size_limit_mib"] == 256
    assert parsed["ledger_scope_id"] == "wp12_vv3d_adaptive"
    assert parsed["attempt_number"] == 1
    assert parsed["max_attempts"] == 1
    assert parsed["attempt_reserved"] is True
    assert parsed["campaign_attempts_used_after"] == 1
    assert parsed["campaign_seconds_reserved_after"] == 1200
    assert parsed["ledger_sha256_after_reservation"] == hashlib.sha256(ledger.path.read_bytes()).hexdigest()
    assert ledger.summary()["seconds_reserved"] == 1200
    with pytest.raises(LedgerError, match="already been attempted"):
        ledger.start_runner_attempt(
            binding=binding, case=make_runner_case("case-1"),
            receipt_path=tmp_path / "receipts" / "case-1-retry.json",
        )
    blocked_root = tmp_path / "blocked"
    blocked_root.mkdir()
    blocked = make_ledger(blocked_root)
    occupied_receipt = tmp_path / "blocked" / "case-occupied.json"
    occupied_receipt.parent.mkdir(parents=True, exist_ok=True)
    occupied_receipt.write_text("historical", encoding="utf-8")
    with pytest.raises(LedgerError, match="refusing overwrite"):
        blocked.start_runner_attempt(
            binding=make_binding("case-2"), case=make_runner_case("case-2"), receipt_path=occupied_receipt,
        )
    assert blocked.summary()["attempt_open"] is True  # fail closed after ledger append


@pytest.mark.parametrize("status", ["TIMEOUT", "INTERRUPTED", "INFRA_ERROR", "INCONCLUSIVE", "RESOURCE_LIMIT"])
def test_every_non_pass_result_fails_closed(tmp_path: Path, status: str) -> None:
    ledger = make_ledger(tmp_path)
    run_id = start_fem(ledger, "case-1")
    ledger.finish_synthetic_attempt(run_id=run_id, status=status, elapsed_seconds=1)

    with pytest.raises(LedgerError, match="non-PASS"):
        start_fem(ledger, "case-2")


def test_only_one_attempt_can_be_open_at_a_time(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    run_id = start_fem(ledger, "first")

    with pytest.raises(LedgerError, match="already open"):
        start_fem(ledger, "second")

    ledger.finish_synthetic_attempt(run_id=run_id, status="PASS", elapsed_seconds=1)
    assert ledger.summary()["attempts_used"] == 1


def test_concurrent_starts_serialize_to_one_open_attempt(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)

    def start(case_id: str) -> str:
        try:
            return start_fem(ledger, case_id)
        except LedgerError:
            return "refused"

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(start, [f"case-{i}" for i in range(8)]))

    assert sum(result != "refused" for result in results) == 1
    assert ledger.summary()["attempts_used"] == 1
    assert ledger.summary()["attempt_open"] is True


def test_crash_keeps_real_elapsed_unknown_and_attempts_blocked(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    run_id = start_fem(ledger, "crashed-worker")

    with pytest.raises(LedgerError, match="explicit confirmation"):
        ledger.recover_interrupted_after_crash(confirmed_process_absent=False)
    event = ledger.recover_interrupted_after_crash(confirmed_process_absent=True)

    assert event["event"] == "ATTEMPT_CRASH_OBSERVED"
    assert event["run_id"] == run_id
    assert event["elapsed_seconds"] is None
    assert event["elapsed_state"] == "NOT_EXPOSED"
    assert event["reserved_seconds"] == MAX_ATTEMPT_SECONDS
    assert ledger.summary()["elapsed_seconds_actual"] == 0
    assert ledger.summary()["seconds_reserved"] == MAX_ATTEMPT_SECONDS
    assert ledger.summary()["crash_blocked"] is True

    with pytest.raises(LedgerError, match="already open"):
        start_fem(ledger, "next-case")
    with pytest.raises(LedgerError, match="documented resolution"):
        ledger.finish_synthetic_attempt(run_id=run_id, status="INTERRUPTED", elapsed_seconds=300)


@pytest.mark.parametrize(
    "resolution",
    [
        {"elapsed_seconds": None, "decision_id": "D-1", "decision_rationale": "measured"},
        {"elapsed_seconds": 300, "decision_id": " ", "decision_rationale": "measured"},
        {"elapsed_seconds": 300, "decision_id": "D-1", "decision_rationale": " "},
        {"elapsed_seconds": -0.25, "decision_id": "D-1", "decision_rationale": "measured"},
    ],
)
def test_crash_resolution_requires_reliable_duration_and_documented_decision(
    tmp_path: Path, resolution: dict[str, object]
) -> None:
    ledger = make_ledger(tmp_path)
    start_fem(ledger, "crashed")
    ledger.recover_interrupted_after_crash(confirmed_process_absent=True)

    with pytest.raises(LedgerError):
        ledger.resolve_crashed_attempt(**resolution)  # type: ignore[arg-type]

    assert ledger.summary()["crash_blocked"] is True
    assert ledger.summary()["seconds_reserved"] == MAX_ATTEMPT_SECONDS


def test_documented_measured_resolution_preserves_interruption_and_stops(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    run_id = start_fem(ledger, "crashed")
    ledger.recover_interrupted_after_crash(confirmed_process_absent=True)
    resolution = ledger.resolve_crashed_attempt(
        elapsed_seconds=247,
        decision_id="owner-review-7",
        decision_rationale="Reliable process accounting confirmed 247 elapsed seconds.",
    )

    assert resolution["run_id"] == run_id
    assert resolution["elapsed_seconds"] == 247
    assert resolution["recovered_after_crash"] is True
    assert ledger.summary()["elapsed_seconds_actual"] == 247
    assert ledger.summary()["seconds_reserved"] == 0
    assert ledger.summary()["crash_blocked"] is False

    with pytest.raises(LedgerError, match="non-PASS"):
        start_fem(ledger, "new-case")


def test_case_id_cannot_recur_after_pass(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    run_id = start_fem(ledger, "already-passed")
    ledger.finish_synthetic_attempt(run_id=run_id, status="PASS", elapsed_seconds=1)

    with pytest.raises(LedgerError, match="already been attempted"):
        start_fem(ledger, "already-passed")
    next_run = start_fem(ledger, "different-case")
    ledger.finish_synthetic_attempt(run_id=next_run, status="PASS", elapsed_seconds=1)


def test_qpost_jobs_share_lock_and_seconds_but_not_fem_attempt_quota(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    job_id = "VV3D-ADAPT-TET4-QPOST"
    source_binding = pass_source(ledger, "qpost-source-tet4")
    qpost_binding = make_qpost_binding("qpost-tet4", "qpost-source-tet4", job_id, source_binding.manifest_sha256)
    run_id = ledger.start_synthetic_postprocess_job(
        job_id=job_id,
        source_case_id="qpost-source-tet4",
        archived_state_sha256="a" * 64,
        binding=qpost_binding,
    )

    with pytest.raises(LedgerError, match="already open"):
        start_fem(ledger, "cannot-overlap")

    finished = ledger.finish_synthetic_postprocess_job(run_id=run_id, status="PASS", elapsed_seconds=1200)
    assert finished["elapsed_seconds"] == 1200
    summary = ledger.summary()
    assert summary["attempts_used"] == 1  # the source case only; QPOST adds no FEM attempt
    assert summary["postprocess_jobs_used"] == 1
    assert summary["postprocess_jobs_remaining"] == len(QPOST_JOB_IDS) - 1
    assert summary["elapsed_seconds_actual"] == 1201

    fem_run = start_fem(ledger, "distinct-fem-case")
    ledger.finish_synthetic_attempt(run_id=fem_run, status="PASS", elapsed_seconds=2.25)
    assert ledger.summary()["attempts_used"] == 2
    assert ledger.summary()["elapsed_seconds_actual"] == 1203.25

    with pytest.raises(LedgerError, match="already been consumed"):
        ledger.start_synthetic_postprocess_job(
            job_id=job_id,
            source_case_id="qpost-source-tet4",
            archived_state_sha256="a" * 64,
            binding=make_qpost_binding("qpost-tet4-duplicate", "qpost-source-tet4", job_id, source_binding.manifest_sha256),
        )


def test_runner_qpost_receipt_charges_time_but_not_science_attempt(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    source_binding = pass_source(ledger, "qpost-runner-source")
    qpost_binding = make_qpost_binding("qpost-runner", "qpost-runner-source", "VV3D-ADAPT-TET4-QPOST",
                                       source_binding.manifest_sha256)
    receipt_path = tmp_path / "receipts" / "qpost.json"
    receipt = ledger.start_runner_postprocess_job(
        job_id="VV3D-ADAPT-TET4-QPOST", source_case_id="qpost-runner-source",
        archived_state_sha256="a" * 64, binding=qpost_binding,
        nodeid="tests/unit/test_vv3d.py::test_qpost[TET4]",
        source_fingerprint="3" * 64, controller_fingerprint="4" * 64,
        evidence_root=str(tmp_path), receipt_path=receipt_path, job_manifest_sha256="5" * 64,
    )
    raw = receipt_path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == receipt["receipt_sha256"]
    import json
    stored = json.loads(raw)
    assert stored["attempt_reserved"] is False
    assert stored["manifest_sha256"] == "5" * 64
    assert stored["campaign_attempts_used_after"] == 1
    assert stored["campaign_seconds_reserved_after"] == 1201
    assert ledger.summary()["attempts_used"] == 1
    ledger.finish_runner_postprocess_job(
        run_id=receipt["reservation_id"], status="PASS", elapsed_seconds=7.5,
    )
    summary = ledger.summary()
    assert summary["attempts_used"] == 1
    assert summary["elapsed_seconds_actual"] == pytest.approx(8.5)
    assert summary["postprocess_jobs_used"] == 1


def test_qpost_can_follow_scientific_fail_only_with_exact_transition_binding(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    source_id = "source-qpost-fail"
    source_binding = make_binding(source_id)
    run_id = ledger.start_synthetic_attempt(case_id=source_id, binding=source_binding)
    ledger.finish_synthetic_attempt(run_id=run_id, status="FAIL", elapsed_seconds=2)
    job_id = "VV3D-ADAPT-TET4-QPOST"

    with pytest.raises(LedgerError, match="exact source-to-job eligibility"):
        ledger.start_synthetic_postprocess_job(
            job_id=job_id, source_case_id=source_id, archived_state_sha256="d" * 64,
            binding=make_binding("unbound-qpost", manifest_sha256=source_binding.manifest_sha256),
        )

    qpost_id = ledger.start_synthetic_postprocess_job(
        job_id=job_id, source_case_id=source_id, archived_state_sha256="d" * 64,
        binding=make_qpost_binding("bound-qpost", source_id, job_id, source_binding.manifest_sha256),
    )
    finished = ledger.finish_synthetic_postprocess_job(run_id=qpost_id, status="PASS", elapsed_seconds=3)

    assert finished["status"] == "PASS"
    assert ledger.summary()["attempts_used"] == 1
    assert ledger.summary()["postprocess_jobs_used"] == 1


def test_adaptive_fem_reservation_requires_exact_receipt_binding_after_scientific_fail(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    source_id = "source-case"
    source = start_fem(ledger, source_id)
    ledger.finish_synthetic_attempt(run_id=source, status="FAIL", elapsed_seconds=5)
    base = make_binding("adaptive")
    transition_sha = "a" * 64
    adaptive_binding = RunBinding(
        base.contract_sha256, base.decision_id, base.decision_sha256, base.manifest_sha256,
        base.preflight_sha256, transition_sha, source_id, "adaptive-case",
    )
    receipt = ledger.start_runner_attempt(
        binding=adaptive_binding,
        case=RunnerCaseBinding(
            "adaptive-case", "tests/unit/test_vv3d.py::test_case[adaptive]", "attempt-adaptive",
            "synthetic-auth-adaptive", "3" * 64, "4" * 64, 100, 1200, 4096, 256, str(tmp_path),
        ),
        receipt_path=tmp_path / "receipts" / "adaptive.json",
    )
    assert receipt["transition_receipt_sha256"] == transition_sha
    assert receipt["transition_source_case_id"] == source_id
    assert receipt["transition_destination_case_id"] == "adaptive-case"


def test_four_catalogued_qpost_identities_are_distinct_and_no_others_are_allowed(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    for index, job_id in enumerate(sorted(QPOST_JOB_IDS)):
        source_case_id = f"source-{index}"
        source_binding = pass_source(ledger, source_case_id)
        run_id = ledger.start_synthetic_postprocess_job(
            job_id=job_id,
            source_case_id=source_case_id,
            archived_state_sha256=f"{index + 1:064x}",
            binding=make_qpost_binding(f"qpost-{index}", source_case_id, job_id, source_binding.manifest_sha256),
        )
        ledger.finish_synthetic_postprocess_job(run_id=run_id, status="PASS", elapsed_seconds=0.5)

    assert ledger.summary()["postprocess_jobs_used"] == 4
    assert ledger.summary()["attempts_used"] == 4
    with pytest.raises(LedgerError, match="closed catalog"):
        ledger.start_synthetic_postprocess_job(
            job_id="UNLISTED-QPOST",
            source_case_id="source-0",
            archived_state_sha256="b" * 64,
            binding=make_binding("unlisted", manifest_sha256=make_binding("source-0").manifest_sha256),
        )


def test_qpost_watchdog_overrun_preserves_elapsed_and_stops_shared_campaign(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    source_binding = pass_source(ledger, "source-overrun")
    run_id = ledger.start_synthetic_postprocess_job(
        job_id="VV3D-ADAPT-HEX8-QPOST",
        source_case_id="source-overrun",
        archived_state_sha256="c" * 64,
        binding=make_qpost_binding("qpost-overrun", "source-overrun", "VV3D-ADAPT-HEX8-QPOST", source_binding.manifest_sha256),
    )
    finished = ledger.finish_synthetic_postprocess_job(run_id=run_id, status="PASS", elapsed_seconds=1200.2)

    assert finished["elapsed_seconds"] == 1200.2
    assert finished["monitored_limit_seconds"] == 1200
    assert finished["status"] == "INFRA_ERROR"
    assert finished["stop_reasons"] == ["PER_ATTEMPT_LIMIT_OVERRUN"]
    with pytest.raises(LedgerError, match="watchdog overrun"):
        start_fem(ledger, "must-not-start")


def test_qpost_crash_keeps_time_unknown_reserved_and_blocks_until_resolution(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    source_binding = pass_source(ledger, "source-crash")
    run_id = ledger.start_synthetic_postprocess_job(
        job_id="VV3D-ADAPT-TET10-QPOST",
        source_case_id="source-crash",
        archived_state_sha256="d" * 64,
        binding=make_qpost_binding("qpost-crash", "source-crash", "VV3D-ADAPT-TET10-QPOST",
                                   source_binding.manifest_sha256),
    )
    crash = ledger.recover_postprocess_after_crash(confirmed_process_absent=True)

    assert crash["event"] == "POSTPROCESS_CRASH_OBSERVED"
    assert crash["elapsed_seconds"] is None
    assert crash["elapsed_state"] == "NOT_EXPOSED"
    assert ledger.summary()["seconds_reserved"] == 1200
    with pytest.raises(LedgerError, match="already open"):
        ledger.start_synthetic_postprocess_job(
            job_id="VV3D-ADAPT-HEX20-QPOST",
            source_case_id="source-crash",
            archived_state_sha256="e" * 64,
            binding=make_qpost_binding("qpost-other", "source-crash", "VV3D-ADAPT-HEX20-QPOST",
                                       source_binding.manifest_sha256),
        )

    finished = ledger.resolve_crashed_postprocess_job(
        elapsed_seconds=17.375,
        decision_id="qpost-crash-review-1",
        decision_rationale="A synthetic reliable clock record supplies elapsed duration.",
    )
    assert finished["run_id"] == run_id
    assert finished["elapsed_seconds"] == 17.375
    assert finished["status"] == "INTERRUPTED"
    with pytest.raises(LedgerError, match="non-PASS"):
        start_fem(ledger, "stopped-after-qpost-crash")


def test_exact_attempt_and_total_time_caps_are_enforced(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    for index in range(MAX_ATTEMPTS):
        run_id = start_fem(ledger, f"c{index}")
        ledger.finish_synthetic_attempt(run_id=run_id, status="PASS", elapsed_seconds=MAX_ATTEMPT_SECONDS)

    assert ledger.summary()["attempts_used"] == MAX_ATTEMPTS
    assert ledger.summary()["elapsed_seconds_actual"] == MAX_TOTAL_SECONDS
    with pytest.raises(LedgerError, match="attempt budget"):
        start_fem(ledger, "extra")


@pytest.mark.parametrize(
    ("status", "elapsed_seconds"),
    [("UNKNOWN", 1), ("FAIL", -1), ("FAIL", float("nan")), ("FAIL", float("inf")), ("FAIL", True)],
)
def test_invalid_finish_values_are_refused(tmp_path: Path, status: str, elapsed_seconds: int) -> None:
    ledger = make_ledger(tmp_path)
    run_id = start_fem(ledger, "valid")
    with pytest.raises(LedgerError):
        ledger.finish_synthetic_attempt(run_id=run_id, status=status, elapsed_seconds=elapsed_seconds)
    assert ledger.summary()["attempt_open"] is True


def test_fractional_elapsed_time_is_preserved_exactly(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    run_id = start_fem(ledger, "fractional")
    finish = ledger.finish_synthetic_attempt(run_id=run_id, status="PASS", elapsed_seconds=0.375)

    assert finish["elapsed_seconds"] == 0.375
    assert finish["monitored_limit_seconds"] == MAX_ATTEMPT_SECONDS
    assert finish["stop_reasons"] == []
    assert finish["status"] == "PASS"
    assert ledger.summary()["elapsed_seconds_actual"] == 0.375


def test_watchdog_overrun_preserves_actual_time_and_stops_campaign(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    run_id = start_fem(ledger, "watchdog-overrun")
    finish = ledger.finish_synthetic_attempt(
        run_id=run_id, status="PASS", elapsed_seconds=1_200.2
    )

    assert finish["elapsed_seconds"] == 1_200.2
    assert finish["monitored_limit_seconds"] == 1_200
    assert finish["status"] == "INFRA_ERROR"
    assert finish["stop_reasons"] == ["PER_ATTEMPT_LIMIT_OVERRUN"]
    assert ledger.summary()["elapsed_seconds_actual"] == 1_200.2
    with pytest.raises(LedgerError, match="watchdog overrun"):
        start_fem(ledger, "must-not-start")


def test_crash_resolution_overrun_is_preserved_as_infra_stop(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    start_fem(ledger, "crashed-overrun")
    ledger.recover_interrupted_after_crash(confirmed_process_absent=True)
    finish = ledger.resolve_crashed_attempt(
        elapsed_seconds=1_200.2,
        decision_id="measured-crash-8",
        decision_rationale="Reliable process accounting measured the full elapsed duration.",
    )

    assert finish["elapsed_seconds"] == 1_200.2
    assert finish["status"] == "INFRA_ERROR"
    assert finish["stop_reasons"] == ["PER_ATTEMPT_LIMIT_OVERRUN"]
    with pytest.raises(LedgerError, match="watchdog overrun"):
        start_fem(ledger, "must-not-start")


def test_ledger_path_must_be_inside_explicit_synthetic_root(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside.jsonl"
    with pytest.raises(LedgerError, match="allowed root"):
        BudgetLedger(outside, allowed_root=tmp_path)
