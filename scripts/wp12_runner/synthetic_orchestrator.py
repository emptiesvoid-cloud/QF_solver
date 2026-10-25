"""Orchestrate fixed WP12 runner self-tests without scientific selectors.

This module can launch only the repository's fixed fake-child cases. Its
temporary receipts and hash-chained journal are self-test diagnostics, not
campaign evidence or a durable qualification ledger.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import uuid
from typing import Any, Mapping

from .contracts import ContractError, REAL_EXECUTION_ENABLED, sha256_bytes, sha256_file
from .evidence import JsonlJournal, verify_receipt, write_receipt
from .process import FAKE_CASES, FAKE_CHILD, ProcessOutcome, run_fake_process


SYNTHETIC_CAMPAIGN_ID = "WP12-X-SYNTHETIC-ORCHESTRATOR"
SYNTHETIC_CASES = tuple(sorted(FAKE_CASES))
_ZERO_SHA256 = "0" * 64
_SELF_TEST_ONLY = "SYNTHETIC_RUNNER_SELF_TEST"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode(
        "utf-8"
    )


def _plan_sha256(cases: tuple[str, ...]) -> str:
    plan = {
        "schema": "qf-wp12-synthetic-orchestration-plan-v1",
        "campaign_id": SYNTHETIC_CAMPAIGN_ID,
        "cases": list(cases),
        "attempts_per_case": 1,
        "limits": {
            "default_timeout_seconds": 2.0,
            "short_timeout_seconds": 0.35,
            "short_timeout_cases": ["sleep", "tree"],
            "process_count_limit": 8,
            "default_output_byte_limit": 65536,
            "flood_output_byte_limit": 256,
            "memory_hard_limit_bytes": 64 * 1024 * 1024,
        },
        "scientific_execution": False,
        "owner_authorization": "NOT_APPLICABLE_TO_SYNTHETIC_SELF_TEST",
    }
    return sha256_bytes(_canonical(plan))


def _runner_file_hashes() -> dict[str, str]:
    module_directory = Path(__file__).resolve().parent
    files = {
        "synthetic_orchestrator": Path(__file__).resolve(),
        "cli": module_directory / "cli.py",
        "contracts": module_directory / "contracts.py",
        "process": module_directory / "process.py",
        "evidence": module_directory / "evidence.py",
        "windows_job": module_directory / "windows_job.py",
        "fake_child": FAKE_CHILD,
    }
    hashes: dict[str, str] = {}
    for name, path in files.items():
        if not path.is_file() or path.is_symlink():
            raise ContractError(f"synthetic runner source is absent or unsafe: {name}")
        hashes[name] = sha256_file(path)
    return hashes


class _SyntheticJournal:
    """Temporary hash-chained lifecycle journal for synthetic units only."""

    def __init__(self, path: Path) -> None:
        self._journal = JsonlJournal(path)
        self._sequence = 0
        self._previous = _ZERO_SHA256
        self.path = path

    @property
    def record_count(self) -> int:
        return self._sequence

    def append(self, event: Mapping[str, Any]) -> dict[str, Any]:
        body = {
            "sequence": self._sequence + 1,
            "previous_event_sha256": self._previous,
            **dict(event),
        }
        digest = sha256_bytes(_canonical(body))
        record = {**body, "event_sha256": digest}
        self._journal.append(record)
        self._sequence += 1
        self._previous = digest
        return record

    def verify(self) -> tuple[str, ...]:
        errors: list[str] = []
        previous = _ZERO_SHA256
        try:
            records = JsonlJournal.read(self.path)
        except (OSError, ContractError) as exc:
            return (f"synthetic lifecycle journal unreadable: {type(exc).__name__}",)
        for sequence, record in enumerate(records, start=1):
            claimed = record.pop("event_sha256", None)
            if record.get("sequence") != sequence:
                errors.append(f"synthetic lifecycle sequence mismatch at {sequence}")
            if record.get("previous_event_sha256") != previous:
                errors.append(f"synthetic lifecycle predecessor mismatch at {sequence}")
            calculated = sha256_bytes(_canonical(record))
            if claimed != calculated:
                errors.append(f"synthetic lifecycle hash mismatch at {sequence}")
            previous = calculated
        return tuple(errors)


def _expected_result(case: str, outcome: ProcessOutcome) -> tuple[bool, str]:
    if case == "memory":
        passed = (
            outcome.state == "PROCESS_EXITED" and outcome.return_code not in (None, 0) and outcome.hard_job_enforced
        )
        explanation = (
            "Windows Job Object terminated the synthetic allocator"
            if passed
            else "hard Windows Job Object memory enforcement was not demonstrated"
        )
        return passed, explanation

    expected = {
        "success": ("PROCESS_EXITED", 0),
        "exit": ("PROCESS_EXITED", 17),
        "sleep": ("TIMEOUT", None),
        "tree": ("TIMEOUT", None),
        "flood": ("RESOURCE_LIMIT", None),
    }[case]
    passed = outcome.state == expected[0]
    if expected[1] is not None:
        passed = passed and outcome.return_code == expected[1]
    if case == "tree":
        passed = passed and not outcome.child_pids_remaining
    explanation = (
        "observed synthetic supervisor result matched its fixed expectation"
        if passed
        else "unexpected synthetic process result"
    )
    return passed, explanation


def _result_record(
    *,
    case: str,
    run_id: str,
    self_test: str,
    explanation: str,
    outcome: ProcessOutcome | None = None,
    receipt_sha256: str | None = None,
    receipt_issues: tuple[str, ...] = (),
    run_directory: Path | None = None,
) -> dict[str, Any]:
    stdout = run_directory / "stdout.bin" if run_directory is not None else None
    stderr = run_directory / "stderr.bin" if run_directory is not None else None
    return {
        "case": case,
        "run_id": run_id,
        "attempt": 1,
        "maximum_attempts": 1,
        "self_test": self_test,
        "result_kind": _SELF_TEST_ONLY,
        "scientific_result": False,
        "explanation": explanation,
        "supervisor_state": outcome.state if outcome is not None else None,
        "return_code": outcome.return_code if outcome is not None else None,
        "stop_reason": outcome.stop_reason if outcome is not None else None,
        "elapsed_seconds": round(outcome.elapsed_seconds, 6) if outcome is not None else None,
        "stdout_bytes_seen": outcome.stdout_bytes if outcome is not None else 0,
        "stderr_bytes_seen": outcome.stderr_bytes if outcome is not None else 0,
        "stdout_sha256": sha256_file(stdout) if stdout is not None and stdout.is_file() else None,
        "stderr_sha256": sha256_file(stderr) if stderr is not None and stderr.is_file() else None,
        "sampled_peak_rss_bytes": outcome.sampled_peak_rss_bytes if outcome is not None else None,
        "sampled_peak_process_count": outcome.sampled_peak_process_count if outcome is not None else 0,
        "child_pids_remaining": list(outcome.child_pids_remaining) if outcome is not None else [],
        "hard_job_enforced": outcome.hard_job_enforced if outcome is not None else False,
        "receipt_sha256": receipt_sha256,
        "receipt_issues": list(receipt_issues),
    }


def _run_one_case(
    case: str,
    *,
    temporary_root: Path,
    plan_sha256: str,
    runner_hashes: Mapping[str, str],
    journal: _SyntheticJournal,
) -> dict[str, Any]:
    run_id = uuid.uuid4().hex
    run_directory = temporary_root / "runs" / run_id
    journal.append(
        {
            "event": "SYNTHETIC_UNIT_STARTED",
            "campaign_id": SYNTHETIC_CAMPAIGN_ID,
            "plan_sha256": plan_sha256,
            "run_id": run_id,
            "case_id": case,
            "attempt": 1,
            "maximum_attempts": 1,
            "status": "RUNNING",
            "started_utc": _utc_now(),
        }
    )

    if case == "memory" and os.name != "nt":
        result = _result_record(
            case=case,
            run_id=run_id,
            self_test="NOT_APPLICABLE",
            explanation="Windows Job Object hard memory enforcement is platform-specific",
        )
        journal.append(
            {
                "event": "SYNTHETIC_UNIT_FINISHED",
                "campaign_id": SYNTHETIC_CAMPAIGN_ID,
                "plan_sha256": plan_sha256,
                "run_id": run_id,
                "case_id": case,
                "attempt": 1,
                "status": "NOT_APPLICABLE",
                "finished_utc": _utc_now(),
                "scientific_execution": False,
            }
        )
        return result

    timeout = 0.35 if case in {"sleep", "tree"} else 2.0
    output_limit = 256 if case == "flood" else 64 * 1024
    memory_limit = 64 * 1024 * 1024 if case == "memory" else None
    outcome: ProcessOutcome | None = None
    receipt_sha: str | None = None
    receipt_issues: tuple[str, ...] = ()
    status = "INFRA_ERROR"
    explanation = "synthetic subprocess did not produce an outcome"
    try:
        outcome = run_fake_process(
            case,
            run_directory,
            timeout_seconds=timeout,
            output_byte_limit=output_limit,
            process_count_limit=8,
            memory_hard_limit_bytes=memory_limit,
        )
        matched, explanation = _expected_result(case, outcome)
        metadata = {
            "mode": "SELF_TEST",
            "evidence_class": _SELF_TEST_ONLY,
            "campaign_id": SYNTHETIC_CAMPAIGN_ID,
            "plan_sha256": plan_sha256,
            "run_id": run_id,
            "case_id": case,
            "attempt": 1,
            "runner_file_sha256": dict(runner_hashes),
            "supervisor_state": outcome.state,
            "return_code": outcome.return_code,
            "expected_behavior_matched": matched,
            "scientific_execution": False,
        }
        receipt_sha, _receipt_path = write_receipt(run_directory, metadata)
        receipt_issues = verify_receipt(run_directory)
        status = "PASS" if matched and not receipt_issues else "FAIL"
        if receipt_issues:
            explanation = "synthetic receipt verification failed"
    except Exception as exc:
        status = "INFRA_ERROR"
        explanation = f"synthetic orchestration error: {type(exc).__name__}"
        if run_directory.is_dir() and not (run_directory / "receipt.json").exists():
            try:
                receipt_sha, _receipt_path = write_receipt(
                    run_directory,
                    {
                        "mode": "SELF_TEST",
                        "evidence_class": _SELF_TEST_ONLY,
                        "campaign_id": SYNTHETIC_CAMPAIGN_ID,
                        "plan_sha256": plan_sha256,
                        "run_id": run_id,
                        "case_id": case,
                        "attempt": 1,
                        "infrastructure_error": type(exc).__name__,
                        "scientific_execution": False,
                    },
                )
                receipt_issues = verify_receipt(run_directory)
            except Exception:
                receipt_issues = ("partial synthetic receipt could not be sealed",)

    result = _result_record(
        case=case,
        run_id=run_id,
        self_test=status,
        explanation=explanation,
        outcome=outcome,
        receipt_sha256=receipt_sha,
        receipt_issues=receipt_issues,
        run_directory=run_directory if run_directory.is_dir() else None,
    )
    journal.append(
        {
            "event": "SYNTHETIC_UNIT_FINISHED",
            "campaign_id": SYNTHETIC_CAMPAIGN_ID,
            "plan_sha256": plan_sha256,
            "run_id": run_id,
            "case_id": case,
            "attempt": 1,
            "status": status,
            "finished_utc": _utc_now(),
            "receipt_sha256": receipt_sha,
            "stdout_sha256": result["stdout_sha256"],
            "stderr_sha256": result["stderr_sha256"],
            "scientific_execution": False,
        }
    )
    return result


def run_synthetic_orchestration(case_selector: str = "all") -> dict[str, Any]:
    """Run only predeclared fake-child cases and return their disposable receipts."""
    if REAL_EXECUTION_ENABLED:
        raise ContractError("SELF_TEST refuses to run when scientific EXECUTE is enabled")
    if not isinstance(case_selector, str):
        raise ContractError("SELF_TEST case selector must be text")
    if case_selector == "all":
        cases = SYNTHETIC_CASES
    elif case_selector in FAKE_CASES:
        cases = (case_selector,)
    else:
        raise ContractError("SELF_TEST accepts only the fixed synthetic case IDs")

    plan_sha256 = _plan_sha256(cases)
    runner_hashes = _runner_file_hashes()
    python_executable = Path(sys.executable)
    environment = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "python_executable_sha256": (
            sha256_file(python_executable)
            if python_executable.is_file() and not python_executable.is_symlink()
            else None
        ),
        "runner_file_sha256": runner_hashes,
    }
    with tempfile.TemporaryDirectory(prefix="qf-wp12-x-self-test-") as temporary:
        temporary_root = Path(temporary)
        journal = _SyntheticJournal(temporary_root / "lifecycle.jsonl")
        journal.append(
            {
                "event": "SYNTHETIC_CAMPAIGN_STARTED",
                "campaign_id": SYNTHETIC_CAMPAIGN_ID,
                "plan_sha256": plan_sha256,
                "case_ids": list(cases),
                "started_utc": _utc_now(),
                "scientific_execution": False,
            }
        )
        results: list[dict[str, Any]] = []
        for case in cases:
            result = _run_one_case(
                case,
                temporary_root=temporary_root,
                plan_sha256=plan_sha256,
                runner_hashes=runner_hashes,
                journal=journal,
            )
            results.append(result)
            if result["self_test"] == "INFRA_ERROR":
                break
        all_pass = all(result["self_test"] in {"PASS", "NOT_APPLICABLE"} for result in results)
        has_not_applicable = any(result["self_test"] == "NOT_APPLICABLE" for result in results)
        state = "PASS_WITH_NOT_APPLICABLE" if all_pass and has_not_applicable else "PASS" if all_pass else "FAIL"
        journal.append(
            {
                "event": "SYNTHETIC_CAMPAIGN_FINISHED",
                "campaign_id": SYNTHETIC_CAMPAIGN_ID,
                "plan_sha256": plan_sha256,
                "state": state,
                "finished_utc": _utc_now(),
                "scientific_execution": False,
            }
        )
        journal_issues = journal.verify()
        journal_sha256 = sha256_file(journal.path)
        journal_record_count = journal.record_count
        if journal_issues:
            state = "FAIL"
    return {
        "mode": "SELF_TEST",
        "campaign_id": SYNTHETIC_CAMPAIGN_ID,
        "result_kind": _SELF_TEST_ONLY,
        "state": state,
        "plan_sha256": plan_sha256,
        "runner_file_sha256": runner_hashes,
        "environment": environment,
        "case_ids": list(cases),
        "results": results,
        "journal_sha256": journal_sha256,
        "journal_chain_verified": not journal_issues,
        "journal_errors": list(journal_issues),
        "journal_record_count": journal_record_count,
        "temporary_evidence_discarded_after_report": True,
        "synthetic_case_invocations": sum(
            result["self_test"] != "NOT_APPLICABLE" for result in results
        ),
        "scientific_execution": False,
        "real_execute_enabled": False,
    }
