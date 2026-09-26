"""Copy the completed WP08 R3 diagnostic outside Git and hash every file.

This utility only copies and hashes existing evidence. It does not run a
solver, alter the source evidence, or delete either copy.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path(
    r"C:\Users\fari\AppData\Local\Temp\qf_solver_wp08_surface_diagnostic_20260926_r3"
)
DEFAULT_MANIFEST = ROOT / (
    "qualification/0_2_9/wp08_surface_stiffness_remediation/"
    "r3_raw_archive_manifest.json"
)
REQUIRED_FILES = (
    "diagnostic_contract.json",
    "source_file_manifest.json",
    "final.json",
    "progress.json",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _inventory(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"archive refuses symlinks: {path}")
        if path.is_file():
            entries.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                }
            )
    return entries


def archive(source: Path, destination: Path, manifest_path: Path) -> dict[str, Any]:
    source = source.resolve(strict=True)
    destination = destination.resolve()
    manifest_path = manifest_path.resolve()
    if not source.is_dir():
        raise ValueError(f"source must be a directory: {source}")
    if destination == source or destination.is_relative_to(source) or source.is_relative_to(destination):
        raise ValueError("source and destination must be disjoint directories")
    if destination.is_relative_to(ROOT):
        raise ValueError("raw evidence archive must stay outside the Git worktree")
    if not manifest_path.is_relative_to(ROOT / "qualification/0_2_9/wp08_surface_stiffness_remediation"):
        raise ValueError("manifest must be written in the dedicated WP08 evidence directory")
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite archive destination: {destination}")
    if manifest_path.exists():
        raise FileExistsError(f"refusing to overwrite archive manifest: {manifest_path}")
    missing = [name for name in REQUIRED_FILES if not (source / name).is_file()]
    if missing:
        raise FileNotFoundError(f"source evidence is incomplete; missing: {missing}")

    source_entries = _inventory(source)
    if not source_entries:
        raise ValueError("source evidence directory is empty")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, copy_function=shutil.copy2)
    archived_entries = _inventory(destination)
    if source_entries != archived_entries:
        raise RuntimeError("archive copy verification failed; both source and destination were preserved")

    record: dict[str, Any] = {
        "schema_version": 1,
        "artifact_id": "QF-029-WP08-SURFACE-R3-RAW-ARCHIVE",
        "status": "PASS_LOCAL_ARCHIVE_HASHES_VERIFIED",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_root": str(source),
        "archive_root": str(destination),
        "archive_classification": "LOCAL_STABLE_COPY_NOT_OFFSITE_BACKUP",
        "git_tracked_raw_evidence": False,
        "source_deleted_or_modified": False,
        "structural_solves_run": False,
        "file_count": len(archived_entries),
        "total_bytes": sum(entry["size_bytes"] for entry in archived_entries),
        "files": archived_entries,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    record = archive(args.source, args.destination, args.manifest)
    print(
        json.dumps(
            {
                "status": record["status"],
                "file_count": record["file_count"],
                "total_bytes": record["total_bytes"],
                "archive_root": record["archive_root"],
                "manifest": str(args.manifest.resolve()),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
