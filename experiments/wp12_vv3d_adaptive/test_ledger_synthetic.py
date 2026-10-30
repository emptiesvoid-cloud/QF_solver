"""Synthetic-only tests for the prospective VV3D budget ledger draft."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from experiments.wp12_vv3d_adaptive.ledger_draft import (
    MAX_ATTEMPTS,
    MAX_ATTEMPT_SECONDS,
    MAX_TOTAL_SECONDS,
    QPOST_JOB_IDS,
    BudgetLedger,
    LedgerError,
)


def make_ledger(tmp_path: Path) -> BudgetLedger:
    return BudgetLedger(tmp_path / "ledger.jsonl", allowed_root=tmp_path)


def test_failed_attempt_charges_observed_time_and_stops_campaign(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    run_id = ledger.start_synthetic_attempt(case_id="case-1")
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
        ledger.start_synthetic_attempt(case_id="case-2")


@pytest.mark.parametrize("status", ["TIMEOUT", "INTERRUPTED", "INFRA_ERROR", "INCONCLUSIVE", "RESOURCE_LIMIT"])
def test_every_non_pass_result_fails_closed(tmp_path: Path, status: str) -> None:
    ledger = make_ledger(tmp_path)
    run_id = ledger.start_synthetic_attempt(case_id="case-1")
    ledger.finish_synthetic_attempt(run_id=run_id, status=status, elapsed_seconds=1)

    with pytest.raises(LedgerError, match="non-PASS"):
        ledger.start_synthetic_attempt(case_id="case-2")


def test_only_one_attempt_can_be_open_at_a_time(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    run_id = ledger.start_synthetic_attempt(case_id="first")

    with pytest.raises(LedgerError, match="already open"):
        ledger.start_synthetic_attempt(case_id="second")

    ledger.finish_synthetic_attempt(run_id=run_id, status="PASS", elapsed_seconds=1)
    assert ledger.summary()["attempts_used"] == 1


def test_concurrent_starts_serialize_to_one_open_attempt(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)

    def start(case_id: str) -> str:
        try:
            return ledger.start_synthetic_attempt(case_id=case_id)
        except LedgerError:
            return "refused"

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(start, [f"case-{i}" for i in range(8)]))

    assert sum(result != "refused" for result in results) == 1
    assert ledger.summary()["attempts_used"] == 1
    assert ledger.summary()["attempt_open"] is True


def test_crash_keeps_real_elapsed_unknown_and_attempts_blocked(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    run_id = ledger.start_synthetic_attempt(case_id="crashed-worker")

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
        ledger.start_synthetic_attempt(case_id="next-case")
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
    ledger.start_synthetic_attempt(case_id="crashed")
    ledger.recover_interrupted_after_crash(confirmed_process_absent=True)

    with pytest.raises(LedgerError):
        ledger.resolve_crashed_attempt(**resolution)  # type: ignore[arg-type]

    assert ledger.summary()["crash_blocked"] is True
    assert ledger.summary()["seconds_reserved"] == MAX_ATTEMPT_SECONDS


def test_documented_measured_resolution_preserves_interruption_and_stops(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    run_id = ledger.start_synthetic_attempt(case_id="crashed")
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
        ledger.start_synthetic_attempt(case_id="new-case")


def test_case_id_cannot_recur_after_pass(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    run_id = ledger.start_synthetic_attempt(case_id="already-passed")
    ledger.finish_synthetic_attempt(run_id=run_id, status="PASS", elapsed_seconds=1)

    with pytest.raises(LedgerError, match="already been attempted"):
        ledger.start_synthetic_attempt(case_id="already-passed")
    next_run = ledger.start_synthetic_attempt(case_id="different-case")
    ledger.finish_synthetic_attempt(run_id=next_run, status="PASS", elapsed_seconds=1)


def test_qpost_jobs_share_lock_and_seconds_but_not_fem_attempt_quota(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    job_id = "VV3D-ADAPT-TET4-QPOST"
    run_id = ledger.start_synthetic_postprocess_job(job_id=job_id, archived_state_sha256="a" * 64)

    with pytest.raises(LedgerError, match="already open"):
        ledger.start_synthetic_attempt(case_id="cannot-overlap")

    finished = ledger.finish_synthetic_postprocess_job(run_id=run_id, status="PASS", elapsed_seconds=1200)
    assert finished["elapsed_seconds"] == 1200
    summary = ledger.summary()
    assert summary["attempts_used"] == 0
    assert summary["postprocess_jobs_used"] == 1
    assert summary["postprocess_jobs_remaining"] == len(QPOST_JOB_IDS) - 1
    assert summary["elapsed_seconds_actual"] == 1200

    fem_run = ledger.start_synthetic_attempt(case_id="distinct-fem-case")
    ledger.finish_synthetic_attempt(run_id=fem_run, status="PASS", elapsed_seconds=2.25)
    assert ledger.summary()["attempts_used"] == 1
    assert ledger.summary()["elapsed_seconds_actual"] == 1202.25

    with pytest.raises(LedgerError, match="already been consumed"):
        ledger.start_synthetic_postprocess_job(job_id=job_id, archived_state_sha256="a" * 64)


def test_four_catalogued_qpost_identities_are_distinct_and_no_others_are_allowed(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    for index, job_id in enumerate(sorted(QPOST_JOB_IDS)):
        run_id = ledger.start_synthetic_postprocess_job(
            job_id=job_id,
            archived_state_sha256=f"{index + 1:064x}",
        )
        ledger.finish_synthetic_postprocess_job(run_id=run_id, status="PASS", elapsed_seconds=0.5)

    assert ledger.summary()["postprocess_jobs_used"] == 4
    assert ledger.summary()["attempts_used"] == 0
    with pytest.raises(LedgerError, match="closed catalog"):
        ledger.start_synthetic_postprocess_job(job_id="UNLISTED-QPOST", archived_state_sha256="b" * 64)


def test_qpost_watchdog_overrun_preserves_elapsed_and_stops_shared_campaign(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    run_id = ledger.start_synthetic_postprocess_job(
        job_id="VV3D-ADAPT-HEX8-QPOST", archived_state_sha256="c" * 64
    )
    finished = ledger.finish_synthetic_postprocess_job(run_id=run_id, status="PASS", elapsed_seconds=1200.2)

    assert finished["elapsed_seconds"] == 1200.2
    assert finished["monitored_limit_seconds"] == 1200
    assert finished["status"] == "INFRA_ERROR"
    assert finished["stop_reasons"] == ["PER_ATTEMPT_LIMIT_OVERRUN"]
    with pytest.raises(LedgerError, match="watchdog overrun"):
        ledger.start_synthetic_attempt(case_id="must-not-start")


def test_qpost_crash_keeps_time_unknown_reserved_and_blocks_until_resolution(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    run_id = ledger.start_synthetic_postprocess_job(
        job_id="VV3D-ADAPT-TET10-QPOST", archived_state_sha256="d" * 64
    )
    crash = ledger.recover_postprocess_after_crash(confirmed_process_absent=True)

    assert crash["event"] == "POSTPROCESS_CRASH_OBSERVED"
    assert crash["elapsed_seconds"] is None
    assert crash["elapsed_state"] == "NOT_EXPOSED"
    assert ledger.summary()["seconds_reserved"] == 1200
    with pytest.raises(LedgerError, match="already open"):
        ledger.start_synthetic_postprocess_job(
            job_id="VV3D-ADAPT-HEX20-QPOST", archived_state_sha256="e" * 64
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
        ledger.start_synthetic_attempt(case_id="stopped-after-qpost-crash")


def test_exact_attempt_and_total_time_caps_are_enforced(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    for index in range(MAX_ATTEMPTS):
        run_id = ledger.start_synthetic_attempt(case_id=f"c{index}")
        ledger.finish_synthetic_attempt(run_id=run_id, status="PASS", elapsed_seconds=MAX_ATTEMPT_SECONDS)

    assert ledger.summary()["attempts_used"] == MAX_ATTEMPTS
    assert ledger.summary()["elapsed_seconds_actual"] == MAX_TOTAL_SECONDS
    with pytest.raises(LedgerError, match="attempt budget"):
        ledger.start_synthetic_attempt(case_id="extra")


@pytest.mark.parametrize(
    ("status", "elapsed_seconds"),
    [("UNKNOWN", 1), ("FAIL", -1), ("FAIL", float("nan")), ("FAIL", float("inf")), ("FAIL", True)],
)
def test_invalid_finish_values_are_refused(tmp_path: Path, status: str, elapsed_seconds: int) -> None:
    ledger = make_ledger(tmp_path)
    run_id = ledger.start_synthetic_attempt(case_id="valid")
    with pytest.raises(LedgerError):
        ledger.finish_synthetic_attempt(run_id=run_id, status=status, elapsed_seconds=elapsed_seconds)
    assert ledger.summary()["attempt_open"] is True


def test_fractional_elapsed_time_is_preserved_exactly(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    run_id = ledger.start_synthetic_attempt(case_id="fractional")
    finish = ledger.finish_synthetic_attempt(run_id=run_id, status="PASS", elapsed_seconds=0.375)

    assert finish["elapsed_seconds"] == 0.375
    assert finish["monitored_limit_seconds"] == MAX_ATTEMPT_SECONDS
    assert finish["stop_reasons"] == []
    assert finish["status"] == "PASS"
    assert ledger.summary()["elapsed_seconds_actual"] == 0.375


def test_watchdog_overrun_preserves_actual_time_and_stops_campaign(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    run_id = ledger.start_synthetic_attempt(case_id="watchdog-overrun")
    finish = ledger.finish_synthetic_attempt(
        run_id=run_id, status="PASS", elapsed_seconds=1_200.2
    )

    assert finish["elapsed_seconds"] == 1_200.2
    assert finish["monitored_limit_seconds"] == 1_200
    assert finish["status"] == "INFRA_ERROR"
    assert finish["stop_reasons"] == ["PER_ATTEMPT_LIMIT_OVERRUN"]
    assert ledger.summary()["elapsed_seconds_actual"] == 1_200.2
    with pytest.raises(LedgerError, match="watchdog overrun"):
        ledger.start_synthetic_attempt(case_id="must-not-start")


def test_crash_resolution_overrun_is_preserved_as_infra_stop(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    ledger.start_synthetic_attempt(case_id="crashed-overrun")
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
        ledger.start_synthetic_attempt(case_id="must-not-start")


def test_ledger_path_must_be_inside_explicit_synthetic_root(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside.jsonl"
    with pytest.raises(LedgerError, match="allowed root"):
        BudgetLedger(outside, allowed_root=tmp_path)
