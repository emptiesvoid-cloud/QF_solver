"""Bounded subprocess supervision for synthetic checks and one gated WP12 pilot."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
from typing import Callable, Mapping, Sequence

from .contracts import ContractError
from .evidence import JsonlJournal


_ROOT = Path(__file__).resolve().parents[2]
FAKE_CHILD = _ROOT / "tests" / "fixtures" / "wp12_runner" / "fake_child.py"
FAKE_CASES = frozenset({"success", "exit", "sleep", "tree", "flood", "memory", "cpu"})


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
    hard_job_enforced: bool = False
    process_started: bool = False
    cpu_limit_exceeded: bool = False


class _OutputCapture:
    def __init__(
        self,
        stdout_path: Path,
        stderr_path: Path,
        byte_limit: int,
        *,
        stream_byte_limits: Mapping[str, int] | None = None,
    ) -> None:
        self.paths = {"stdout": stdout_path, "stderr": stderr_path}
        self.byte_limit = byte_limit
        self.stream_byte_limits = dict(stream_byte_limits or {"stdout": byte_limit, "stderr": byte_limit})
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
                    stream_limit = self.stream_byte_limits[stream_name]
                    remaining = min(
                        max(0, self.byte_limit - self.total_written),
                        max(0, stream_limit - self.stream_written[stream_name]),
                    )
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
    memory_hard_limit_bytes: int | None = None,
    cpu_hard_limit_seconds: int | None = None,
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
    if memory_hard_limit_bytes is not None and memory_hard_limit_bytes < 1:
        raise ContractError("hard memory limit must be positive")
    if cpu_hard_limit_seconds is not None and cpu_hard_limit_seconds < 1:
        raise ContractError("hard CPU time limit must be positive")
    if os.name != "nt" and (memory_hard_limit_bytes is not None or cpu_hard_limit_seconds is not None):
        raise ContractError("requested hard memory or CPU limit requires a Windows Job Object")
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
    job = None
    hard_job_enforced = False
    started = time.monotonic()
    peak_rss: int | None = 0
    peak_processes = 0
    stop_reason: str | None = None
    remaining: tuple[int, ...] = ()
    process: subprocess.Popen[bytes] | None = None
    threads: list[threading.Thread] = []
    try:
        if os.name == "nt":
            from .windows_job import WindowsJob

            job = WindowsJob(
                process_count_limit=process_count_limit,
                memory_limit_bytes=memory_hard_limit_bytes,
                cpu_time_limit_seconds=cpu_hard_limit_seconds,
            )
            job.__enter__()
            creationflags |= getattr(subprocess, "CREATE_SUSPENDED", 0x00000004)
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
        if job is not None:
            job.assign_suspended_process(process)
            hard_job_enforced = True
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
        cpu_limit_exceeded = bool(job is not None and job.cpu_limit_exceeded())
        if cpu_limit_exceeded:
            state = "RESOURCE_LIMIT"
            stop_reason = "hard Windows Job Object user CPU-time limit exceeded"
            if job is not None and job.active_process_count() > 0:
                job.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    pass
                if job.active_process_count() > 0:
                    state = "INFRA_ERROR"
                    stop_reason = "processes remained active after CPU-time Job Object termination"
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
            cpu_limit_exceeded=cpu_limit_exceeded,
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
    except Exception as exc:
        if process is not None and process.poll() is None:
            try:
                process.kill()
                process.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                pass
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
            hard_job_enforced=hard_job_enforced,
            cpu_limit_exceeded=bool(job is not None and job.cpu_limit_exceeded()),
        )
    if job is not None:
        try:
            job.close()
        except OSError as exc:
            outcome = ProcessOutcome(
                state="INFRA_ERROR",
                return_code=outcome.return_code,
                stop_reason=f"Windows Job Object close failed: {type(exc).__name__}",
                elapsed_seconds=outcome.elapsed_seconds,
                stdout_bytes=outcome.stdout_bytes,
                stderr_bytes=outcome.stderr_bytes,
                sampled_peak_rss_bytes=outcome.sampled_peak_rss_bytes,
                sampled_peak_process_count=outcome.sampled_peak_process_count,
                child_pids_remaining=outcome.child_pids_remaining,
                hard_job_enforced=hard_job_enforced,
                cpu_limit_exceeded=outcome.cpu_limit_exceeded,
            )
    if hard_job_enforced and not outcome.hard_job_enforced:
        outcome = ProcessOutcome(
            state=outcome.state,
            return_code=outcome.return_code,
            stop_reason=outcome.stop_reason,
            elapsed_seconds=outcome.elapsed_seconds,
            stdout_bytes=outcome.stdout_bytes,
            stderr_bytes=outcome.stderr_bytes,
            sampled_peak_rss_bytes=outcome.sampled_peak_rss_bytes,
            sampled_peak_process_count=outcome.sampled_peak_process_count,
            child_pids_remaining=outcome.child_pids_remaining,
            hard_job_enforced=True,
            cpu_limit_exceeded=outcome.cpu_limit_exceeded,
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


def run_approved_pilot_process(
    command: Sequence[str],
    *,
    campaign_id: str,
    run_id: str,
    nodeid: str,
    manifest_sha256: str,
    cwd: Path,
    run_directory: Path,
    environment: Mapping[str, str],
    resource_limits: Mapping[str, object],
    interrupt_event: threading.Event | None = None,
    poll_interval_seconds: float = 0.05,
) -> ProcessOutcome:
    """Disabled scientific-process boundary.

    The existing SYSTEM worker verifies and copies evidence bytes but does not
    attest the identity or result of the launched child. Refuse here as well as
    in the CLI and pilot orchestrator, so callers cannot bypass preflight by
    invoking this low-level API directly. Synthetic process supervision uses a
    separate fixed fake-child path.
    """
    raise ContractError("SYSTEM_CHILD_PROCESS_ATTESTATION_NOT_IMPLEMENTED")


def validate_approved_pilot_command(
    command: Sequence[str],
    *,
    cwd: Path,
    run_directory: Path,
    python_executable: str,
    expected_nodeid: str,
) -> None:
    """Validate the single supported pytest argv without starting a process."""
    from .inline_fixtures import PILOT_NODEID

    if not command or any(not isinstance(item, str) or not item for item in command):
        raise ContractError("approved process argv is malformed")
    expected_prefix = [
        str(Path(python_executable).resolve()),
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        "-p",
        "scripts.wp12_runner.pytest_provenance_plugin",
    ]
    if (
        len(command) != 13
        or str(Path(command[0]).resolve()) != expected_prefix[0]
        or list(command[1:8]) != expected_prefix[1:]
        or list(command[8:10]) != ["-o", "addopts="]
        or command[10] != "--noconftest"
        or expected_nodeid != PILOT_NODEID
        or command[12] != expected_nodeid
    ):
        raise ContractError("approved process accepts only the exact WP12-1 pilot pytest command")
    junit_option = command[11]
    if not junit_option.startswith("--junitxml="):
        raise ContractError("approved process requires the pinned JUnit output argument")
    junit_path = Path(junit_option.removeprefix("--junitxml="))
    if not junit_path.is_absolute():
        junit_path = cwd / junit_path
    if junit_path.resolve(strict=False) != (run_directory / "junit.xml").resolve(strict=False):
        raise ContractError("approved JUnit output must be the exact reserved evidence file")


def classify_pytest_junit(xml_payload: bytes, expected_nodeid: str) -> str:
    """Classify one exact pytest testcase, rejecting absent or contradictory XML."""
    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(xml_payload)
    except ET.ParseError:
        return "INFRA_ERROR"
    if root.tag == "testsuite":
        suite = root
    elif root.tag == "testsuites":
        if any(child.tag != "testsuite" for child in root) or len(root) != 1:
            return "INFRA_ERROR"
        suite = root[0]
    else:
        return "INFRA_ERROR"
    if any(child.tag not in {"properties", "testcase"} for child in suite):
        return "INFRA_ERROR"
    cases = [child for child in suite if child.tag == "testcase"]
    if len(cases) != 1 or suite.findall(".//testsuite"):
        return "INFRA_ERROR"
    try:
        declared_tests = int(suite.get("tests", "-1"))
        declared_failures = int(suite.get("failures", "-1"))
        declared_errors = int(suite.get("errors", "-1"))
        declared_skipped = int(suite.get("skipped", "-1"))
    except ValueError:
        return "INFRA_ERROR"
    case = cases[0]
    if any(child.tag not in {"failure", "error", "skipped", "system-out", "system-err"} for child in case):
        return "INFRA_ERROR"
    failure_nodes = case.findall("failure")
    error_nodes = case.findall("error")
    skipped_nodes = case.findall("skipped")
    if len(failure_nodes) > 1 or len(error_nodes) > 1 or len(skipped_nodes) > 1:
        return "INFRA_ERROR"
    failure = failure_nodes[0] if failure_nodes else None
    error = error_nodes[0] if error_nodes else None
    skipped = skipped_nodes[0] if skipped_nodes else None
    actual_counts = (1, int(failure is not None), int(error is not None), int(skipped is not None))
    if (declared_tests, declared_failures, declared_errors, declared_skipped) != actual_counts:
        return "INFRA_ERROR"
    if root.tag == "testsuites":
        for name, actual in zip(("tests", "failures", "errors", "skipped"), actual_counts, strict=True):
            declared = root.get(name)
            if declared is not None:
                try:
                    if int(declared) != actual:
                        return "INFRA_ERROR"
                except ValueError:
                    return "INFRA_ERROR"
    node_path, _, test_path = expected_nodeid.partition("::")
    expected_module = node_path.removesuffix(".py").replace("/", ".")
    expected_name = test_path.split("::")[-1]
    if case.get("name") != expected_name or case.get("classname") not in {expected_module, Path(node_path).stem}:
        return "INFRA_ERROR"
    outcomes = sum(item is not None for item in (failure, error, skipped))
    if outcomes > 1:
        return "INFRA_ERROR"
    if failure is not None:
        return "FAIL"
    if error is not None:
        return "INFRA_ERROR"
    if skipped is not None:
        return "INCONCLUSIVE"
    return "PASS"


def classify_process_result(outcome: ProcessOutcome, junit_payload: bytes | None, expected_nodeid: str) -> str:
    """Combine the supervised process state with its exact one-test JUnit record."""
    if outcome.state in {"TIMEOUT", "RESOURCE_LIMIT", "INTERRUPTED", "INFRA_ERROR"}:
        return outcome.state
    if outcome.state != "PROCESS_EXITED" or outcome.return_code is None:
        return "INFRA_ERROR"
    if junit_payload is None:
        return "INFRA_ERROR"
    test_state = classify_pytest_junit(junit_payload, expected_nodeid)
    if outcome.return_code == 1 and test_state == "FAIL":
        return "FAIL"
    if outcome.return_code != 0:
        return "INFRA_ERROR"
    if test_state == "FAIL":
        return "INFRA_ERROR"
    return test_state
