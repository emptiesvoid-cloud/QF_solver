"""Experimental cgroup v2 synthetic supervisor. Not enabled for CI.

Requires an already delegated cgroup v2 subtree with cpu, memory and pids
controllers enabled. It limits memory and disables swap. The script never
changes the parent controller setup.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid


class CgroupUnavailable(RuntimeError):
    """The host has not delegated all controls required for hard limits."""


def _cgroup2_dir() -> Path:
    """Resolve this process's cgroup v2 directory from procfs."""
    try:
        cgroup_path = next(line.split("::", 1)[1] for line in Path("/proc/self/cgroup").read_text().splitlines()
                           if "::" in line)
        mount = next(line for line in Path("/proc/self/mountinfo").read_text().splitlines()
                     if " - cgroup2 " in line)
    except (OSError, StopIteration, IndexError) as exc:
        raise CgroupUnavailable("cgroup v2 mount/current membership is unavailable") from exc

    fields = mount.split()
    try:
        root = Path(fields[3].replace("\\040", " "))
        mountpoint = Path(fields[4].replace("\\040", " "))
        relative = Path(cgroup_path.lstrip("/"))
        if root != Path("/"):
            relative = relative.relative_to(root.relative_to("/"))
    except (IndexError, ValueError) as exc:
        raise CgroupUnavailable("cannot map cgroup membership to cgroup2 mount") from exc
    current = mountpoint / relative
    if not current.is_dir() or not (current / "cgroup.controllers").is_file():
        raise CgroupUnavailable("current cgroup v2 directory is inaccessible")
    return current


def _read_int(path: Path, key: str | None = None) -> int:
    content = path.read_text().strip()
    if key is not None:
        values = dict(line.split() for line in content.splitlines())
        return int(values[key])
    return int(content)


def _write(path: Path, value: str) -> None:
    try:
        path.write_text(value)
    except OSError as exc:
        raise CgroupUnavailable(f"required cgroup control is not writable: {path.name}") from exc


def _kill_and_remove(group: Path) -> None:
    """Kill all members and remove the subgroup, failing if either step fails."""
    if not group.exists():
        return
    populated = _read_int(group / "cgroup.events", "populated")
    if populated:
        _write(group / "cgroup.kill", "1")
        deadline = time.monotonic() + 5
        while _read_int(group / "cgroup.events", "populated") and time.monotonic() < deadline:
            time.sleep(0.05)
    if _read_int(group / "cgroup.events", "populated"):
        raise RuntimeError("cgroup remained populated after cgroup.kill")
    try:
        group.rmdir()
    except OSError as exc:
        raise RuntimeError("empty cgroup could not be removed") from exc


def run(argv: list[str], memory_bytes: int, pids: int, cpu_quota_us: int,
        cpu_period_us: int, seconds: float, *, delegated_parent: Path | None = None) -> dict:
    """Run one synthetic command under strict cgroup v2 resource limits."""
    if not argv or min(memory_bytes, pids, cpu_quota_us, cpu_period_us) <= 0 or seconds <= 0:
        raise ValueError("a command and positive limits are required")

    current = _cgroup2_dir()
    parent = delegated_parent.resolve(strict=True) if delegated_parent else current
    if parent != current and parent not in current.parents:
        raise CgroupUnavailable("delegated parent must contain the supervisor's cgroup")
    required = {"cpu", "memory", "pids"}
    try:
        enabled = set((parent / "cgroup.subtree_control").read_text().split())
        available = set((parent / "cgroup.controllers").read_text().split())
    except OSError as exc:
        raise CgroupUnavailable("cannot inspect delegated cgroup controllers") from exc
    missing = required - enabled
    if missing:
        raise CgroupUnavailable("controllers are not enabled in delegated subtree: " + ", ".join(sorted(missing)))
    if not required.issubset(available):
        raise CgroupUnavailable("required controllers are unavailable: " + ", ".join(sorted(required - available)))

    group = parent / ("codex-synthetic-" + uuid.uuid4().hex)
    try:
        group.mkdir()
    except OSError as exc:
        raise CgroupUnavailable("cannot create a cgroup in the delegated subtree") from exc

    proc: subprocess.Popen | None = None
    started = time.monotonic()
    timed_out = False
    violation = None
    try:
        for control in ("memory.max", "memory.swap.max", "pids.max", "cpu.max", "cgroup.kill", "cgroup.procs"):
            if not (group / control).exists():
                raise CgroupUnavailable(f"required cgroup v2 control is missing: {control}")
        _write(group / "memory.max", str(memory_bytes))
        _write(group / "memory.swap.max", "0")
        _write(group / "pids.max", str(pids))
        _write(group / "cpu.max", f"{cpu_quota_us} {cpu_period_us}")
        # Verify the recursive kill control is writable before starting work.
        _write(group / "cgroup.kill", "1")

        def enter_group() -> None:
            # Called in the forked child before exec, so it cannot create descendants
            # outside the limited cgroup.
            (group / "cgroup.procs").write_text(str(os.getpid()))

        proc = subprocess.Popen(argv, preexec_fn=enter_group, start_new_session=True)
        deadline = started + seconds
        while True:
            if _read_int(group / "memory.events", "oom"):
                violation = "memory_oom"
            elif _read_int(group / "pids.events", "max"):
                violation = "pids_limit"
            if violation or proc.poll() is not None:
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                break
            time.sleep(min(remaining, 0.05))
        if timed_out or violation:
            _write(group / "cgroup.kill", "1")
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError("cgroup.kill did not stop the supervised process") from exc

        # A command may exit while leaving workers behind. Reap the whole cgroup
        # before reporting so a successful leader cannot leak descendants.
        if _read_int(group / "cgroup.events", "populated"):
            _write(group / "cgroup.kill", "1")
            deadline = time.monotonic() + 5
            while _read_int(group / "cgroup.events", "populated") and time.monotonic() < deadline:
                time.sleep(0.05)
        if _read_int(group / "cgroup.events", "populated"):
            raise RuntimeError("cgroup remained populated after supervised command ended")

        stat = dict(line.split() for line in (group / "memory.events").read_text().splitlines())
        pids_events = dict(line.split() for line in (group / "pids.events").read_text().splitlines())
        cpu = dict(line.split() for line in (group / "cpu.stat").read_text().splitlines())
        events = {key: int(value) for key, value in stat.items()}
        if not violation and events["oom"]:
            violation = "memory_oom"
        if not violation and int(pids_events["max"]):
            violation = "pids_limit"
        report = {
            "timed_out": timed_out,
            "violation": violation,
            "exit_code": proc.returncode,
            "elapsed_seconds": time.monotonic() - started,
            "memory_limit_bytes": memory_bytes,
            "memory_swap_limit_bytes": 0,
            "memory_current_bytes": _read_int(group / "memory.current"),
            "memory_events": events,
            "pids_limit": pids,
            "pids_current": _read_int(group / "pids.current"),
            "pids_limit_events": {key: int(value) for key, value in pids_events.items()},
            "cpu_max": (group / "cpu.max").read_text().strip(),
            "cpu_usage_usec": int(cpu["usage_usec"]),
            "remaining_processes": _read_int(group / "cgroup.events", "populated"),
            "cgroup_cleanup": "removed",
        }
        _kill_and_remove(group)
        return report
    finally:
        # cgroup.kill is recursive and is also used on exceptional paths. Delete only
        # after the kernel reports that no process remains in the entire subtree.
        if group.exists():
            _kill_and_remove(group)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--memory-bytes", type=int, default=256 * 1024 * 1024)
    parser.add_argument("--pids", type=int, default=32)
    parser.add_argument("--cpu-quota-us", type=int, default=100_000)
    parser.add_argument("--cpu-period-us", type=int, default=100_000)
    parser.add_argument("--seconds", type=float, default=10)
    parser.add_argument("--delegated-parent", type=Path, help="delegated ancestor when the supervisor runs in a leaf")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    try:
        report = run(command or [sys.executable, "-c", "print('synthetic')"], args.memory_bytes,
                     args.pids, args.cpu_quota_us, args.cpu_period_us, args.seconds, delegated_parent=args.delegated_parent)
    except (CgroupUnavailable, OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "unavailable", "reason": str(exc)}))
        return 2
    report["status"] = "completed"
    print(json.dumps(report, sort_keys=True))
    if report["timed_out"]:
        return 124
    if report["violation"]:
        return 125
    return int(report["exit_code"] or 0)


if __name__ == "__main__":
    raise SystemExit(main())
