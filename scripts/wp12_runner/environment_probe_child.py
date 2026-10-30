"""Collect non-numerical provenance from the exact candidate Python process."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys


PACKAGES = (
    "qf-solver",
    "numpy",
    "scipy",
    "pytest",
    "pytest-cov",
    "psutil",
    "cryptography",
    "jsonschema",
    "matplotlib",
    "h5py",
    "threadpoolctl",
    "coverage",
    "ruff",
    "mypy",
    "hypothesis",
    "PyYAML",
)
NATIVE_SUFFIXES = {".dll", ".pyd", ".so", ".dylib"}
THREAD_VARIABLES = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "BLIS_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "NUMEXPR_NUM_THREADS",
)


def main() -> int:
    packages: dict[str, str | None] = {}
    native: dict[str, str] = {}
    for name in PACKAGES:
        try:
            distribution = importlib.metadata.distribution(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
            continue
        packages[name] = distribution.version
        if name not in {"numpy", "scipy"}:
            continue
        for item in distribution.files or ():
            if Path(item.name).suffix.lower() not in NATIVE_SUFFIXES:
                continue
            candidate = Path(distribution.locate_file(item))
            if candidate.is_file():
                native[f"{name}/{item.as_posix()}"] = hashlib.sha256(candidate.read_bytes()).hexdigest()

    executable = Path(sys.executable).resolve()
    venv_config = Path(sys.prefix) / "pyvenv.cfg"
    include_system = False
    if venv_config.is_file():
        include_system = any(
            line.strip().lower() == "include-system-site-packages = true"
            for line in venv_config.read_text(encoding="utf-8").splitlines()
        )
    report = {
        "schema": "qf-wp12-child-environment-v1",
        "python_executable": str(executable),
        "python_executable_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "architecture": platform.architecture()[0],
        "platform": platform.platform(),
        "prefix": str(Path(sys.prefix).resolve()),
        "base_prefix": str(Path(sys.base_prefix).resolve()),
        "virtual_environment": sys.prefix != sys.base_prefix,
        "include_system_site_packages": include_system,
        "packages": packages,
        "native_libraries_sha256": dict(sorted(native.items())),
        "thread_environment": {name: os.environ.get(name) for name in THREAD_VARIABLES},
    }
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
