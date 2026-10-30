"""Read-only execution-environment provenance without importing QF/NumPy/SciPy."""

from __future__ import annotations

import importlib.metadata
import os
from pathlib import Path
import platform
import sys
from typing import Any, Iterable

from .contracts import sha256_file


_DISTRIBUTIONS = ("qf-solver", "numpy", "scipy", "pytest", "psutil", "cryptography", "jsonschema")
_NATIVE_SUFFIXES = {".dll", ".pyd", ".so", ".dylib"}
_THREAD_VARIABLES = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "BLIS_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "NUMEXPR_NUM_THREADS",
)


def _python_executable() -> dict[str, Any]:
    path = Path(sys.executable)
    observed: dict[str, Any] = {"path": str(path), "exists": path.is_file(), "source": "observed"}
    if path.is_file():
        observed["sha256"] = sha256_file(path)
    else:
        observed["sha256"] = None
    return observed


def collect_environment_provenance(
    *,
    declared: dict[str, Any] | None = None,
    repository_root: Path | None = None,
    source_files: Iterable[str] = (),
    test_files: Iterable[str] = (),
    fixture_files: Iterable[str] = (),
) -> dict[str, Any]:
    """Collect metadata and hashes; dynamic imports and loaded-library claims stay unknown."""
    packages: dict[str, Any] = {}
    native_libraries: list[dict[str, Any]] = []
    for name in _DISTRIBUTIONS:
        try:
            distribution = importlib.metadata.distribution(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = {"version": None, "state": "NOT_INSTALLED_OBSERVED"}
            continue
        packages[name] = {
            "version": distribution.version,
            "metadata_path": str(getattr(distribution, "_path", "")),
            "state": "OBSERVED_DISTRIBUTION_METADATA",
        }
        if name in {"numpy", "scipy"}:
            for item in distribution.files or ():
                if Path(item.name).suffix.lower() not in _NATIVE_SUFFIXES:
                    continue
                path = Path(distribution.locate_file(item))
                if path.is_file():
                    native_libraries.append(
                        {"distribution": name, "path": str(path), "sha256": sha256_file(path), "state": "OBSERVED_FILE"}
                    )

    root = repository_root.resolve(strict=True) if repository_root is not None else None

    def input_inventory(paths: Iterable[str]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for relative in sorted(set(paths)):
            if root is None:
                records.append({"path": relative, "state": "UNVERIFIABLE_NO_REPOSITORY_ROOT"})
                continue
            candidate = root.joinpath(*relative.split("/"))
            try:
                candidate.resolve(strict=True).relative_to(root)
                current = root
                safe = True
                for part in candidate.relative_to(root).parts:
                    current = current / part
                    if current.is_symlink() or bool(getattr(current, "is_junction", lambda: False)()):
                        safe = False
                        break
                safe = safe and candidate.is_file()
            except (OSError, ValueError):
                safe = False
            if safe:
                records.append({"path": relative, "sha256": sha256_file(candidate), "state": "OBSERVED_FILE"})
            else:
                records.append({"path": relative, "state": "MISSING_OR_UNSAFE"})
        return records

    solver_distribution = packages.get("qf-solver", {})
    project_solver = root / "src" / "solveur" / "__init__.py" if root is not None else None
    solver_origin = {
        "installed_distribution": solver_distribution,
        "checkout_candidate": str(project_solver) if project_solver is not None else None,
        "checkout_candidate_sha256": sha256_file(project_solver)
        if project_solver is not None and project_solver.is_file()
        else None,
        "actual_child_import_origin": None,
        "actual_child_import_state": "UNVERIFIABLE_WITHOUT_APPROVED_CHILD_INSTRUMENTATION",
    }
    return {
        "schema": "qf-wp12-environment-provenance-v1",
        "declared": dict(declared or {}),
        "observed": {
            "python": {
                **_python_executable(),
                "version": platform.python_version(),
                "prefix": sys.prefix,
                "base_prefix": sys.base_prefix,
                "virtual_environment": sys.prefix != sys.base_prefix,
            },
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "architecture": platform.architecture()[0],
                "platform_string": platform.platform(),
            },
            "packages": packages,
            "native_libraries_from_distribution_metadata": native_libraries,
            "thread_environment": {name: os.environ.get(name) for name in _THREAD_VARIABLES},
            "inputs": {
                "sources": input_inventory(source_files),
                "tests": input_inventory(test_files),
                "fixtures": input_inventory(fixture_files),
            },
            "solver_origin": solver_origin,
        },
        "unverifiable": [
            "libraries dynamically loaded in a future child process",
            "actual BLAS/LAPACK implementation selected at runtime without child instrumentation",
            "actual solver import origin in a future child process",
            "file access isolation and filesystem confinement",
            "machine firmware, OS patch level, and runtime CPU frequency state",
        ],
    }
