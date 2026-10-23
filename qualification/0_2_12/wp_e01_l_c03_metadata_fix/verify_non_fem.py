"""Record the isolated standard-library-only mathematical test run.

This utility never executes the scientific solver or an FEM kernel. The test
suite uses synthetic mathematical/serialization fixtures and read-only inputs.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    root = Path(__file__).resolve().parent
    executable = Path(sys.executable).resolve()
    command = [str(executable), "-I", "-S", "-B", "-m", "unittest", "discover",
               "-s", str(root), "-p", "test_*.py", "-v"]
    started = time.monotonic()
    result = subprocess.run(command, cwd=root, capture_output=True, check=False)
    elapsed = time.monotonic() - started
    stdout_path = root / "non_fem_tests.stdout.txt"
    stderr_path = root / "non_fem_tests.stderr.txt"
    stdout_path.write_bytes(result.stdout)
    stderr_path.write_bytes(result.stderr)
    record = {
        "purpose": "synthetic_non_FEM_mathematical_verification_only",
        "command_argv": command,
        "cwd": str(root),
        "returncode": result.returncode,
        "elapsed_seconds": elapsed,
        "runtime": {
            "executable": str(executable),
            "executable_sha256": digest(executable),
            "version": sys.version,
            "implementation": sys.implementation.name,
            "platform": platform.platform(),
            "binary_float_radix": sys.float_info.radix,
            "binary_float_mantissa_bits": sys.float_info.mant_dig,
            "binary_float_max_exp": sys.float_info.max_exp,
            "binary_float_min_exp": sys.float_info.min_exp,
            "isolated_child": True,
            "site_initialization_disabled": True,
            "bytecode_writes_disabled": True,
        },
        "tested_sources": {
            p.name: digest(p) for p in sorted(root.glob("*.py"))
        },
        "stdout": {"path": stdout_path.name, "sha256": digest(stdout_path)},
        "stderr": {"path": stderr_path.name, "sha256": digest(stderr_path)},
        "scientific_evidence": False,
        "FEM_execution": "NOT_RUN",
    }
    (root / "non_fem_verification_record.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"returncode": result.returncode,
                      "elapsed_seconds": elapsed,
                      "record": "non_fem_verification_record.json"}))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
