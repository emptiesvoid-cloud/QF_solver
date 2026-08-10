"""Evidence manifests for large-scale solver outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from solveur.io.manifest import (
    command_line,
    discovered_file_entries,
    git_source_state,
    large_artifact_role,
    locked_environment_fingerprints,
    runtime_fingerprint,
    utc_timestamp,
    write_json_file,
)
from solveur.version import DISPLAY_NAME, __version__
from solveur.verification.traceability import qualification_readiness


def write_large_manifest(directory: str | Path, metadata: dict[str, Any] | None = None) -> Path:
    """Write an evidence_manifest.json covering large-scale output artifacts."""
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    manifest_path = root / "evidence_manifest.json"
    files = discovered_file_entries(root, large_artifact_role)
    input_entry = next(
        (entry for entry in files if entry["role"] in {"input_fingerprint", "model"}),
        None,
    )
    input_fingerprint: object = (
        input_entry["sha256"]
        if input_entry is not None
        else {"status": "unavailable", "reason": "no solver input was generated for this evidence stage"}
    )
    manifest = {
        "manifest_schema_version": 2,
        "created_at_utc": utc_timestamp(),
        "solver": {"name": DISPLAY_NAME, "version": __version__},
        "source": git_source_state(Path(__file__).resolve().parents[2]),
        "runtime": runtime_fingerprint(),
        "locked_environments": locked_environment_fingerprints(Path(__file__).resolve().parents[2]),
        "command_line": command_line(),
        "evidence_kind": "large_scale",
        "input_sha256": input_fingerprint,
        "traceability": qualification_readiness("large-tet4-linear-static").to_dict(),
        "metadata": metadata or {},
        "file_count": len(files),
        "files": files,
    }
    write_json_file(manifest_path, manifest)
    return manifest_path
