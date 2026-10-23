"""Bounded, noninteractive pytest launcher for local development only.

This is a workflow/resource monitor, not a sandbox. It intentionally exposes
fixed pytest scopes instead of an arbitrary command execution interface.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Iterator, Mapping, Sequence

try:
    import psutil
except ImportError:  # pragma: no cover - exercised only in an incomplete dev install
    psutil = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "development_autonomous_policy.json"
SERIES_RE = re.compile(r"^dev-[a-z0-9][a-z0-9-]{7,48}$")
STANDARD_SCOPES = {"unit", "integration"}
WORKTREE_SCOPES = {"fem_exploratory", "math_non_fem"}
OWNER_ENV_KEYS = {
    "WPC02_AR_NATIVE_OWNER_GO_TOKEN",
    "WPC02_AR_NATIVE_OWNER_GO_MANIFEST_SHA256",
    "QF_SOLVER_RUN_EVIDENCE",
    "QF_SOLVER_RUN_RECOVERED_EVIDENCE",
    "QF_SOLVER_EVIDENCE_ARCHIVE_ROOT",
}


class PolicyError(ValueError):
    """A development run is outside the repository policy."""


@dataclass(frozen=True)
class ProcessResult:
    status: str
    return_code: int | None
    elapsed_seconds: float
    peak_rss_bytes: int
    peak_process_count: int
    stdout_bytes: int
    stderr_bytes: int
    archive_bytes: int
    temporary_bytes: int
    stop_reason: str | None


def _positive_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PolicyError(f"policy field {name} must be a positive number")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise PolicyError(f"policy field {name} must be a finite positive number") from exc
    if not math.isfinite(number) or number <= 0:
        raise PolicyError(f"policy field {name} must be a positive number")
    return number


def _positive_integer(value: Any, name: str) -> int:
    number = _positive_number(value, name)
    if not number.is_integer():
        raise PolicyError(f"policy field {name} must be an integer")
    return int(number)


def load_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    if not _is_within(path.resolve(), ROOT.resolve()):
        raise PolicyError("development policy must be stored inside this worktree")
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyError(f"cannot read development policy: {exc}") from exc
    if not isinstance(policy, dict) or policy.get("schema") != "qfsolver-development-autonomous-v2":
        raise PolicyError("unsupported development policy schema")
    if policy.get("mode") != "DEVELOPMENT_AUTONOMOUS":
        raise PolicyError("this launcher only accepts DEVELOPMENT_AUTONOMOUS")
    store = Path(str(policy.get("run_store", "")))
    if store.as_posix() != ".codex/development-runs":
        raise PolicyError("run_store must be the dedicated .codex/development-runs directory")
    _positive_number(policy.get("minimum_free_disk_mib"), "minimum_free_disk_mib")
    poll = _positive_number(policy.get("poll_interval_seconds"), "poll_interval_seconds")
    if poll > 5:
        raise PolicyError("poll_interval_seconds must not exceed 5")
    if not isinstance(policy.get("mandate_id"), str) or not policy["mandate_id"].startswith("DEVELOPMENT_AUTONOMOUS-"):
        raise PolicyError("a development-only mandate ID is required")
    scopes = policy.get("standard_scopes")
    expected_roots = {"unit": "tests/unit", "integration": "tests/integration"}
    if not isinstance(scopes, dict) or set(scopes) != set(expected_roots):
        raise PolicyError("only the fixed unit and integration scopes are accepted here")
    for name, scope in scopes.items():
        if not isinstance(scope, dict):
            raise PolicyError(f"scope {name} must be an object")
        for field in (
            "timeout_seconds",
            "rss_soft_limit_mib",
            "process_tree_limit",
            "output_total_limit_mib",
            "output_stream_limit_mib",
            "temporary_limit_mib",
            "archive_size_limit_mib",
            "max_attempts_per_series",
        ):
            _positive_number(scope.get(field), f"scopes.{name}.{field}")
        for field in ("process_tree_limit", "max_attempts_per_series"):
            _positive_integer(scope.get(field), f"scopes.{name}.{field}")
        if scope.get("pytest_root") != expected_roots[name]:
            raise PolicyError(f"scope {name} is bound to its fixed repository test directory")
        if name in STANDARD_SCOPES and scope.get("markers") != "not evidence and not benchmark and not large":
            raise PolicyError(f"scope {name} must exclude controlled evidence, benchmark, and large tests")
        if scope["output_total_limit_mib"] > 2 * scope["output_stream_limit_mib"]:
            raise PolicyError(f"scope {name} total output limit exceeds its two stream limits")
    worktrees = policy.get("worktrees")
    if not isinstance(worktrees, dict) or set(worktrees) != {"d01", "c01", "e01"}:
        raise PolicyError("the authorized worktree registry must contain exactly d01, c01, and e01")
    required_budget_fields = (
        "timeout_seconds",
        "rss_soft_limit_mib",
        "process_tree_limit",
        "output_total_limit_mib",
        "output_stream_limit_mib",
        "temporary_limit_mib",
        "archive_size_limit_mib",
    )
    for worktree_id, entry in worktrees.items():
        if not isinstance(entry, dict):
            raise PolicyError(f"worktree {worktree_id} must be an object")
        expected_mode = "math_non_fem" if worktree_id == "e01" else "fem_exploratory"
        if entry.get("mode") != expected_mode:
            raise PolicyError(f"worktree {worktree_id} has an unauthorized execution mode")
        for field in ("root", "git_root", "branch", "baseline_commit", "source_root", "pytest_root"):
            if not isinstance(entry.get(field), str) or not entry[field]:
                raise PolicyError(f"worktree {worktree_id} requires {field}")
        if not re.fullmatch(r"[0-9a-f]{40}", entry["baseline_commit"]):
            raise PolicyError(f"worktree {worktree_id} baseline_commit must be a full Git SHA-1")
        if Path(entry["root"]).resolve() != Path(entry["git_root"]).resolve():
            raise PolicyError(f"worktree {worktree_id} root and git_root must be identical")
        nodeids = entry.get("allowed_nodeids")
        if not isinstance(nodeids, list) or not nodeids or len(nodeids) != len(set(nodeids)):
            raise PolicyError(f"worktree {worktree_id} requires unique exact nodeids")
        if entry.get("allow_native_vv_skip_override") is not (worktree_id == "d01"):
            raise PolicyError("only the exact D01 M3 development node may lift its native-V&V skip")
        attempt_limit = _positive_integer(entry.get("attempt_limit_per_nodeid"), f"worktrees.{worktree_id}.attempt_limit_per_nodeid")
        if attempt_limit != 3:
            raise PolicyError("this Owner mandate permits at most three attempts per nodeid")
        budgets = entry.get("budgets")
        if not isinstance(budgets, dict):
            raise PolicyError(f"worktree {worktree_id} requires a budgets object")
        for field in required_budget_fields:
            _positive_number(budgets.get(field), f"worktrees.{worktree_id}.budgets.{field}")
        for field in ("process_tree_limit",):
            _positive_integer(budgets[field], f"worktrees.{worktree_id}.budgets.{field}")
        if budgets["output_total_limit_mib"] > 2 * budgets["output_stream_limit_mib"]:
            raise PolicyError(f"worktree {worktree_id} aggregate output exceeds its two stream caps")
        expected_test_root = "tests/unit" if worktree_id in {"c01", "e01"} else "tests/verification"
        if entry["pytest_root"] != expected_test_root:
            raise PolicyError(f"worktree {worktree_id} is bound to the wrong test class")
        for nodeid in nodeids:
            if not isinstance(nodeid, str) or "::" not in nodeid:
                raise PolicyError(f"worktree {worktree_id} contains a non-nodeid target")
            test_path = Path(nodeid.split("::", maxsplit=1)[0])
            if test_path.is_absolute() or ".." in test_path.parts or not nodeid.startswith(expected_test_root + "/"):
                raise PolicyError(f"worktree {worktree_id} nodeid escapes its approved test root")
            if worktree_id == "e01" and re.search(r"(?i)(tet|hex|beam|assembly|fem)", nodeid):
                raise PolicyError("E01 allowlist may contain only non-FEM constitutive-math tests")
    if worktrees["d01"]["allowed_nodeids"] != [
        "tests/verification/test_wp_d01_bj_wp05_native_experiment.py::test_wp05_native_modal_and_residual_flexibility_characterization[M3]"
    ]:
        raise PolicyError("D01 development permission is limited to the exact M3 diagnostic node")
    return policy


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def resolve_targets(
    scope_name: str,
    target: str | None,
    policy: Mapping[str, Any],
    *,
    worktree_id: str | None = None,
) -> list[str]:
    if scope_name in WORKTREE_SCOPES:
        if worktree_id not in policy["worktrees"]:
            raise PolicyError("a registered worktree ID is required for this scope")
        entry = policy["worktrees"][worktree_id]
        if entry["mode"] != scope_name:
            raise PolicyError(f"worktree {worktree_id} is not authorized for {scope_name}")
        if not target or target not in entry["allowed_nodeids"]:
            raise PolicyError("target must be one exact nodeid in the registered worktree allowlist")
        path_text = target.split("::", maxsplit=1)[0]
        candidate = (Path(entry["root"]) / path_text).resolve()
        scope_root = (Path(entry["root"]) / entry["pytest_root"]).resolve()
        if not _is_within(candidate, scope_root) or not candidate.is_file():
            raise PolicyError("registered nodeid resolves outside its canonical worktree test root")
        return [target]

    if scope_name not in STANDARD_SCOPES:
        raise PolicyError(f"unsupported development scope: {scope_name}")
    if worktree_id is not None:
        raise PolicyError("standard local scopes do not accept an external worktree ID")
    scope = policy["standard_scopes"][scope_name]
    scope_root = (ROOT / scope["pytest_root"]).resolve()
    if target is None:
        raise PolicyError("standard development scopes require one explicit test function; broad suites are not auto-enabled")
    if "::" not in target or not target.rsplit("::", maxsplit=1)[-1].startswith("test_"):
        raise PolicyError("standard development scopes require one exact pytest test-function nodeid")
    path_text = target.split("::", maxsplit=1)[0]
    relative = Path(path_text)
    if relative.is_absolute() or ".." in relative.parts:
        raise PolicyError("test target must be repository-relative and cannot traverse parents")
    candidate = (ROOT / relative).resolve()
    if (
        not _is_within(candidate, scope_root)
        or not candidate.is_file()
        or candidate.suffix != ".py"
        or not candidate.name.startswith("test_")
    ):
        raise PolicyError(f"target must be a test module below {scope['pytest_root']}")
    return [target]


def build_pytest_command(
    scope_name: str,
    targets: Sequence[str],
    temp_dir: Path,
    *,
    repository_root: Path = ROOT,
    source_root: Path | None = None,
    controller_root: Path = ROOT,
    allow_native_skip_override: bool = False,
) -> list[str]:
    if scope_name in WORKTREE_SCOPES:
        if len(targets) != 1 or source_root is None:
            raise PolicyError("registered worktree execution requires one exact nodeid and a source root")
        native_override = "True" if allow_native_skip_override else "False"
        bootstrap = "\n".join(
            (
                "from pathlib import Path",
                "import sys",
                "src = Path(sys.argv[1]).resolve()",
                "root = Path(sys.argv[2]).resolve()",
                "controller = Path(sys.argv[3]).resolve()",
                "mode = sys.argv[4]",
                "target = sys.argv[5]",
                "sys.path.insert(0, str(src))",
                "sys.path.insert(0, str(controller / 'scripts'))",
                "import solveur",
                "origin = Path(solveur.__file__).resolve()",
                "expected = (src / 'solveur' / '__init__.py').resolve()",
                "print('QF_DEV_SOLVER_ORIGIN=' + str(origin))",
                "if origin != expected:",
                "    raise SystemExit('wrong solveur import origin: ' + str(origin))",
                "import pytest",
                "from development_autonomous_pytest_plugin import ExactNodeGate",
                f"gate = ExactNodeGate((target,), allow_native_skip_override=(mode == 'd01' and {native_override}))",
                "raise SystemExit(pytest.main(sys.argv[6:], plugins=[gate]))",
            )
        )
        return [
            sys.executable,
            "-B",
            "-c",
            bootstrap,
            str(source_root),
            str(repository_root),
            str(controller_root),
            "d01" if allow_native_skip_override else "registered",
            targets[0],
            "-q",
            "-p",
            "no:cacheprovider",
            "--basetemp",
            str(temp_dir),
            targets[0],
        ]
    command = [
        sys.executable,
        "-B",
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        "--basetemp",
        str(temp_dir),
    ]
    if scope_name in STANDARD_SCOPES:
        command.extend(["-m", "not evidence and not benchmark and not large"])
    command.extend(targets)
    return command


def build_child_environment(
    temp_dir: Path,
    base: Mapping[str, str] | None = None,
    *,
    source_root: Path | None = None,
    d01_source_sha: str | None = None,
) -> dict[str, str]:
    environment = dict(os.environ if base is None else base)
    for key in tuple(environment):
        if key in OWNER_ENV_KEYS or (key.startswith("QF_") and ("OWNER" in key or "QUALIFICATION" in key)):
            environment.pop(key, None)
    environment.pop("PYTEST_ADDOPTS", None)
    environment.pop("PYTEST_PLUGINS", None)
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONSTARTUP", None)
    environment["QF_SOLVER_RUN_EVIDENCE"] = "0"
    environment["QF_SOLVER_RUN_RECOVERED_EVIDENCE"] = "0"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["TMP"] = str(temp_dir)
    environment["TEMP"] = str(temp_dir)
    environment["TMPDIR"] = str(temp_dir)
    if source_root is not None:
        environment["PYTHONPATH"] = str(source_root)
    if d01_source_sha is not None:
        environment["QF_WP_D01_BJ_SOURCE_SHA"] = d01_source_sha
    environment["QF_DEVELOPMENT_AUTONOMOUS"] = "1"
    return environment


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
        temporary = Path(stream.name)
    os.replace(temporary, path)


def _archive_size(path: Path) -> int:
    total = 0
    for item in path.rglob("*"):
        try:
            if item.is_file():
                total += item.stat().st_size
        except OSError:
            continue
    return total


def _directory_size(path: Path) -> int:
    return _archive_size(path) if path.exists() else 0


def _process_snapshot(pid: int) -> tuple[int, int]:
    if psutil is None:
        raise PolicyError("psutil is required for monitored development execution")
    try:
        root = psutil.Process(pid)
        processes = [root, *root.children(recursive=True)]
    except psutil.NoSuchProcess:
        return 0, 0
    alive = []
    rss = 0
    for process in processes:
        try:
            if process.is_running() and process.status() != psutil.STATUS_ZOMBIE:
                alive.append(process)
                rss += process.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return len(alive), rss


def _terminate_tree(pid: int) -> None:
    if psutil is None:
        return
    try:
        root = psutil.Process(pid)
        children = root.children(recursive=True)
    except psutil.NoSuchProcess:
        return
    processes = list(reversed(children)) + [root]
    for process in processes:
        try:
            process.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    _gone, alive = psutil.wait_procs(processes, timeout=2)
    for process in alive:
        try:
            process.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    psutil.wait_procs(alive, timeout=2)


def run_supervised_command(
    command: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    output_dir: Path,
    temporary_dir: Path | None = None,
    limits: Mapping[str, Any],
    poll_interval: float = 0.25,
) -> ProcessResult:
    """Run a child noninteractively with bounded capture and monitored resources."""
    if psutil is None:
        raise PolicyError("psutil is required; install the project test/dev dependencies before launching")
    output_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = output_dir / "stdout.log"
    stderr_path = output_dir / "stderr.log"
    total_cap = int(limits["output_total_limit_mib"] * 1024 * 1024)
    stream_cap = int(limits["output_stream_limit_mib"] * 1024 * 1024)
    archive_cap = int(limits["archive_size_limit_mib"] * 1024 * 1024)
    temporary_dir = output_dir if temporary_dir is None else temporary_dir
    temporary_cap = int(limits.get("temporary_limit_mib", limits["archive_size_limit_mib"]) * 1024 * 1024)
    free_disk_floor = int(limits.get("minimum_free_disk_mib", 0) * 1024 * 1024)
    rss_cap = int(limits["rss_soft_limit_mib"] * 1024 * 1024)
    process_cap = int(limits["process_tree_limit"])
    timeout = float(limits["timeout_seconds"])

    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
    process = subprocess.Popen(
        list(command),
        cwd=cwd,
        env=dict(environment),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=creationflags,
        start_new_session=(os.name != "nt"),
        bufsize=0,
    )
    state_lock = threading.Lock()
    output_exceeded = threading.Event()
    capture = {"observed": {"stdout": 0, "stderr": 0}, "saved": {"stdout": 0, "stderr": 0}, "total_saved": 0}
    reader_errors: list[str] = []

    def pump(pipe: BinaryIO, path: Path, name: str) -> None:
        try:
            with path.open("wb") as output:
                while True:
                    chunk = pipe.read(64 * 1024)
                    if not chunk:
                        break
                    with state_lock:
                        capture["observed"][name] += len(chunk)
                        allowed = min(
                            len(chunk),
                            max(0, stream_cap - capture["saved"][name]),
                            max(0, total_cap - capture["total_saved"]),
                        )
                        if allowed:
                            output.write(chunk[:allowed])
                            capture["saved"][name] += allowed
                            capture["total_saved"] += allowed
                        if allowed < len(chunk):
                            output_exceeded.set()
                output.flush()
        except (OSError, ValueError) as exc:
            reader_errors.append(f"{name}: {exc}")
        finally:
            try:
                pipe.close()
            except OSError:
                pass

    assert process.stdout is not None and process.stderr is not None
    readers = [
        threading.Thread(target=pump, args=(process.stdout, stdout_path, "stdout"), daemon=True),
        threading.Thread(target=pump, args=(process.stderr, stderr_path, "stderr"), daemon=True),
    ]
    for reader in readers:
        reader.start()

    started = time.monotonic()
    peak_rss = 0
    peak_processes = 0
    stop_reason: str | None = None
    try:
        while True:
            if output_exceeded.is_set():
                stop_reason = "CAPTURED_OUTPUT_LIMIT_EXCEEDED"
                _terminate_tree(process.pid)
                break
            elapsed = time.monotonic() - started
            if elapsed > timeout:
                stop_reason = "WALL_TIMEOUT_EXCEEDED"
                _terminate_tree(process.pid)
                break
            if process.poll() is not None:
                break
            process_count, rss = _process_snapshot(process.pid)
            peak_processes = max(peak_processes, process_count)
            peak_rss = max(peak_rss, rss)
            if process_count > process_cap:
                stop_reason = "PROCESS_TREE_LIMIT_EXCEEDED"
            elif rss > rss_cap:
                stop_reason = "RSS_SOFT_LIMIT_EXCEEDED"
            elif _directory_size(output_dir) > archive_cap:
                stop_reason = "RUN_ARCHIVE_SIZE_LIMIT_OBSERVED"
            elif _directory_size(temporary_dir) > temporary_cap:
                stop_reason = "TEMPORARY_SIZE_LIMIT_OBSERVED"
            elif free_disk_floor and shutil.disk_usage(cwd).free < free_disk_floor:
                stop_reason = "MINIMUM_FREE_DISK_FLOOR_CROSSED"
            if stop_reason is not None:
                _terminate_tree(process.pid)
                break
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        stop_reason = "INTERRUPTED_BY_OPERATOR"
        _terminate_tree(process.pid)

    try:
        return_code = process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        _terminate_tree(process.pid)
        return_code = process.wait(timeout=5)
    except KeyboardInterrupt:
        stop_reason = "INTERRUPTED_BY_OPERATOR"
        _terminate_tree(process.pid)
        return_code = process.wait(timeout=5)
    for reader in readers:
        reader.join(timeout=5)
    elapsed = time.monotonic() - started
    archive_bytes = _directory_size(output_dir)
    temporary_bytes = _directory_size(temporary_dir)
    if archive_bytes > archive_cap and stop_reason is None:
        stop_reason = "RUN_ARCHIVE_SIZE_LIMIT_OBSERVED"
    if temporary_bytes > temporary_cap and stop_reason is None:
        stop_reason = "TEMPORARY_SIZE_LIMIT_OBSERVED"
    if output_exceeded.is_set() and stop_reason is None:
        stop_reason = "CAPTURED_OUTPUT_LIMIT_EXCEEDED"
    if reader_errors and stop_reason is None:
        stop_reason = "OUTPUT_CAPTURE_ERROR"
    if stop_reason:
        status = stop_reason
    elif return_code == 0:
        status = "PASS"
    else:
        status = "PYTEST_FAILED"
    with state_lock:
        stdout_bytes = int(capture["saved"]["stdout"])
        stderr_bytes = int(capture["saved"]["stderr"])
    return ProcessResult(
        status=status,
        return_code=return_code,
        elapsed_seconds=elapsed,
        peak_rss_bytes=peak_rss,
        peak_process_count=peak_processes,
        stdout_bytes=stdout_bytes,
        stderr_bytes=stderr_bytes,
        archive_bytes=archive_bytes,
        temporary_bytes=temporary_bytes,
        stop_reason=stop_reason or ("; ".join(reader_errors) if reader_errors else None),
    )


def _git_identity(
    root: Path = ROOT,
    *,
    expected_branch: str | None = None,
    baseline_commit: str | None = None,
) -> dict[str, Any]:
    def git(*args: str) -> str | None:
        result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else None

    top_level = git("rev-parse", "--show-toplevel")
    head = git("rev-parse", "HEAD")
    tree = git("rev-parse", "HEAD^{tree}")
    branch = git("branch", "--show-current")
    if not top_level or Path(top_level).resolve() != root.resolve() or not head or not tree:
        raise PolicyError("registered project root is not the Git worktree being executed")
    if expected_branch is not None and branch != expected_branch:
        raise PolicyError(f"worktree branch mismatch: expected {expected_branch}, got {branch}")
    if baseline_commit is not None:
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", baseline_commit, "HEAD"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise PolicyError("registered baseline is not an ancestor of this worktree HEAD")
    return {
        "root": str(root.resolve()),
        "branch": branch,
        "head": head,
        "tree": tree,
        "status_short": git("status", "--short", "--untracked-files=all"),
    }


def _next_attempt(
    series_dir: Path,
    series_id: str,
    scope_name: str,
    maximum: int,
    *,
    worktree_id: str | None = None,
    target: str | None = None,
) -> tuple[int, Path]:
    series_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = series_dir / "series.json"
    metadata = {
        "schema": "qfsolver-development-series-v2",
        "series_id": series_id,
        "scope": scope_name,
        "worktree_id": worktree_id,
        "target": target,
    }
    try:
        with metadata_path.open("x", encoding="utf-8") as stream:
            json.dump(metadata, stream, sort_keys=True)
            stream.write("\n")
    except FileExistsError:
        try:
            existing = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PolicyError(f"development series metadata is unreadable: {exc}") from exc
        if existing != metadata:
            raise PolicyError("development series ID is already bound to a different scope")
    prior = [path for path in series_dir.glob("attempt-[0-9][0-9][0-9][0-9]") if path.is_dir()]
    number = len(prior) + 1
    if number > maximum:
        raise PolicyError(f"development series exhausted its {maximum}-attempt budget")
    attempt_dir = series_dir / f"attempt-{number:04d}"
    try:
        attempt_dir.mkdir(exist_ok=False)
    except FileExistsError as exc:
        raise PolicyError("another invocation is already using this development series") from exc
    return number, attempt_dir


@contextmanager
def _exclusive_file_lock(path: Path) -> Iterator[None]:
    """Acquire an OS-released lock; a stale lock file never blocks a later run."""
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = path.open("a+b")
    try:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"\0")
            stream.flush()
        stream.seek(0)
        if os.name == "nt":
            import msvcrt

            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise PolicyError(f"another authorized scenario is active ({path.name})") from exc
        else:  # pragma: no cover - exercised on non-Windows development hosts
            import fcntl

            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise PolicyError(f"another authorized scenario is active ({path.name})") from exc
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:  # pragma: no cover - exercised on non-Windows development hosts
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
    finally:
        stream.close()


def _worktree_source_fingerprint(root: Path, target: str) -> str:
    """Hash the loaded solver, its Python helpers, test, conftests, and project config."""
    listed = subprocess.run(
        [
            "git",
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            "src/solveur",
            "experiments",
            "tests",
            "pyproject.toml",
            "pytest.ini",
        ],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if listed.returncode != 0:
        raise PolicyError("cannot inventory worktree source files for retry identity")
    target_module = target.split("::", maxsplit=1)[0]
    files: set[str] = set()
    for raw in listed.stdout.split(b"\0"):
        if not raw:
            continue
        relative = Path(os.fsdecode(raw).replace("\\", "/"))
        relative_text = relative.as_posix()
        if (
            relative_text.startswith("src/solveur/") and relative.suffix == ".py"
            or relative_text.startswith("experiments/") and relative.suffix == ".py"
            or relative_text == target_module
            or relative_text in {"tests/conftest.py", "tests/unit/conftest.py", "pyproject.toml", "pytest.ini"}
        ):
            files.add(relative_text)
    if target_module not in files:
        raise PolicyError("approved test module is absent from the source fingerprint inventory")
    digest = hashlib.sha256()
    for relative_text in sorted(files):
        path = (root / Path(relative_text)).resolve()
        if not _is_within(path, root.resolve()) or not path.is_file():
            raise PolicyError(f"source file escapes or is unavailable: {relative_text}")
        digest.update(relative_text.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(_sha256(path)))
    return digest.hexdigest()


def _reserve_node_attempt(
    ledger_path: Path,
    lock_path: Path,
    *,
    mandate_id: str,
    worktree_id: str,
    target: str,
    series_id: str,
    source_fingerprint: str,
    reason: str,
    maximum: int,
) -> tuple[str, int]:
    key = f"{mandate_id}:{worktree_id}:{target}"
    with _exclusive_file_lock(lock_path):
        if ledger_path.exists():
            try:
                ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise PolicyError(f"development attempt ledger is unreadable: {exc}") from exc
        else:
            ledger = {"schema": "qfsolver-development-node-ledger-v1", "mandate_id": mandate_id, "entries": {}}
        if (
            not isinstance(ledger, dict)
            or ledger.get("schema") != "qfsolver-development-node-ledger-v1"
            or ledger.get("mandate_id") != mandate_id
            or not isinstance(ledger.get("entries"), dict)
        ):
            raise PolicyError("development attempt ledger identity/schema mismatch")
        attempts = ledger["entries"].setdefault(key, [])
        if not isinstance(attempts, list):
            raise PolicyError("development attempt ledger entry is malformed")
        if len(attempts) >= maximum:
            raise PolicyError(f"development mandate exhausted {maximum} attempts for this nodeid")
        if attempts:
            last = attempts[-1]
            if last.get("source_fingerprint") == source_fingerprint and last.get("reason") == reason:
                raise PolicyError("identical repeat refused: change the source or document a new diagnostic hypothesis")
        number = len(attempts) + 1
        attempts.append(
            {
                "attempt": number,
                "series_id": series_id,
                "source_fingerprint": source_fingerprint,
                "reason": reason,
                "state": "RESERVED",
                "started_at_utc": datetime.now(timezone.utc).isoformat(),
            }
        )
        _atomic_json(ledger_path, ledger)
    return key, number


def _complete_node_attempt(
    ledger_path: Path,
    lock_path: Path,
    *,
    key: str,
    attempt_number: int,
    state: str,
    finished_at_utc: str,
    post_fingerprint: str,
) -> None:
    with _exclusive_file_lock(lock_path):
        try:
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            attempts = ledger["entries"][key]
            record = attempts[attempt_number - 1]
        except (OSError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise PolicyError(f"cannot finalize development attempt ledger: {exc}") from exc
        record["state"] = state
        record["finished_at_utc"] = finished_at_utc
        record["post_source_fingerprint"] = post_fingerprint
        _atomic_json(ledger_path, ledger)


def _registered_worktree(
    worktree_id: str,
    target: str,
    policy: Mapping[str, Any],
) -> tuple[dict[str, Any], Path, Path, dict[str, Any], str]:
    try:
        entry = policy["worktrees"][worktree_id]
    except KeyError as exc:
        raise PolicyError("unknown registered worktree") from exc
    root = Path(entry["root"]).resolve(strict=True)
    git_root = Path(entry["git_root"]).resolve(strict=True)
    if root != git_root:
        raise PolicyError("registered worktree/Git root identity changed")
    source_root = (root / entry["source_root"]).resolve(strict=True)
    expected_init = (source_root / "solveur" / "__init__.py").resolve(strict=True)
    if not _is_within(source_root, root) or not expected_init.is_file():
        raise PolicyError("registered solver package is missing or outside its source root")
    test_module = (root / target.split("::", maxsplit=1)[0]).resolve(strict=True)
    test_root = (root / entry["pytest_root"]).resolve(strict=True)
    if not _is_within(test_module, test_root) or not test_module.is_file():
        raise PolicyError("registered test module is missing or escaped its worktree")
    identity = _git_identity(
        root,
        expected_branch=entry["branch"],
        baseline_commit=entry["baseline_commit"],
    )
    fingerprint = _worktree_source_fingerprint(root, target)
    return entry, root, source_root, identity, fingerprint


def _run_root(policy: Mapping[str, Any]) -> Path:
    root = (ROOT / policy["run_store"]).resolve()
    if not _is_within(root, ROOT.resolve()) or _is_within(root, (ROOT / "qualification").resolve()):
        raise PolicyError("development run store must be inside the worktree and outside qualification")
    return root


def _series_root(store: Path, scope_name: str, worktree_id: str | None) -> Path:
    if worktree_id is not None:
        if worktree_id not in {"d01", "c01", "e01"}:
            raise PolicyError("unknown worktree output namespace")
        return store / "worktrees" / worktree_id
    if scope_name not in STANDARD_SCOPES:
        raise PolicyError("standard output namespace requires a fixed local test scope")
    return store / "standard" / scope_name


def _controller_provenance() -> dict[str, Any]:
    files = {
        "runner": Path(__file__).resolve(),
        "pytest_plugin": Path(__file__).with_name("development_autonomous_pytest_plugin.py").resolve(),
        "policy": POLICY_PATH.resolve(),
    }
    return {
        "identity": _git_identity(ROOT),
        "sha256": {name: _sha256(path) for name, path in files.items()},
        "runtime": {
            "python_executable": sys.executable,
            "python_version": sys.version.split()[0],
            "pytest_version": importlib.metadata.version("pytest"),
            "psutil_version": importlib.metadata.version("psutil") if psutil is not None else None,
        },
    }


def run_pytest(
    scope_name: str,
    target: str | None,
    series_id: str | None,
    *,
    worktree_id: str | None = None,
    reason: str | None = None,
) -> tuple[dict[str, Any], int]:
    policy = load_policy()
    is_registered = scope_name in WORKTREE_SCOPES
    targets = resolve_targets(scope_name, target, policy, worktree_id=worktree_id)
    entry: dict[str, Any] | None = None
    source_root: Path | None = None
    source_fingerprint: str | None = None
    if is_registered:
        if not worktree_id or not target or not reason or not reason.strip():
            raise PolicyError("registered worktree tests require one exact target, worktree, and documented reason")
        entry, execution_root, source_root, identity, source_fingerprint = _registered_worktree(
            worktree_id,
            target,
            policy,
        )
        scope = dict(entry["budgets"])
        attempt_limit = int(entry["attempt_limit_per_nodeid"])
    else:
        execution_root = ROOT
        scope = policy["standard_scopes"][scope_name]
        identity = _git_identity(ROOT)
        attempt_limit = int(scope["max_attempts_per_series"])
    if is_registered and scope_name == "fem_exploratory":
        # The lock is shared by D01 and C01: at most one exploratory FEM/test
        # scenario started through this policy can be active at a time.
        scenario_lock = _exclusive_file_lock(_run_root(policy) / "locks" / "fem-exploratory.lock")
    else:
        scenario_lock = nullcontext()
    if psutil is None:
        raise PolicyError("psutil is missing; install the project test/dev dependencies before launch")
    free_bytes = min(shutil.disk_usage(ROOT).free, shutil.disk_usage(execution_root).free)
    minimum_free = int(policy["minimum_free_disk_mib"] * 1024 * 1024)
    if free_bytes < minimum_free:
        raise PolicyError(f"insufficient free disk: {free_bytes} bytes; requires {minimum_free}")
    if series_id is None:
        series_id = f"dev-{uuid.uuid4().hex[:12]}"
    if not SERIES_RE.fullmatch(series_id):
        raise PolicyError("series ID must use the development-only format dev-<lowercase-id>")
    store = _run_root(policy)
    series_dir = _series_root(store, scope_name, worktree_id) / series_id
    with scenario_lock:
        number, attempt_dir = _next_attempt(
            series_dir,
            series_id,
            scope_name,
            attempt_limit,
            worktree_id=worktree_id,
            target=targets[0] if is_registered else (target or "<scope>"),
        )
        node_ledger_path = store / "node-attempt-ledger.json"
        node_ledger_lock = store / "node-attempt-ledger.lock"
        ledger_key: str | None = None
        ledger_number: int | None = None
        if is_registered:
            assert worktree_id is not None and source_fingerprint is not None and reason is not None and target is not None
            try:
                ledger_key, ledger_number = _reserve_node_attempt(
                    node_ledger_path,
                    node_ledger_lock,
                    mandate_id=str(policy["mandate_id"]),
                    worktree_id=worktree_id,
                    target=target,
                    series_id=series_id,
                    source_fingerprint=source_fingerprint,
                    reason=reason.strip(),
                    maximum=attempt_limit,
                )
            except Exception:
                attempt_dir.rmdir()
                raise
        temp_dir = attempt_dir / "tmp"
        output_dir = attempt_dir / "output"
        temp_dir.mkdir()
        output_dir.mkdir()
        command = build_pytest_command(
            scope_name,
            targets,
            temp_dir,
            repository_root=execution_root,
            source_root=source_root,
            controller_root=ROOT,
            allow_native_skip_override=bool(entry and entry["allow_native_vv_skip_override"]),
        )
        started_at = datetime.now(timezone.utc).isoformat()
        initial: dict[str, Any] = {
            "schema": "qfsolver-development-attempt-v2",
            "mode": "DEVELOPMENT_AUTONOMOUS",
            "mandate_id": policy["mandate_id"],
            "series_id": series_id,
            "attempt": ledger_number or number,
            "scope": scope_name,
            "worktree_id": worktree_id,
            "target": targets,
            "reason": reason.strip() if reason else None,
            "state": "RUNNING",
            "started_at_utc": started_at,
            "identity": identity,
            "controller_provenance": _controller_provenance(),
            "source_fingerprint": source_fingerprint,
            "solver_import_root": str(source_root.resolve()) if source_root else None,
            "solver_origin_expected": str((source_root / "solveur" / "__init__.py").resolve()) if source_root else None,
            "command": command,
            "budgets": dict(scope),
            "budget_semantics": {
                "wall_timeout": "watchdog-triggered process-tree termination; best-effort OS control",
                "rss": "sampled soft monitor; not a hard memory/commit limit",
                "process_count": "sampled process-tree monitor; not a job-object boundary",
                "captured_output": "application-enforced byte caps on captured stdout/stderr",
                "temporary_and_archive_size": "sampled size monitoring; not an NTFS quota",
                "free_disk": "preflight and sampled floor check",
                "attempt_limit": "persistent procedural ledger under the development run store",
            },
            "free_disk_before_bytes": free_bytes,
            "qualification": "NOT_APPLICABLE_DEVELOPMENT_ONLY",
            "qualification_promotion": "PROHIBITED",
        }
        record_path = attempt_dir / "run.json"
        _atomic_json(record_path, initial)
        environment = build_child_environment(
            temp_dir,
            source_root=source_root,
            d01_source_sha=identity["head"] if worktree_id == "d01" else None,
        )
        limits = dict(scope)
        limits["minimum_free_disk_mib"] = policy["minimum_free_disk_mib"]
        try:
            result = run_supervised_command(
                command,
                cwd=execution_root,
                environment=environment,
                output_dir=output_dir,
                temporary_dir=temp_dir,
                limits=limits,
                poll_interval=float(policy["poll_interval_seconds"]),
            )
        except OSError as exc:
            finished_at = datetime.now(timezone.utc).isoformat()
            post_fingerprint = _worktree_source_fingerprint(execution_root, target) if is_registered and target else "NOT_CAPTURED"
            final = {
                **initial,
                "state": "LAUNCH_FAILED",
                "finished_at_utc": finished_at,
                "launch_error": f"{type(exc).__name__}: {exc}",
                "free_disk_after_bytes": min(shutil.disk_usage(ROOT).free, shutil.disk_usage(execution_root).free),
                "temporary_bytes": _directory_size(temp_dir),
            }
            _atomic_json(record_path, final)
            if ledger_key and ledger_number:
                _complete_node_attempt(
                    node_ledger_path,
                    node_ledger_lock,
                    key=ledger_key,
                    attempt_number=ledger_number,
                    state="LAUNCH_FAILED",
                    finished_at_utc=finished_at,
                    post_fingerprint=post_fingerprint,
                )
            return {"series_id": series_id, "attempt": ledger_number or number, "state": "LAUNCH_FAILED", "record": str(record_path)}, 1
        finished_at = datetime.now(timezone.utc).isoformat()
        post_fingerprint = source_fingerprint
        state = result.status
        if is_registered and target:
            try:
                post_fingerprint = _worktree_source_fingerprint(execution_root, target)
            except PolicyError:
                post_fingerprint = "UNAVAILABLE"
            if post_fingerprint != source_fingerprint:
                state = "SOURCE_CHANGED_DURING_RUN"
        final = {
            **initial,
            "state": state,
            "finished_at_utc": finished_at,
            "return_code": result.return_code,
            "elapsed_seconds": result.elapsed_seconds,
            "peak_rss_bytes": result.peak_rss_bytes,
            "peak_process_count": result.peak_process_count,
            "stdout_bytes": result.stdout_bytes,
            "stderr_bytes": result.stderr_bytes,
            "stdout_sha256": _sha256(output_dir / "stdout.log"),
            "stderr_sha256": _sha256(output_dir / "stderr.log"),
            "archive_bytes": result.archive_bytes,
            "temporary_bytes": result.temporary_bytes,
            "post_source_fingerprint": post_fingerprint,
            "stop_reason": result.stop_reason,
            "free_disk_after_bytes": min(shutil.disk_usage(ROOT).free, shutil.disk_usage(execution_root).free),
        }
        _atomic_json(record_path, final)
        if ledger_key and ledger_number:
            _complete_node_attempt(
                node_ledger_path,
                node_ledger_lock,
                key=ledger_key,
                attempt_number=ledger_number,
                state=state,
                finished_at_utc=finished_at,
                post_fingerprint=post_fingerprint,
            )
        return {
            "series_id": series_id,
            "attempt": ledger_number or number,
            "state": state,
            "record": str(record_path),
            "metrics": final,
        }, (0 if state == "PASS" else 1)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    test_parser = subparsers.add_parser("test", help="run one fixed development pytest scope")
    test_parser.add_argument("--scope", choices=("unit", "integration", "fem_exploratory", "math_non_fem"), required=True)
    test_parser.add_argument("--target", help="repository-relative test file/nodeid; FEM requires an exact approved nodeid")
    test_parser.add_argument("--series", help="development-only dev-* series ID for bounded follow-up attempts")
    test_parser.add_argument("--worktree", help="registered worktree ID (d01, c01, e01) for an exact development nodeid")
    test_parser.add_argument("--reason", help="short documented development hypothesis/reason for a registered nodeid attempt")
    args = parser.parse_args(argv)
    try:
        result, exit_code = run_pytest(
            args.scope,
            args.target,
            args.series,
            worktree_id=args.worktree,
            reason=args.reason,
        )
    except PolicyError as exc:
        print(json.dumps({"state": "REFUSED", "reason": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
