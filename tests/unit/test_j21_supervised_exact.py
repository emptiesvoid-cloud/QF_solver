from __future__ import annotations

import hashlib
import json
import sys
import threading
from pathlib import Path

import numpy as np
import psutil

from research.j21 import supervised_exact
from research.j21.synthetic_inputs import build_archive_payload, write_archive
from research.j21.supervised_exact import ProcessOutcome, SupervisorLimits, run_supervised_exact


ROOT = Path(__file__).resolve().parents[2]
PINNED_SOURCES = (
    "research/j21/exact_worker.py",
    "research/j21/supervised_exact.py",
    "research/j21/synthetic_inputs.py",
    "research/j17/exact_residual.py",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _archive(path: Path, *, matrix: np.ndarray, rhs: np.ndarray, solution: np.ndarray) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        path,
        impedance_real=matrix.real,
        impedance_imag=matrix.imag,
        rhs_real=rhs.real,
        rhs_imag=rhs.imag,
        x_unscaled_real=solution.real,
        x_unscaled_imag=solution.imag,
    )
    return _sha256(path)


def _contract(tmp_path: Path, cases: list[dict[str, object]]) -> tuple[Path, Path]:
    inputs = tmp_path / "inputs"
    sources = {relative: _sha256(ROOT / relative) for relative in PINNED_SOURCES}
    document = {
        "schema": "qfsolver-j21-supervised-exact-contract-v1",
        "contract_id": "J21-SYNTHETIC-SUPERVISOR-TEST",
        "state": "FROZEN_BEFORE_EXECUTION",
        "baseline": {"source_code_commit": "synthetic-test-source"},
        "source_hashes": sources,
        "limits": {
            "case_timeout_seconds": 8.0,
            "poll_interval_seconds": 0.01,
            "termination_grace_seconds": 0.1,
            "memory_soft_limit_mib": 512,
            "maximum_worker_result_bytes": 1_000_000,
            "max_dimension": 256,
            "max_nonzero_entries": 100_000,
            "max_fraction_bits": 65_536,
            "exact_time_budget_seconds": 5.0,
        },
        "criteria": {"tolerance": 1.0e-7},
        "cases": cases,
    }
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(json.dumps(document, indent=2), encoding="utf-8")
    return contract_path, inputs


def test_j21_supervisor_preserves_normal_exact_pass_and_fail(tmp_path: Path) -> None:
    pass_path = tmp_path / "inputs" / "pass.npz"
    pass_digest = _archive(
        pass_path,
        matrix=np.array([[2.0 + 0.0j]], dtype=np.complex128),
        rhs=np.array([2.0 + 0.0j]),
        solution=np.array([1.0 + 0.0j]),
    )
    fail_path = tmp_path / "inputs" / "fail.npz"
    fail_digest = _archive(
        fail_path,
        matrix=np.array([[2.0 + 0.0j]], dtype=np.complex128),
        rhs=np.array([0.0 + 0.0j]),
        solution=np.array([1.0 + 0.0j]),
    )
    contract_path, inputs = _contract(
        tmp_path,
        [
            {
                "case_id": "represented-pass",
                "input_path": "pass.npz",
                "input_sha256": pass_digest,
                "historical_guard_outcome": "NOT_APPLICABLE_SYNTHETIC",
            },
            {
                "case_id": "represented-fail",
                "input_path": "fail.npz",
                "input_sha256": fail_digest,
                "historical_guard_outcome": "NOT_APPLICABLE_SYNTHETIC",
            },
        ],
    )
    assert inputs == tmp_path / "inputs"
    journal = run_supervised_exact(
        contract_path,
        tmp_path / "run",
        repository_root=ROOT,
        input_root=tmp_path / "inputs",
    )

    assert journal["run_status"] == "COMPLETE"
    assert [case["exact_status"] for case in journal["cases"]] == ["PASS", "FAIL"]
    assert all(case["supervisor_status"] == "COMPLETE" for case in journal["cases"])
    assert all(case["historical_guard_outcome"] == "NOT_APPLICABLE_SYNTHETIC" for case in journal["cases"])
    assert json.loads((tmp_path / "run" / "supervisor.json").read_text(encoding="utf-8"))["run_status"] == "COMPLETE"


def test_j21_supervisor_preserves_duplicate_csr_entries(tmp_path: Path) -> None:
    archive_path = tmp_path / "inputs" / "duplicate-csr.npz"
    archive_path.parent.mkdir(parents=True)
    np.savez(archive_path, **build_archive_payload("duplicate_csr", 8))
    digest = _sha256(archive_path)
    contract_path, _ = _contract(
        tmp_path,
        [{"case_id": "duplicate-csr", "input_path": "duplicate-csr.npz", "input_sha256": digest}],
    )

    journal = run_supervised_exact(
        contract_path,
        tmp_path / "run",
        repository_root=ROOT,
        input_root=tmp_path / "inputs",
    )

    case = journal["cases"][0]
    assert journal["run_status"] == "COMPLETE"
    assert case["exact_status"] == "PASS"
    assert case["exact_result"]["stored_entries"] == 4 * 8 - 1
    assert case["exact_result"]["nonzero_entries"] == 4 * 8 - 1


def test_j21_synthetic_archive_bytes_are_reproducible(tmp_path: Path) -> None:
    first = write_archive(tmp_path / "first.npz", "duplicate_csr", 8)
    second = write_archive(tmp_path / "second.npz", "duplicate_csr", 8)
    assert _sha256(first) == _sha256(second)


def test_j21_supervisor_records_worker_exception_and_continues(tmp_path: Path) -> None:
    bad_path = tmp_path / "inputs" / "bad.npz"
    bad_path.parent.mkdir(parents=True)
    np.savez(bad_path, unrelated=np.ones(1))
    good_path = tmp_path / "inputs" / "good.npz"
    good_digest = _archive(
        good_path,
        matrix=np.eye(2, dtype=np.complex128),
        rhs=np.ones(2, dtype=np.complex128),
        solution=np.ones(2, dtype=np.complex128),
    )
    contract_path, _ = _contract(
        tmp_path,
        [
            {"case_id": "bad-archive", "input_path": "bad.npz", "input_sha256": _sha256(bad_path)},
            {"case_id": "good-archive", "input_path": "good.npz", "input_sha256": good_digest},
        ],
    )
    journal = run_supervised_exact(
        contract_path,
        tmp_path / "run",
        repository_root=ROOT,
        input_root=tmp_path / "inputs",
    )

    assert journal["run_status"] == "COMPLETE_WITH_INCONCLUSIVE_CASES"
    assert journal["cases"][0]["supervisor_status"] == "WORKER_EXCEPTION"
    assert journal["cases"][0]["exact_status"] == "INCONCLUSIVE"
    assert journal["cases"][1]["supervisor_status"] == "COMPLETE"
    assert journal["cases"][1]["exact_status"] == "PASS"


def test_j21_supervisor_timeout_kills_worker_and_observed_child_tree(tmp_path: Path) -> None:
    child_pid_path = tmp_path / "child.pid"
    child_code = "import time; time.sleep(30)"
    parent_code = (
        "import subprocess,sys,time,pathlib; "
        f"child=subprocess.Popen([sys.executable,'-c',{child_code!r}]); "
        f"pathlib.Path({str(child_pid_path)!r}).write_text(str(child.pid)); "
        "time.sleep(30)"
    )
    outcome = supervised_exact._run_external_process(
        [sys.executable, "-c", parent_code],
        cwd=tmp_path,
        limits=SupervisorLimits(
            case_timeout_seconds=0.5,
            poll_interval_seconds=0.01,
            termination_grace_seconds=0.1,
            memory_soft_limit_bytes=512 * 1024 * 1024,
        ),
        stop_requested=lambda: False,
    )

    assert outcome.state == "TIMED_OUT"
    assert outcome.termination_confirmed is True
    assert child_pid_path.is_file()
    child_pid = int(child_pid_path.read_text(encoding="utf-8"))
    assert child_pid in outcome.observed_process_pids
    assert not psutil.pid_exists(child_pid)


def test_j21_supervisor_memory_threshold_is_sampled_soft_and_terminates(tmp_path: Path) -> None:
    outcome = supervised_exact._run_external_process(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        cwd=tmp_path,
        limits=SupervisorLimits(
            case_timeout_seconds=5.0,
            poll_interval_seconds=0.01,
            termination_grace_seconds=0.1,
            memory_soft_limit_bytes=1,
        ),
        stop_requested=lambda: False,
    )

    assert outcome.state == "MEMORY_LIMIT_OBSERVED"
    assert outcome.peak_rss_bytes is not None and outcome.peak_rss_bytes > 1
    assert outcome.termination_confirmed is True


def test_j21_supervisor_interruption_preserves_complete_and_marks_remaining_inconclusive(
    tmp_path: Path,
    monkeypatch,
) -> None:
    first = tmp_path / "inputs" / "first.npz"
    first_digest = _archive(
        first,
        matrix=np.eye(1, dtype=np.complex128),
        rhs=np.ones(1, dtype=np.complex128),
        solution=np.ones(1, dtype=np.complex128),
    )
    second = tmp_path / "inputs" / "second.npz"
    second_digest = _archive(
        second,
        matrix=np.eye(1, dtype=np.complex128),
        rhs=np.ones(1, dtype=np.complex128),
        solution=np.ones(1, dtype=np.complex128),
    )
    contract_path, _ = _contract(
        tmp_path,
        [
            {"case_id": "first", "input_path": "first.npz", "input_sha256": first_digest},
            {"case_id": "second", "input_path": "second.npz", "input_sha256": second_digest},
            {"case_id": "third", "input_path": "first.npz", "input_sha256": first_digest},
        ],
    )
    stop = threading.Event()
    calls = 0

    def fake_process(command, *, cwd, limits, stop_requested):
        nonlocal calls
        calls += 1
        if calls == 1:
            result_path = Path(command[command.index("--result") + 1])
            case_id = command[command.index("--case-id") + 1]
            digest = command[command.index("--expected-sha256") + 1]
            result_path.write_text(json.dumps({
                "schema": "qfsolver-j21-exact-worker-result-v1",
                "case_id": case_id,
                "input_sha256": digest,
                "record_state": "COMPLETE",
                "exact_status": "PASS",
                "reason": "exact synthetic result",
            }), encoding="utf-8")
            return ProcessOutcome("EXITED", 0, 0.01, 10_000, 10, (10,), True)
        stop.set()
        return ProcessOutcome("INTERRUPTED", None, 0.02, 10_000, 11, (11,), True, "stop requested")

    monkeypatch.setattr(supervised_exact, "_run_external_process", fake_process)
    journal = run_supervised_exact(
        contract_path,
        tmp_path / "run",
        repository_root=ROOT,
        input_root=tmp_path / "inputs",
        stop_event=stop,
    )

    assert journal["run_status"] == "INTERRUPTED"
    assert journal["cases"][0]["exact_status"] == "PASS"
    assert journal["cases"][0]["supervisor_status"] == "COMPLETE"
    assert journal["cases"][1]["exact_status"] == "INCONCLUSIVE"
    assert journal["cases"][1]["supervisor_status"] == "INTERRUPTED"
    assert journal["cases"][2]["exact_status"] == "INCONCLUSIVE"
    assert journal["cases"][2]["supervisor_status"] == "NOT_STARTED"


def test_j21_supervisor_incomplete_worker_result_cannot_be_pass(monkeypatch, tmp_path: Path) -> None:
    archive = tmp_path / "inputs" / "empty.npz"
    digest = _archive(
        archive,
        matrix=np.eye(1, dtype=np.complex128),
        rhs=np.ones(1, dtype=np.complex128),
        solution=np.ones(1, dtype=np.complex128),
    )
    contract_path, _ = _contract(
        tmp_path,
        [{"case_id": "no-result", "input_path": "empty.npz", "input_sha256": digest}],
    )

    monkeypatch.setattr(
        supervised_exact,
        "_run_external_process",
        lambda *args, **kwargs: ProcessOutcome("EXITED", 0, 0.01, 0, 12, (12,), True),
    )
    journal = run_supervised_exact(
        contract_path,
        tmp_path / "run",
        repository_root=ROOT,
        input_root=tmp_path / "inputs",
    )

    case = journal["cases"][0]
    assert case["supervisor_status"] == "INCOMPLETE_RESULT"
    assert case["exact_status"] == "INCONCLUSIVE"
    assert journal["run_status"] == "COMPLETE_WITH_INCONCLUSIVE_CASES"


def test_j21_supervisor_stop_file_interrupts_child_process(tmp_path: Path) -> None:
    stop_file = tmp_path / "STOP"
    timer = threading.Timer(0.15, stop_file.touch)
    timer.start()
    try:
        outcome = supervised_exact._run_external_process(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            cwd=tmp_path,
            limits=SupervisorLimits(
                case_timeout_seconds=5.0,
                poll_interval_seconds=0.01,
                termination_grace_seconds=0.1,
            ),
            stop_requested=stop_file.exists,
        )
    finally:
        timer.cancel()

    assert outcome.state == "INTERRUPTED"
    assert outcome.termination_confirmed is True
    assert not psutil.pid_exists(outcome.worker_pid)
