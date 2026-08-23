"""Runtime traceability for large-scale evidence bundles."""

from __future__ import annotations

import importlib.metadata as importlib_metadata
import importlib.util
import json
import os
import platform
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from solveur.version import DISPLAY_NAME, __version__

DEFAULT_PACKAGES = ("numpy", "scipy", "h5py", "mpi4py", "petsc4py")
TRACKED_ENVIRONMENT_VARIABLES = (
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "PYTHONHASHSEED",
    "PETSC_DIR",
    "PETSC_ARCH",
)
_WINDOWS_PATH_PREFIX = r"[a-z]:[\\/]+"
_UNIX_PATH_PREFIX = "/" + r"(?:home|users)/"
_NETWORK_PATH_PREFIX = r"\\\\" + "users\\\\"
_ABSOLUTE_PATH = re.compile(
    rf"(?i)(?:{_WINDOWS_PATH_PREFIX}|{_UNIX_PATH_PREFIX}|{_NETWORK_PATH_PREFIX})"
)
_PATH_ENVIRONMENT_VARIABLES = {"PETSC_DIR", "PETSC_ARCH"}


def collect_runtime_environment(
    metadata: dict[str, Any] | None = None,
    *,
    packages: tuple[str, ...] = DEFAULT_PACKAGES,
) -> dict[str, Any]:
    """Return a reproducible, non-secret runtime report for a large-scale run."""
    return {
        "report_schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "solver": {"name": DISPLAY_NAME, "version": __version__},
        "python": _python_report(),
        "platform": _platform_report(),
        "process": _process_report(),
        "environment": _environment_report(),
        "packages": {name: _package_report(name) for name in packages},
        "metadata": _portable_value(metadata or {}),
    }


def write_runtime_environment(
    directory: str | Path,
    metadata: dict[str, Any] | None = None,
    *,
    filename: str = "runtime_environment.json",
) -> Path:
    """Write runtime_environment.json in an evidence directory."""
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    path = root / filename
    report = collect_runtime_environment(metadata)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path


def _python_report() -> dict[str, Any]:
    return {
        "version": sys.version,
        "version_info": list(sys.version_info[:5]),
        "executable": Path(sys.executable).name,
        "implementation": platform.python_implementation(),
        "compiler": platform.python_compiler(),
        "build": list(platform.python_build()),
    }


def _platform_report() -> dict[str, Any]:
    return {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "architecture": list(platform.architecture()),
    }


def _process_report() -> dict[str, Any]:
    return {
        "pid": os.getpid(),
        "cwd": ".",
        "argv": [_portable_value(argument) for argument in sys.argv],
    }


def _environment_report() -> dict[str, str | None]:
    values: dict[str, str | None] = {}
    for name in TRACKED_ENVIRONMENT_VARIABLES:
        value = os.environ.get(name)
        values[name] = "<set>" if value and name in _PATH_ENVIRONMENT_VARIABLES else value
    return values


def _package_report(name: str) -> dict[str, Any]:
    spec = importlib.util.find_spec(name)
    try:
        version = importlib_metadata.version(name)
    except importlib_metadata.PackageNotFoundError:
        version = None
    return {
        "available": spec is not None,
        "version": version,
        "origin": Path(spec.origin).name if spec is not None and spec.origin is not None else None,
    }


def _portable_value(value: Any) -> Any:
    """Remove absolute workstation paths from recursively stored evidence data."""
    if isinstance(value, dict):
        return {key: _portable_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_portable_value(item) for item in value]
    if isinstance(value, tuple):
        return [_portable_value(item) for item in value]
    if isinstance(value, str) and _ABSOLUTE_PATH.search(value):
        return _ABSOLUTE_PATH.sub("<absolute-path>", value)
    return value
