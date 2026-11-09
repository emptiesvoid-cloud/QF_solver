"""Run fixed, synthetic smoke cases through the experimental CI supervisors.

Linux uses one transient, delegated systemd service and creates its supervisor
leaf only inside that service. Windows uses an isolated Job Object. No project
dependencies, test suite, solver code, credentials, or external inputs are used.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid


ROOT = Path(__file__).resolve().parents[1]
def _validate_success(report: dict, label: str) -> None:
    if report.get("timed_out") or report.get("violation") or report.get("exit_code") != 0:
        raise RuntimeError(f"{label} synthetic success case failed: {report}")
    if report.get("remaining_processes", report.get("active_descendants")) != 0:
        raise RuntimeError(f"{label} synthetic success left descendants: {report}")
    if label == "Linux" and report.get("cgroup_cleanup") != "removed":
        raise RuntimeError(f"Linux synthetic cgroup was not removed: {report}")


def _linux_worker(unit: str) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from ci_linux_cgroup_synthetic import _cgroup2_dir, run

    parent = _cgroup2_dir()
    if not unit.startswith("qf-pr132-synthetic-") or parent != Path(f"/sys/fs/cgroup/system.slice/{unit}.service"):
        raise RuntimeError(f"unexpected transient service cgroup: {parent}")
    required = {"cpu", "memory", "pids"}
    if not required <= set((parent / "cgroup.controllers").read_text().split()):
        raise RuntimeError("transient service lacks required controllers")
    leaf = parent / "supervisor"
    leaf.mkdir()
    (leaf / "cgroup.procs").write_text(str(os.getpid()))
    control = parent / "cgroup.subtree_control"
    missing = required - set(control.read_text().split())
    if missing:
        control.write_text(" ".join(f"+{name}" for name in sorted(missing)))

    success = run([sys.executable, "-c", "print('synthetic')"], 256 * 1024 * 1024,
                  16, 100_000, 100_000, 5, delegated_parent=parent)
    _validate_success(success, "Linux")
    child_code = ("import subprocess,sys,time; "
                  "subprocess.Popen([sys.executable,'-c','import time; time.sleep(10)']); "
                  "time.sleep(10)")
    timeout = run([sys.executable, "-c", child_code], 256 * 1024 * 1024,
                  16, 100_000, 100_000, 1, delegated_parent=parent)
    if not timeout.get("timed_out") or timeout.get("violation"):
        raise RuntimeError(f"Linux synthetic timeout case failed: {timeout}")
    if timeout.get("remaining_processes") != 0 or timeout.get("cgroup_cleanup") != "removed":
        raise RuntimeError(f"Linux timeout case did not clean up: {timeout}")
    memory = run([sys.executable, "-c",
                  "import time; b=bytearray(128*1024*1024); b[::4096]=b'X'*(len(b)//4096); time.sleep(1)",
                  ], 64 * 1024 * 1024, 16, 100_000, 100_000, 5,
                 delegated_parent=parent)
    if memory.get("violation") != "memory_oom":
        raise RuntimeError(f"Linux synthetic memory limit was not observed: {memory}")
    pids_code = ("import subprocess,sys,time; "
                 "children=[subprocess.Popen([sys.executable,'-c','import time; time.sleep(10)']) "
                 "for _ in range(12)]; time.sleep(10)")
    pids = run([sys.executable, "-c", pids_code], 256 * 1024 * 1024,
               4, 100_000, 100_000, 5, delegated_parent=parent)
    if pids.get("violation") != "pids_limit":
        raise RuntimeError(f"Linux synthetic process limit was not observed: {pids}")
    if pids.get("remaining_processes") != 0 or pids.get("cgroup_cleanup") != "removed":
        raise RuntimeError(f"Linux process limit case did not clean up: {pids}")
    print(json.dumps({"platform": "linux", "success_case": success,
                      "timeout_descendant_cleanup_case": timeout,
                      "memory_limit_case": memory, "process_limit_case": pids}, sort_keys=True))


def _run_linux() -> None:
    if not Path("/sys/fs/cgroup/cgroup.controllers").is_file():
        raise RuntimeError("cgroup v2 is unavailable")
    for tool in ("sudo", "systemd-run"):
        if not shutil.which(tool):
            raise RuntimeError(f"required Linux smoke tool is unavailable: {tool}")
    unit = "qf-pr132-synthetic-" + uuid.uuid4().hex[:12]
    command = [
        "sudo", "-n", "systemd-run", "--quiet", "--pipe", "--wait", "--collect",
        "--unit", unit, "--property=Delegate=yes", "--property=RuntimeMaxSec=30s",
        sys.executable, str(Path(__file__).resolve()), "--delegated-worker", unit,
    ]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=40)
    if result.stdout:
        print(result.stdout, end="")
    if result.returncode:
        raise RuntimeError(f"delegated systemd smoke failed ({result.returncode}): {result.stderr.strip()}")


def _run_windows() -> None:
    if os.name != "nt":
        raise RuntimeError("Windows smoke requested on a non-Windows host")
    sys.path.insert(0, str(ROOT / "scripts"))
    from ci_windows_job_synthetic import run

    success = run([sys.executable, "-c", "print('synthetic')"], 256 * 1024 * 1024, 4, 5)
    _validate_success(success, "Windows")
    child_code = ("import subprocess,sys,time; "
                  "subprocess.Popen([sys.executable,'-c','import time; time.sleep(10)']); "
                  "time.sleep(10)")
    timeout = run([sys.executable, "-c", child_code],
                  256 * 1024 * 1024, 4, 1)
    if not timeout.get("timed_out") or timeout.get("violation"):
        raise RuntimeError(f"Windows synthetic timeout case failed: {timeout}")
    if timeout.get("active_descendants") != 0:
        raise RuntimeError(f"Windows timeout case did not clean up: {timeout}")
    memory_code = ("import time; b=bytearray(128*1024*1024); "
                   "b[::4096]=b'X'*(len(b)//4096); time.sleep(1)")
    memory = run([sys.executable, "-c", memory_code], 64 * 1024 * 1024, 4, 5)
    if memory.get("violation") not in ("process_memory_limit", "job_memory_limit"):
        raise RuntimeError(f"Windows synthetic memory limit was not observed: {memory}")
    pids_code = ("import subprocess,sys,time; "
                 "children=[subprocess.Popen([sys.executable,'-c','import time; time.sleep(10)']) "
                 "for _ in range(8)]; time.sleep(10)")
    pids = run([sys.executable, "-c", pids_code], 256 * 1024 * 1024, 3, 5)
    if pids.get("violation") != "active_process_limit":
        raise RuntimeError(f"Windows synthetic process limit was not observed: {pids}")
    if pids.get("active_descendants") != 0:
        raise RuntimeError(f"Windows process limit case did not clean up: {pids}")
    print(json.dumps({"platform": "windows", "success_case": success,
                      "timeout_descendant_cleanup_case": timeout,
                      "memory_limit_case": memory, "process_limit_case": pids}, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delegated-worker", metavar="UNIT", help=argparse.SUPPRESS)
    parser.add_argument("--platform", choices=("auto", "linux", "windows"), default="auto",
                        help="select a host for local smoke execution (default: detect host)")
    args = parser.parse_args()
    try:
        if args.delegated_worker:
            _linux_worker(args.delegated_worker)
        elif args.platform == "windows" or (args.platform == "auto" and os.name == "nt"):
            _run_windows()
        elif args.platform == "linux" or (args.platform == "auto" and sys.platform.startswith("linux")):
            _run_linux()
        else:
            raise RuntimeError(f"no smoke implementation for host platform {sys.platform}")
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
        print(f"synthetic CI supervisor smoke failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
