"""Synthetic-only subprocess supervision used by WP12 runner self-tests.

There is intentionally no public arbitrary-command launch function.  Real WP12
execution remains disabled until Owner-signature trust and an OS sandbox with
the required hard limits are established.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
from typing import Callable

from .contracts import ContractError
from .evidence import JsonlJournal


_ROOT = Path(__file__).resolve().parents[2]
FAKE_CHILD = _ROOT / "tests" / "fixtures" / "wp12_runner" / "fake_child.py"
FAKE_CASES = frozenset({"success", "exit", "sleep", "tree", "flood"})


@dataclass(frozen=True)
class ResourceSample:
    process_count: int
    rss_bytes: int | None


@dataclass(frozen=True)
class ProcessOutcome:
    state: str
    return_code: int | None
    stop_reason: str | None
    elapsed_seconds: float
    stdout_bytes: int
    stderr_bytes: int
    sampled_peak_rss_bytes: int | None
    sampled_peak_process_count: int
    child_pids_remaining: tuple[int, ...]


class _OutputCapture:
    def __init__(self, stdout_path: Path, stderr_path: Path, byte_limit: int) -> None:
        self.paths = {"stdout": stdout_path, "stderr": stderr_path}
        self.byte_limit = byte_limit
        self.lock = threading.Lock()
        self.total_written = 0
        self.stream_written = {"stdout": 0, "stderr": 0}
        self.stream_seen = {"stdout": 0, "stderr": 0}
        self.exceeded = threading.Event()

    def drain(self, stream_name: str, pipe: object) -> None:
        path = self.paths[stream_name]
        with path.open("xb") as sink:
            while True:
                chunk = pipe.read(65536)  # type: ignore[attr-defined]
                if not chunk:
                    break
                with self.lock:
                    self.stream_seen[stream_name] += len(chunk)
                    remaining = max(0, self.byte_limit - self.total_written)
                    kept = chunk[:remaining]
                    if kept:
                        sink.write(kept)
                        self.total_written += len(kept)
                        self.stream_written[stream_name] += len(kept)
                    if len(kept) != len(chunk):
                        self.exceeded.set()


def _sample_process_tree(pid: int) -> ResourceSample:
    try:
        import psutil
    except ImportError:
        return ResourceSample(process_count=1, rss_bytes=None)
    try:
        root = psutil.Process(pid)
        processes = [root, *root.children(recursive=True)]
    except psutil.NoSuchProcess:
        return ResourceSample(process_count=0, rss_bytes=0)
    alive = 0
    rss = 0
    for process in processes:
        try:
            rss += process.memory_info().rss
            alive += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return ResourceSample(process_count=alive, rss_bytes=rss)


def _terminate_tree(process: subprocess.Popen[bytes]) -> tuple[int, ...]:
    if os.name == "nt":
        try:
            import psutil
        except ImportError:
            psutil = None  # type: ignore[assignment]
        descendants = []
        if psutil is not None:
            try:
                root = psutil.Process(process.pid)
                descendants = root.children(recursive=True)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                descendants = []
        else:
            descendants = []
        pids = [item.pid for item in descendants]
        for item in reversed(descendants):
            try:
                item.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):  # descendants exist only when psutil imported
                pass
        try:
            process.terminate()
        except OSError:
            pass
        if psutil is not None:
            try:
                psutil.wait_procs([*descendants, psutil.Process(process.pid)], timeout=0.5)
            except psutil.NoSuchProcess:
                pass
            for item in descendants:
                try:
                    if item.is_running():
                        item.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            try:
                if psutil.pid_exists(process.pid):
                    psutil.Process(process.pid).kill()
            except psutil.NoSuchProcess:
                pass
            remaining = tuple(pid for pid in pids if psutil.pid_exists(pid))
            return remaining
        try:
            result = subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                check=False,
                capture_output=True,
                timeout=5,
            )
            return () if result.returncode == 0 else tuple(pids)
        except (OSError, subprocess.TimeoutExpired):
            return tuple(pids)

    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=0.5)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass
    for _attempt in range(10):
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            return ()
        time.sleep(0.05)
    return (-process.pid,)


def run_fake_process(
    case: str,
    run_directory: Path,
    *,
    timeout_seconds: float = 2.0,
    output_byte_limit: int = 64 * 1024,
    process_count_limit: int = 8,
    memory_soft_limit_bytes: int | None = None,
    storage_soft_limit_bytes: int | None = None,
    poll_interval_seconds: float = 0.02,
    sample_provider: Callable[[int], ResourceSample] = _sample_process_tree,
    interrupt_event: threading.Event | None = None,
) -> ProcessOutcome:
    """Run one fixed fake-child case; never accepts caller-supplied argv."""
    if case not in FAKE_CASES:
        raise ContractError("SELF_TEST accepts only the fixed synthetic child cases")
    if not FAKE_CHILD.is_file() or FAKE_CHILD.is_symlink():
        raise ContractError("synthetic child fixture is missing or unsafe")
    if run_directory.exists() or run_directory.is_symlink():
        raise FileExistsError(f"refusing to reuse run directory: {run_directory}")
    if timeout_seconds <= 0 or output_byte_limit < 1 or process_count_limit < 1:
        raise ContractError("self-test limits must be positive")
    run_directory.mkdir(parents=True, exist_ok=False)
    journal = JsonlJournal(run_directory / "journal.jsonl")
    journal.append({"event": "RUNNING", "case": case, "utc_epoch": time.time()})
    stdout_path = run_directory / "stdout.bin"
    stderr_path = run_directory / "stderr.bin"
    capture = _OutputCapture(stdout_path, stderr_path, output_byte_limit)
    child_pid_path = run_directory / "child.pid"
    command = [sys.executable, str(FAKE_CHILD), case, str(child_pid_path)]
    environment = {
        name: value for name, value in os.environ.items() if name in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP"}
    }
    environment.update({"PYTHONHASHSEED": "0", "PYTHONIOENCODING": "utf-8"})
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
    started = time.monotonic()
    peak_rss: int | None = 0
    peak_processes = 0
    stop_reason: str | None = None
    remaining: tuple[int, ...] = ()
    process: subprocess.Popen[bytes] | None = None
    threads: list[threading.Thread] = []
    try:
        process = subprocess.Popen(
            command,
            cwd=run_directory,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            close_fds=True,
            creationflags=creationflags,
            start_new_session=(os.name != "nt"),
        )
        assert process.stdout is not None and process.stderr is not None
        threads = [
            threading.Thread(target=capture.drain, args=("stdout", process.stdout), daemon=True),
            threading.Thread(target=capture.drain, args=("stderr", process.stderr), daemon=True),
        ]
        for thread in threads:
            thread.start()
        state = "PROCESS_EXITED"
        while process.poll() is None:
            if interrupt_event is not None and interrupt_event.is_set():
                state = "INTERRUPTED"
                stop_reason = "synthetic interrupt event"
                remaining = _terminate_tree(process)
                break
            if capture.exceeded.is_set():
                state = "RESOURCE_LIMIT"
                stop_reason = "combined stdout/stderr byte limit exceeded"
                remaining = _terminate_tree(process)
                break
            if time.monotonic() - started > timeout_seconds:
                state = "TIMEOUT"
                stop_reason = "wall timeout exceeded"
                remaining = _terminate_tree(process)
                break
            sample = sample_provider(process.pid)
            peak_processes = max(peak_processes, sample.process_count)
            if sample.rss_bytes is not None:
                peak_rss = max(peak_rss or 0, sample.rss_bytes)
            if sample.process_count > process_count_limit:
                state = "RESOURCE_LIMIT"
                stop_reason = "sampled process-tree count exceeded configured soft limit"
                remaining = _terminate_tree(process)
                break
            if (
                memory_soft_limit_bytes is not None
                and sample.rss_bytes is not None
                and sample.rss_bytes > memory_soft_limit_bytes
            ):
                state = "RESOURCE_LIMIT"
                stop_reason = "sampled RSS exceeded configured soft limit; this is not a hard memory cap"
                remaining = _terminate_tree(process)
                break
            if storage_soft_limit_bytes is not None:
                current_size = sum(path.stat().st_size for path in run_directory.rglob("*") if path.is_file())
                if current_size > storage_soft_limit_bytes:
                    state = "RESOURCE_LIMIT"
                    stop_reason = "sampled evidence-directory size exceeded configured soft limit"
                    remaining = _terminate_tree(process)
                    break
            time.sleep(poll_interval_seconds)
        try:
            return_code = process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            remaining = _terminate_tree(process)
            return_code = process.poll()
            if state == "PROCESS_EXITED":
                state = "INFRA_ERROR"
                stop_reason = "process did not terminate after supervisor stop"
        for thread in threads:
            thread.join(timeout=2)
        if any(thread.is_alive() for thread in threads):
            state = "INFRA_ERROR"
            stop_reason = "output drain thread did not finish"
        if capture.exceeded.is_set() and state == "PROCESS_EXITED":
            state = "RESOURCE_LIMIT"
            stop_reason = "combined stdout/stderr byte limit exceeded"
        if remaining:
            state = "INFRA_ERROR"
            stop_reason = f"process descendants remain after termination: {remaining}"
        elapsed = time.monotonic() - started
        outcome = ProcessOutcome(
            state=state,
            return_code=return_code,
            stop_reason=stop_reason,
            elapsed_seconds=elapsed,
            stdout_bytes=capture.stream_seen["stdout"],
            stderr_bytes=capture.stream_seen["stderr"],
            sampled_peak_rss_bytes=peak_rss,
            sampled_peak_process_count=peak_processes,
            child_pids_remaining=remaining,
        )
    except KeyboardInterrupt:
        if process is not None:
            remaining = _terminate_tree(process)
        for thread in threads:
            thread.join(timeout=2)
        outcome = ProcessOutcome(
            state="INTERRUPTED" if not remaining else "INFRA_ERROR",
            return_code=process.poll() if process is not None else None,
            stop_reason="keyboard interrupt" if not remaining else f"descendants remain: {remaining}",
            elapsed_seconds=time.monotonic() - started,
            stdout_bytes=capture.stream_seen["stdout"],
            stderr_bytes=capture.stream_seen["stderr"],
            sampled_peak_rss_bytes=peak_rss,
            sampled_peak_process_count=peak_processes,
            child_pids_remaining=remaining,
        )
    except OSError as exc:
        outcome = ProcessOutcome(
            state="INFRA_ERROR",
            return_code=None,
            stop_reason=f"process launch/capture error: {type(exc).__name__}",
            elapsed_seconds=time.monotonic() - started,
            stdout_bytes=capture.stream_seen["stdout"],
            stderr_bytes=capture.stream_seen["stderr"],
            sampled_peak_rss_bytes=peak_rss,
            sampled_peak_process_count=peak_processes,
            child_pids_remaining=remaining,
        )
    journal.append(
        {
            "event": outcome.state,
            "return_code": outcome.return_code,
            "stop_reason": outcome.stop_reason,
            "elapsed_seconds": outcome.elapsed_seconds,
            "stdout_bytes": outcome.stdout_bytes,
            "stderr_bytes": outcome.stderr_bytes,
            "utc_epoch": time.time(),
        }
    )
    return outcome


def classify_pytest_junit(xml_payload: bytes, expected_nodeid: str) -> str:
    """Classify exactly one JUnit testcase without importing pytest or QF Solver."""
    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(xml_payload)
    except ET.ParseError:
        return "INFRA_ERROR"
    cases = root.findall(".//testcase")
    if len(cases) != 1:
        return "INFRA_ERROR"
    node_path, _, test_path = expected_nodeid.partition("::")
    expected_module = node_path.removesuffix(".py").replace("/", ".")
    expected_name = test_path.split("::")[-1]
    case = cases[0]
    if case.get("name") != expected_name or case.get("classname") not in {expected_module, Path(node_path).stem}:
        return "INFRA_ERROR"
    if case.find("failure") is not None:
        return "FAIL"
    if case.find("error") is not None:
        return "INFRA_ERROR"
    if case.find("skipped") is not None:
        return "INCONCLUSIVE"
    return "PASS"


def classify_process_result(outcome: ProcessOutcome, junit_payload: bytes | None, expected_nodeid: str) -> str:
    if outcome.state in {"TIMEOUT", "RESOURCE_LIMIT", "INTERRUPTED", "INFRA_ERROR"}:
        return outcome.state
    if junit_payload is None:
        return "INFRA_ERROR"
    test_state = classify_pytest_junit(junit_payload, expected_nodeid)
    if outcome.return_code != 0 and test_state == "PASS":
        return "INFRA_ERROR"
    return test_state
