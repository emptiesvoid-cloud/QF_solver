"""Shared manifest and fingerprint helpers for evidence artifacts."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


def utc_timestamp() -> str:
    """Return the manifest timestamp format used by evidence bundles."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json_file(path: str | Path, data: dict[str, Any]) -> None:
    """Write an indented UTF-8 JSON file, creating the parent directory."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2), encoding="utf-8")


def sha256(path: str | Path) -> str:
    """Return the SHA-256 fingerprint of a file without loading it fully."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def content_digest(data: bytes) -> str:
    """Return a deterministic digest for in-memory manifest content."""
    digest = hashlib.sha256()
    digest.update(data)
    return digest.hexdigest()


def manifest_file_entry(role: str, path: str | Path, root: str | Path) -> dict[str, Any]:
    """Return one evidence manifest file entry."""
    source = Path(path)
    base = Path(root)
    return {
        "role": role,
        "path": source.resolve().relative_to(base.resolve()).as_posix(),
        "size_bytes": source.stat().st_size,
        "sha256": sha256(source),
    }


def discovered_file_entries(
    root: str | Path,
    role_for_relative_path: Callable[[str], str],
    *,
    exclude_names: tuple[str, ...] = ("evidence_manifest.json",),
) -> list[dict[str, Any]]:
    """Return manifest entries for files discovered under a directory."""
    base = Path(root)
    entries: list[dict[str, Any]] = []
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.name in exclude_names:
            continue
        relative = path.resolve().relative_to(base.resolve()).as_posix()
        entries.append(manifest_file_entry(role_for_relative_path(relative), path, base))
    return entries


def large_artifact_role(relative_path: str) -> str:
    """Map large-scale artifact filenames to stable manifest roles."""
    name = Path(relative_path).name
    if name == "summary.json":
        return "summary"
    if name == "audit_large.json":
        return "audit_large"
    if name == "benchmark_large.json":
        return "benchmark"
    if name == "benchmark_large.md":
        return "benchmark_markdown"
    if name == "input_fingerprint.json":
        return "input_fingerprint"
    if name == "runtime_environment.json":
        return "runtime_environment"
    if name == "displacements_metadata.json":
        return "displacements_metadata"
    if name.startswith("displacements."):
        return "displacements"
    if name.endswith(".xdmf"):
        return "xdmf"
    return Path(relative_path).stem


def is_relative_to(path: Path, root: Path) -> bool:
    """Backport-friendly path containment helper."""
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def git_source_state(project_root: str | Path) -> dict[str, Any]:
    """Return revision and dirty state without requiring a committed baseline."""
    root = Path(project_root)
    revision = _git_output(root, "rev-parse", "HEAD")
    status = _git_output(root, "status", "--porcelain", allow_empty=True)
    return {
        # Evidence may be published. The revision identifies the source; an
        # absolute workstation path adds no reproducible information.
        "repository": ".",
        "revision": revision or "uncommitted",
        "dirty": bool(status) or not revision,
    }


def runtime_fingerprint() -> dict[str, Any]:
    """Return compact platform, dependency and numerical-runtime metadata."""
    packages: dict[str, str | None] = {}
    for name in ("numpy", "scipy", "matplotlib", "h5py", "mpi4py", "petsc4py"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    blas: dict[str, Any] = {}
    try:
        import numpy as np

        config = np.__config__.show(mode="dicts")
        raw_blas = config.get("Build Dependencies", {}).get("blas", {})
        blas = {
            "name": raw_blas.get("name"),
            "version": raw_blas.get("version"),
            "configuration": raw_blas.get("openblas configuration", ""),
        }
    except (AttributeError, TypeError):
        blas = {"name": "unknown", "version": None, "configuration": ""}
    return {
        "python": {"version": sys.version, "executable": sys.executable},
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "packages": packages,
        "blas": blas,
        "parallel_environment": {
            name: os.environ.get(name)
            for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "PETSC_ARCH")
        },
    }


def command_line() -> list[str]:
    """Return the command line that created an evidence bundle."""
    return [str(value) for value in sys.argv]


def locked_environment_fingerprints(project_root: str | Path) -> list[dict[str, Any]]:
    """Fingerprint controlled dependency baselines referenced by evidence."""
    root = Path(project_root)
    records: list[dict[str, Any]] = []
    for name in ("baseline-standard.txt", "baseline-large-linux.txt", "baseline-large-container.txt"):
        relative = f"requirements/{name}"
        project_path = root / relative
        installed_path = Path(sys.prefix) / "requirements" / name
        path = project_path if project_path.is_file() else installed_path
        if path.is_file():
            records.append({"path": relative, "sha256": sha256(path), "size_bytes": path.stat().st_size})
    return records


def _git_output(root: Path, *arguments: str, allow_empty: bool = False) -> str:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if completed.returncode != 0:
        return ""
    value = completed.stdout.strip()
    return value if value or allow_empty else ""
