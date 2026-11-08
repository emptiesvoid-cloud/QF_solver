"""Run one command in a transient, delegated systemd service with cgroup limits.

This launcher requires a non-root Linux CI runner and a working system systemd
manager with cgroup v2 delegation. It intentionally has no local-process or
unbounded fallback. The supervisor and workload retain the runner UID; these
limits are for cooperative, trusted test code. A process that can modify its
delegated cgroup controls can change its own limits, so this is not a sandbox.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import sys
import uuid


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=int, required=True, help="workload timeout in seconds")
    parser.add_argument("--memory-bytes", type=int, required=True)
    parser.add_argument("--pids", type=int, required=True)
    parser.add_argument("--cpu-quota-us", type=int, required=True)
    parser.add_argument("--cpu-period-us", type=int, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    limits = (args.seconds, args.memory_bytes, args.pids, args.cpu_quota_us, args.cpu_period_us)
    if min(limits) <= 0:
        print("ci_linux_bounded_step: every limit must be a positive integer", file=sys.stderr)
        return 2
    if not command:
        print("ci_linux_bounded_step: a command after -- is required", file=sys.stderr)
        return 2
    if sys.platform != "linux":
        print("ci_linux_bounded_step: Linux is required; no fallback is available", file=sys.stderr)
        return 2
    if not hasattr(os, "geteuid") or os.geteuid() == 0:
        print("ci_linux_bounded_step: refusing root; run as the original non-root CI runner", file=sys.stderr)
        return 2
    systemd_run = shutil.which("systemd-run")
    sudo = shutil.which("sudo")
    env_bin = shutil.which("env")
    python = shutil.which("python3")
    if not systemd_run or not sudo or not env_bin or not python:
        print("ci_linux_bounded_step: sudo, systemd-run, env, and python3 are required", file=sys.stderr)
        return 2
    try:
        runner = pwd.getpwuid(os.getuid())
    except KeyError:
        print("ci_linux_bounded_step: original runner account cannot be resolved", file=sys.stderr)
        return 2

    unit = "codex-bounded-" + uuid.uuid4().hex
    expected_cgroup = f"/system.slice/{unit}.service"
    try:
        working_directory = str(Path.cwd().resolve(strict=True))
    except OSError as exc:
        print(f"ci_linux_bounded_step: working directory is unavailable: {exc}", file=sys.stderr)
        return 2
    helper = Path(__file__).resolve().with_name("ci_linux_cgroup_synthetic.py")
    supervisor = [
        python, str(helper), "--seconds", str(args.seconds),
        "--memory-bytes", str(args.memory_bytes), "--pids", str(args.pids),
        "--cpu-quota-us", str(args.cpu_quota_us), "--cpu-period-us", str(args.cpu_period_us),
        "--expected-cgroup", expected_cgroup, "--expected-uid", str(os.getuid()),
        "--expected-gid", str(os.getgid()), "--enable-controllers", "--", *command,
    ]
    # env -i ensures the service workload receives no inherited CI credentials,
    # HMAC variables, or other runner environment. Only ordinary execution context
    # is supplied. systemd-run itself does not copy the caller's environment into
    # the service; env -i also clears manager-provided service variables.
    clean_exec = [env_bin, "-i", f"PATH={os.environ.get('PATH', os.defpath)}",
                  f"HOME={runner.pw_dir}", "LANG=C.UTF-8", *supervisor]
    # RuntimeMaxSec bounds the active service; systemd's bounded stop grace is
    # added after it, keeping the hard outer allowance at roughly +15 seconds.
    outer_seconds = args.seconds + 9
    cmd = [
        sudo, "-n", "--", systemd_run, "--wait", "--pipe", "--collect", "--service-type=exec",
        f"--unit={unit}",
        f"--property=User={os.getuid()}", f"--property=Group={os.getgid()}",
        "--property=Delegate=cpu memory pids", f"--property=WorkingDirectory={working_directory}",
        "--property=KillMode=control-group", "--property=NoNewPrivileges=yes",
        "--property=TimeoutStopSec=6s", f"--property=RuntimeMaxSec={outer_seconds}s",
        "--", *clean_exec,
    ]
    try:
        return subprocess.run(cmd, check=False).returncode
    except OSError as exc:
        print(f"ci_linux_bounded_step: could not start systemd-run: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
