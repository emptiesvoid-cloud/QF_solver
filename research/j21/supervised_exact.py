"""External process supervision for the bounded exact residual research tool.

The RSS threshold is sampled and soft, not an OS-enforced memory quota.
Timeout and process-tree termination are external to the exact evaluator, but
OS termination is still best effort and is recorded as such.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from research.j19.checkpoint import write_atomic_json

try:
    import psutil
except ImportError:  # pragma: no cover - tested through the missing-dependency path
    psutil = None  # type: ignore[assignment]


_EXACT_STATUSES = {"PASS", "FAIL", "INCONCLUSIVE"}
_CASE_ID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
_MAX_CASES_PER_RUN = 32
_MAX_INPUT_BYTES = 64 * 1024 * 1024
_MAX_EXTERNAL_TIMEOUT_SECONDS = 300.0


@dataclass(frozen=True)
class SupervisorLimits:
    case_timeout_seconds: float
    poll_interval_seconds: float = 0.05
    memory_soft_limit_bytes: int | None = None
    termination_grace_seconds: float = 0.25
    maximum_worker_result_bytes: int = 8 * 1024 * 1024

    def validate(self) -> None:
        for name, value in (
            ("case_timeout_seconds", self.case_timeout_seconds),
            ("poll_interval_seconds", self.poll_interval_seconds),
            ("termination_grace_seconds", self.termination_grace_seconds),
        ):
            if not math.isfinite(float(value)) or float(value) <= 0:
                raise ValueError(f"{name} must be a finite positive number")
        if self.memory_soft_limit_bytes is not None and (
            isinstance(self.memory_soft_limit_bytes, bool)
            or not isinstance(self.memory_soft_limit_bytes, int)
            or self.memory_soft_limit_bytes <= 0
        ):
            raise ValueError("memory_soft_limit_bytes must be a positive integer")
        if (
            isinstance(self.maximum_worker_result_bytes, bool)
            or not isinstance(self.maximum_worker_result_bytes, int)
            or self.maximum_worker_result_bytes <= 0
        ):
            raise ValueError("maximum_worker_result_bytes must be a positive integer")


@dataclass(frozen=True)
class ProcessOutcome:
    state: str
    return_code: int | None
    elapsed_seconds: float
    peak_rss_bytes: int | None
    worker_pid: int
    observed_process_pids: tuple[int, ...]
    termination_confirmed: bool | None
    reason: str | None = None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _source_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _process_tree_pids(root_pid: int) -> set[int]:
    if psutil is None:
        return {root_pid}
    pids = {root_pid}
    try:
        root = psutil.Process(root_pid)
        pids.update(child.pid for child in root.children(recursive=True))
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    return pids


def _process_tree_rss(root_pid: int) -> int | None:
    if psutil is None:
        return None
    try:
        root = psutil.Process(root_pid)
        processes = [root, *root.children(recursive=True)]
        return sum(process.memory_info().rss for process in processes)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None


def _pid_is_running(pid: int) -> bool:
    if psutil is None or not psutil.pid_exists(pid):
        return False
    try:
        return psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def _terminate_process_tree(
    process: subprocess.Popen[bytes],
    known_pids: set[int],
    grace_seconds: float,
) -> tuple[tuple[int, ...], bool]:
    pids = set(known_pids) | _process_tree_pids(process.pid)
    pids.add(process.pid)

    if os.name == "nt":
        taskkill = shutil.which("taskkill")
        if taskkill is not None:
            try:
                subprocess.run(
                    [taskkill, "/PID", str(process.pid), "/T", "/F"],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                    timeout=max(1.0, grace_seconds + 1.0),
                )
            except (OSError, subprocess.TimeoutExpired):
                pass
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass

    if psutil is not None:
        children = []
        for pid in sorted(pids, reverse=True):
            try:
                if psutil.pid_exists(pid):
                    children.append(psutil.Process(pid))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        for child in children:
            try:
                child.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        _, alive = psutil.wait_procs(children, timeout=grace_seconds)
        for child in alive:
            try:
                child.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        if alive:
            psutil.wait_procs(alive, timeout=max(0.1, grace_seconds))
    elif os.name != "nt":  # pragma: no cover - psutil is a declared test extra
        time.sleep(grace_seconds)
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass

    try:
        process.wait(timeout=max(1.0, grace_seconds + 1.0))
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except OSError:
            pass
        process.wait(timeout=1.0)

    ordered_pids = tuple(sorted(pids))
    confirmed = all(not _pid_is_running(pid) for pid in ordered_pids) if psutil is not None else process.poll() is not None
    return ordered_pids, confirmed


def _run_external_process(
    command: list[str],
    *,
    cwd: Path,
    limits: SupervisorLimits,
    stop_requested: Callable[[], bool],
) -> ProcessOutcome:
    limits.validate()
    if psutil is None:
        raise RuntimeError("psutil is required for process-tree monitoring and termination checks")
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env={
            **os.environ,
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        },
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=False,
        creationflags=creationflags,
        start_new_session=(os.name != "nt"),
    )
    started = time.monotonic()
    observed_pids: set[int] = {process.pid}
    peak_rss: int | None = None

    while True:
        observed_pids.update(_process_tree_pids(process.pid))
        return_code = process.poll()
        if return_code is not None:
            live_children = [pid for pid in observed_pids if pid != process.pid and psutil.pid_exists(pid)]
            if live_children:
                terminated, confirmed = _terminate_process_tree(
                    process, observed_pids, limits.termination_grace_seconds
                )
                return ProcessOutcome(
                    "CHILD_PROCESS_REMAINS", return_code, time.monotonic() - started,
                    peak_rss, process.pid, terminated, confirmed,
                    "worker exited while an observed descendant remained alive",
                )
            return ProcessOutcome(
                "EXITED", return_code, time.monotonic() - started, peak_rss, process.pid,
                tuple(sorted(observed_pids)), True, None,
            )

        if stop_requested():
            terminated, confirmed = _terminate_process_tree(
                process, observed_pids, limits.termination_grace_seconds
            )
            return ProcessOutcome(
                "INTERRUPTED", process.returncode, time.monotonic() - started,
                peak_rss, process.pid, terminated, confirmed, "stop requested",
            )

        elapsed = time.monotonic() - started
        if elapsed >= limits.case_timeout_seconds:
            terminated, confirmed = _terminate_process_tree(
                process, observed_pids, limits.termination_grace_seconds
            )
            return ProcessOutcome(
                "TIMED_OUT", process.returncode, time.monotonic() - started,
                peak_rss, process.pid, terminated, confirmed, "external wall-time limit reached",
            )

        current_rss = _process_tree_rss(process.pid)
        if current_rss is None:
            if limits.memory_soft_limit_bytes is not None:
                terminated, confirmed = _terminate_process_tree(
                    process, observed_pids, limits.termination_grace_seconds
                )
                return ProcessOutcome(
                    "MEMORY_MONITOR_UNAVAILABLE", process.returncode, time.monotonic() - started,
                    peak_rss, process.pid, terminated, confirmed,
                    "RSS sampling failed while a memory threshold was configured",
                )
        else:
            peak_rss = max(peak_rss or 0, current_rss)
            if limits.memory_soft_limit_bytes is not None and current_rss > limits.memory_soft_limit_bytes:
                terminated, confirmed = _terminate_process_tree(
                    process, observed_pids, limits.termination_grace_seconds
                )
                return ProcessOutcome(
                    "MEMORY_LIMIT_OBSERVED", process.returncode, time.monotonic() - started,
                    peak_rss, process.pid, terminated, confirmed,
                    "sampled process-tree RSS exceeded the configured soft threshold",
                )
        try:
            time.sleep(limits.poll_interval_seconds)
        except KeyboardInterrupt:
            terminated, confirmed = _terminate_process_tree(
                process, observed_pids, limits.termination_grace_seconds
            )
            return ProcessOutcome(
                "INTERRUPTED", process.returncode, time.monotonic() - started,
                peak_rss, process.pid, terminated, confirmed, "keyboard interrupt",
            )


def _validate_contract(contract: dict[str, Any], contract_path: Path, root: Path, data_root: Path) -> list[dict[str, Any]]:
    if contract.get("schema") != "qfsolver-j21-supervised-exact-contract-v1":
        raise ValueError("unsupported J21 contract schema")
    if contract.get("state") != "FROZEN_BEFORE_EXECUTION":
        raise ValueError("contract must be frozen before execution")
    cases = contract.get("cases")
    if not isinstance(cases, list) or not cases or len(cases) > _MAX_CASES_PER_RUN:
        raise ValueError(f"contract must contain between 1 and {_MAX_CASES_PER_RUN} cases")
    sources = contract.get("source_hashes")
    if not isinstance(sources, dict) or not sources:
        raise ValueError("contract must pin source files")
    for relative, expected in sources.items():
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("contract source path must be repository relative")
        source_path = (root / path).resolve()
        try:
            source_path.relative_to(root.resolve())
        except ValueError as exc:
            raise ValueError("contract source path resolves outside the repository root") from exc
        if sha256_file(source_path) != expected:
            raise ValueError(f"source SHA-256 mismatch: {relative}")
    seen: set[str] = set()
    validated: list[dict[str, Any]] = []
    for item in cases:
        if not isinstance(item, dict):
            raise ValueError("case entries must be objects")
        case_id = item.get("case_id")
        input_path = item.get("input_path")
        digest = item.get("input_sha256")
        if (
            not isinstance(case_id, str)
            or not case_id
            or any(character not in _CASE_ID_CHARS for character in case_id)
            or case_id in seen
        ):
            raise ValueError("case IDs must be unique safe filenames")
        if case_id in {".", ".."}:
            raise ValueError("case ID must not be a dot path component")
        if not isinstance(input_path, str):
            raise ValueError("input_path must be repository relative")
        relative_input = Path(input_path)
        if relative_input.is_absolute() or ".." in relative_input.parts:
            raise ValueError("input_path must not escape the input root")
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest.lower())
        ):
            raise ValueError("case input SHA-256 is malformed")
        data_path = (data_root / relative_input).resolve()
        try:
            data_path.relative_to(data_root.resolve())
        except ValueError as exc:
            raise ValueError("input_path resolves outside the input root") from exc
        if not data_path.is_file() or data_path.stat().st_size > _MAX_INPUT_BYTES:
            raise ValueError(f"case input is missing or exceeds the input byte limit: {input_path}")
        if sha256_file(data_path) != digest.lower():
            raise ValueError(f"case input is missing or its SHA-256 differs: {input_path}")
        seen.add(case_id)
        validated.append({**item, "input_sha256": digest.lower(), "resolved_input_path": data_path})
    limits = contract.get("limits")
    if not isinstance(limits, dict):
        raise ValueError("contract limits are required")
    contract_path.stat()
    return validated


def run_supervised_exact(
    contract_path: Path,
    output_directory: Path,
    *,
    repository_root: Path | None = None,
    input_root: Path | None = None,
    stop_file: Path | None = None,
    stop_event: threading.Event | None = None,
) -> dict[str, Any]:
    """Run pinned exact checks in separate processes and atomically journal progress."""
    root = (repository_root or _source_root()).resolve()
    data_root = (input_root or root).resolve()
    contract_path = Path(contract_path).resolve()
    output = Path(output_directory).resolve()
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    cases = _validate_contract(contract, contract_path, root, data_root)
    limits_data = contract["limits"]
    memory_mib = limits_data.get("memory_soft_limit_mib")
    if memory_mib is not None and (isinstance(memory_mib, bool) or not isinstance(memory_mib, int) or memory_mib <= 0):
        raise ValueError("memory_soft_limit_mib must be a positive integer")
    timeout = limits_data.get("case_timeout_seconds")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(float(timeout)):
        raise ValueError("case_timeout_seconds must be a finite number")
    if timeout <= 0 or timeout > _MAX_EXTERNAL_TIMEOUT_SECONDS:
        raise ValueError(f"case_timeout_seconds must be in (0, {_MAX_EXTERNAL_TIMEOUT_SECONDS}]")
    for key, maximum in (
        ("max_dimension", 256),
        ("max_nonzero_entries", 100_000),
        ("max_fraction_bits", 65_536),
    ):
        value = limits_data.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0 or value > maximum:
            raise ValueError(f"{key} must be in [1, {maximum}]")
    exact_time_budget = limits_data.get("exact_time_budget_seconds")
    if (
        isinstance(exact_time_budget, bool)
        or not isinstance(exact_time_budget, (int, float))
        or not math.isfinite(float(exact_time_budget))
        or exact_time_budget <= 0
        or exact_time_budget > _MAX_EXTERNAL_TIMEOUT_SECONDS
    ):
        raise ValueError("exact_time_budget_seconds is outside the supported range")
    limits = SupervisorLimits(
        case_timeout_seconds=float(timeout),
        poll_interval_seconds=float(limits_data.get("poll_interval_seconds", 0.05)),
        memory_soft_limit_bytes=None if memory_mib is None else memory_mib * 1024 * 1024,
        termination_grace_seconds=float(limits_data.get("termination_grace_seconds", 0.25)),
        maximum_worker_result_bytes=int(limits_data.get("maximum_worker_result_bytes", 8 * 1024 * 1024)),
    )
    limits.validate()
    if psutil is None:
        raise RuntimeError("psutil is required; no child process was started")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("supervisor output directory is nonempty; refusing to overwrite a previous run")
    output.mkdir(parents=True, exist_ok=True)

    journal: dict[str, Any] = {
        "schema": "qfsolver-j21-supervised-exact-run-v1",
        "contract_id": contract["contract_id"],
        "contract_sha256": sha256_file(contract_path),
        "source_code_commit": contract.get("baseline", {}).get("source_code_commit"),
        "execution_source_commit": _git_head(root),
        "run_status": "RUNNING",
        "classification": "EXACT_REPRESENTED_SYSTEM_REVIEW_NO_FEM_ASSEMBLY",
        "environment": {
            "python": sys.version.split()[0],
            "platform": sys.platform,
            "psutil": psutil.__version__,
        },
        "limits": {
            **limits_data,
            "memory_semantics": "sampled_soft_threshold_not_an_OS_quota",
            "timeout_semantics": "external_watchdog_with_process_tree_termination_best_effort",
        },
        "cases": [],
    }
    for item in cases:
        journal["cases"].append({
            "case_id": item["case_id"],
            "frequency_hz": item.get("frequency_hz"),
            "input_path": item["input_path"],
            "input_sha256": item["input_sha256"],
            "historical_guard_outcome": item.get("historical_guard_outcome"),
            "supervisor_status": "NOT_STARTED",
            "exact_status": "INCONCLUSIVE",
            "reason": "case has not completed; default is not PASS",
        })
    checkpoint = output / "supervisor.json"
    write_atomic_json(checkpoint, journal)

    def stopped() -> bool:
        return (stop_event is not None and stop_event.is_set()) or (stop_file is not None and Path(stop_file).exists())

    stop_reason: str | None = None
    for item, record in zip(cases, journal["cases"], strict=True):
        if stopped():
            stop_reason = "INTERRUPTED"
            record["reason"] = "run interrupted before this case started"
            break
        record.update(supervisor_status="RUNNING", reason="worker is running")
        write_atomic_json(checkpoint, journal)
        worker_result_path = output / f"{item['case_id']}.worker.json"
        if worker_result_path.exists():
            raise FileExistsError("worker result already exists; refusing to overwrite")
        command = [
            sys.executable,
            "-m",
            "research.j21.exact_worker",
            "--input",
            str(item["resolved_input_path"]),
            "--expected-sha256",
            item["input_sha256"],
            "--result",
            str(worker_result_path),
            "--case-id",
            item["case_id"],
            "--tolerance",
            str(float(contract.get("criteria", {}).get("tolerance", 1.0e-7))),
            "--max-dimension",
            str(int(limits_data["max_dimension"])),
            "--max-nonzero-entries",
            str(int(limits_data["max_nonzero_entries"])),
            "--max-fraction-bits",
            str(int(limits_data["max_fraction_bits"])),
            "--max-elapsed-seconds",
            str(float(limits_data["exact_time_budget_seconds"])),
        ]
        outcome = _run_external_process(
            command,
            cwd=root,
            limits=limits,
            stop_requested=stopped,
        )
        record.update(
            worker_pid=outcome.worker_pid,
            observed_process_pids=list(outcome.observed_process_pids),
            elapsed_seconds=outcome.elapsed_seconds,
            peak_rss_bytes_sampled=outcome.peak_rss_bytes,
            worker_return_code=outcome.return_code,
            termination_confirmed=outcome.termination_confirmed,
        )
        if outcome.state != "EXITED":
            record.update(
                supervisor_status=outcome.state,
                exact_status="INCONCLUSIVE",
                reason=outcome.reason or outcome.state,
            )
            stop_reason = "INTERRUPTED" if outcome.state == "INTERRUPTED" else outcome.state
            write_atomic_json(checkpoint, journal)
            break

        if outcome.return_code != 0:
            record.update(
                supervisor_status="WORKER_EXCEPTION",
                exact_status="INCONCLUSIVE",
                reason="worker exited nonzero; any worker PASS is discarded",
            )
            if worker_result_path.is_file() and worker_result_path.stat().st_size <= limits.maximum_worker_result_bytes:
                try:
                    child_record = json.loads(worker_result_path.read_text(encoding="utf-8"))
                    record["worker_exception_type"] = child_record.get("reason", "worker error")
                except (OSError, ValueError):
                    pass
            write_atomic_json(checkpoint, journal)
            continue

        if not worker_result_path.is_file():
            record.update(
                supervisor_status="INCOMPLETE_RESULT",
                exact_status="INCONCLUSIVE",
                reason="worker exited successfully without a durable result",
            )
            write_atomic_json(checkpoint, journal)
            continue
        if worker_result_path.stat().st_size > limits.maximum_worker_result_bytes:
            record.update(
                supervisor_status="INCOMPLETE_RESULT",
                exact_status="INCONCLUSIVE",
                reason="worker result exceeded the configured byte limit",
            )
            write_atomic_json(checkpoint, journal)
            continue
        record["worker_result_sha256"] = sha256_file(worker_result_path)
        record["worker_result_bytes"] = worker_result_path.stat().st_size
        try:
            child_record = json.loads(worker_result_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            child_record = None
        if (
            not isinstance(child_record, dict)
            or child_record.get("schema") != "qfsolver-j21-exact-worker-result-v1"
            or child_record.get("case_id") != item["case_id"]
            or child_record.get("input_sha256") != item["input_sha256"]
            or child_record.get("record_state") != "COMPLETE"
            or child_record.get("exact_status") not in _EXACT_STATUSES
            or not isinstance(child_record.get("reason"), str)
        ):
            record.update(
                supervisor_status="INCOMPLETE_RESULT",
                exact_status="INCONCLUSIVE",
                reason="worker result is missing, partial, or inconsistent with the pinned input",
            )
        else:
            record.update(
                supervisor_status="COMPLETE",
                exact_status=child_record["exact_status"],
                reason=child_record["reason"],
                exact_result={key: value for key, value in child_record.items() if key not in {
                    "schema", "case_id", "input_sha256", "record_state", "exact_status", "reason"
                }},
            )
        write_atomic_json(checkpoint, journal)

    if stop_reason is not None:
        for record in journal["cases"]:
            if record["supervisor_status"] == "NOT_STARTED":
                record["reason"] = "case not run after supervisor interruption; default is INCONCLUSIVE"
        journal["run_status"] = stop_reason
    elif all(record["supervisor_status"] == "COMPLETE" for record in journal["cases"]):
        journal["run_status"] = "COMPLETE"
    else:
        journal["run_status"] = "COMPLETE_WITH_INCONCLUSIVE_CASES"
    write_atomic_json(checkpoint, journal)
    return journal


def _git_head(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, timeout=3.0,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--repository-root", type=Path, default=_source_root())
    parser.add_argument("--input-root", type=Path)
    parser.add_argument("--stop-file", type=Path)
    args = parser.parse_args(argv)
    stop_event = threading.Event()
    previous_handlers: dict[int, Any] = {}

    def request_stop(_signum: int, _frame: Any) -> None:
        stop_event.set()

    for signum in (signal.SIGINT, signal.SIGTERM):
        try:
            previous_handlers[signum] = signal.signal(signum, request_stop)
        except (ValueError, OSError):
            pass
    try:
        journal = run_supervised_exact(
            args.contract,
            args.output,
            repository_root=args.repository_root,
            input_root=args.input_root,
            stop_file=args.stop_file,
            stop_event=stop_event,
        )
    except Exception as exc:
        print(f"supervisor preflight failed: {type(exc).__name__}", file=sys.stderr)
        return 2
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
    return 0 if journal["run_status"] == "COMPLETE" else 2


if __name__ == "__main__":
    sys.exit(main())
