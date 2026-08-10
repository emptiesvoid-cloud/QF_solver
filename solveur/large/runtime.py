"""Runtime traceability for large-scale evidence bundles."""

from __future__ import annotations

import importlib.metadata as importlib_metadata
import importlib.util
import json
import os
import platform
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
        "metadata": metadata or {},
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
        "executable": sys.executable,
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
        "cwd": str(Path.cwd().resolve()),
        "argv": list(sys.argv),
    }


def _environment_report() -> dict[str, str | None]:
    return {name: os.environ.get(name) for name in TRACKED_ENVIRONMENT_VARIABLES}


def _package_report(name: str) -> dict[str, Any]:
    spec = importlib.util.find_spec(name)
    try:
        version = importlib_metadata.version(name)
    except importlib_metadata.PackageNotFoundError:
        version = None
    return {
        "available": spec is not None,
        "version": version,
        "origin": str(spec.origin) if spec is not None and spec.origin is not None else None,
    }
