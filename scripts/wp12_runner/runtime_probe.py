"""Launch the pinned interpreter in isolated metadata-only probe mode."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Any, Mapping

from .contracts import ContractError


_RUNNER_ROOT = Path(__file__).resolve().parents[2]
_CHILD = _RUNNER_ROOT / "scripts" / "wp12_runner" / "environment_probe_child.py"
_SAFE_ENVIRONMENT_KEYS = ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP")
_THREAD_VARIABLES = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "BLIS_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "NUMEXPR_NUM_THREADS",
)


def probe_runtime_environment(
    python_executable: Path,
    *,
    thread_environment: Mapping[str, str],
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    """Inspect only import metadata and native-file hashes, never NumPy/SciPy code."""
    if set(thread_environment) != set(_THREAD_VARIABLES) or any(
        thread_environment.get(name) != "1" for name in _THREAD_VARIABLES
    ):
        raise ContractError("runtime probe requires all declared numerical thread variables set to one")
    python = python_executable.resolve(strict=True)
    if not python.is_file() or not _CHILD.is_file() or _CHILD.is_symlink():
        raise ContractError("runtime probe executable or script is missing or unsafe")
    environment = {key: value for key, value in os.environ.items() if key in _SAFE_ENVIRONMENT_KEYS}
    environment.update(
        {
            "PYTHONNOUSERSITE": "1",
            "PYTHONHASHSEED": "0",
            "PYTHONIOENCODING": "utf-8",
            **dict(thread_environment),
        }
    )
    completed = subprocess.run(
        [str(python), "-I", str(_CHILD)],
        cwd=_RUNNER_ROOT,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        check=False,
        timeout=timeout_seconds,
    )
    if completed.returncode != 0:
        raise ContractError("isolated runtime provenance probe failed")
    try:
        report = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("runtime provenance probe returned invalid JSON") from exc
    if not isinstance(report, dict) or report.get("schema") != "qf-wp12-child-environment-v1":
        raise ContractError("runtime provenance probe returned an unsupported report")
    if report.get("python_executable") != str(python):
        raise ContractError("runtime provenance probe used a different Python executable")
    return report


def runtime_environment_mismatches(
    report: Mapping[str, Any],
    *,
    expected_python_sha256: str,
    expected_python_version: str,
    expected_packages: Mapping[str, str],
    expected_native_hashes: Mapping[str, str],
    expected_threads: Mapping[str, str],
    expected_venv_root: Path,
    expected_base_root: Path | None = None,
) -> tuple[str, ...]:
    """Compare observed child metadata against the frozen execution manifest."""
    errors: list[str] = []
    if report.get("python_executable_sha256") != expected_python_sha256:
        errors.append("PYTHON_EXECUTABLE_HASH_MISMATCH")
    if report.get("python_version") != expected_python_version:
        errors.append("PYTHON_VERSION_MISMATCH")
    if report.get("virtual_environment") is not True or report.get("include_system_site_packages") is not False:
        errors.append("PYTHON_ENVIRONMENT_NOT_ISOLATED")
    if Path(str(report.get("prefix", ""))).resolve(strict=False) != expected_venv_root.resolve(strict=False):
        errors.append("VENV_ROOT_MISMATCH")
    if expected_base_root is not None and Path(str(report.get("base_prefix", ""))).resolve(
        strict=False
    ) != expected_base_root.resolve(strict=False):
        errors.append("PYTHON_BASE_ROOT_MISMATCH")
    observed_packages = report.get("packages")
    if not isinstance(observed_packages, Mapping):
        errors.append("PYTHON_PACKAGE_PROVENANCE_MISSING")
    else:
        for name, version in expected_packages.items():
            if observed_packages.get(name) != version:
                errors.append(f"PACKAGE_VERSION_MISMATCH:{name}")
        if observed_packages.get("qf-solver") is not None:
            errors.append("GLOBAL_QF_SOLVER_DISTRIBUTION_PRESENT_IN_VENV")
    observed_native = report.get("native_libraries_sha256")
    if not isinstance(observed_native, Mapping):
        errors.append("NATIVE_LIBRARY_PROVENANCE_MISSING")
    elif dict(observed_native) != dict(expected_native_hashes):
        errors.append("NATIVE_LIBRARY_INVENTORY_MISMATCH")
    if report.get("thread_environment") != dict(expected_threads):
        errors.append("THREAD_ENVIRONMENT_MISMATCH")
    return tuple(errors)
