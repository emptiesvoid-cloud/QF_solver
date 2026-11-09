"""Start one approved PR test command under the Linux hard-limit supervisor."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

from ci_verify_pr_identity import load_approved_manifest


LIMIT_FLAGS = {
    "seconds": "--seconds",
    "memory_bytes": "--memory-bytes",
    "pids": "--pids",
    "cpu_quota_us": "--cpu-quota-us",
    "cpu_period_us": "--cpu-period-us",
}
# P0 follows the reference test step, which leaves this report behind.
GENERATED = {"quality-p0": ("junit.xml",)}


def launcher_args(profile: str, args: list[str], manifest: dict) -> list[str]:
    """Bind the command and every limit to the authenticated manifest."""
    approved = manifest["profiles"][profile]
    if not isinstance(approved, dict) or args != approved.get("python_args") or not args:
        raise ValueError("command differs from approved profile")
    if approved.get("python_minor") != f"{sys.version_info.major}.{sys.version_info.minor}":
        raise ValueError("Python version differs from approved profile")
    limits = approved.get("limits")
    if not isinstance(limits, dict) or limits.keys() != LIMIT_FLAGS.keys():
        raise ValueError("profile must specify every supported limit")
    result: list[str] = []
    for name, flag in LIMIT_FLAGS.items():
        value = limits[name]
        if type(value) is not int or value <= 0:
            raise ValueError(f"invalid approved limit: {name}")
        result.extend((flag, str(value)))
    return [*result, "--", sys.executable, *args]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("python_args", nargs=argparse.REMAINDER)
    parsed = parser.parse_args()
    try:
        if sys.platform != "linux" or os.environ.get("GITHUB_ACTIONS") != "true":
            raise ValueError("bounded PR test steps require a Linux GitHub runner")
        args = parsed.python_args
        if args[:1] != ["--"]:
            raise ValueError("separate the approved Python arguments with --")
        root = Path.cwd()
        manifest = load_approved_manifest(root, allowed_untracked=GENERATED.get(parsed.profile, ()))
        command = launcher_args(parsed.profile, args[1:], manifest)
        env = {key: value for key, value in os.environ.items() if not key.startswith(("QF_MANIFEST_", "QF_APPROVED_"))}
        launcher = root / "scripts/ci_linux_bounded_step.py"
        return subprocess.run([sys.executable, "-B", str(launcher), *command], env=env, check=False).returncode
    except (KeyError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Bounded CI step refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
