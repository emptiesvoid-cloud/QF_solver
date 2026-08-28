"""Small, digest-first evidence manifest helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from solveur.io.manifest import sha256

from .registry import canonical_json


def write_manifest(
    output_dir: Path,
    *,
    source: dict[str, Any],
    registry_digest: str,
    profile: str,
    result_paths: Iterable[Path],
    environment: dict[str, Any],
) -> Path:
    """Write a compact manifest; timestamps intentionally remain runtime metadata."""

    output_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for path in sorted(result_paths):
        resolved = path.resolve()
        if output_dir.resolve() not in resolved.parents:
            raise ValueError(f"Manifest file escapes controlled output directory: {resolved}")
        files.append({"path": resolved.relative_to(output_dir.resolve()).as_posix(), "sha256": sha256(resolved)})
    payload = {
        "schema_version": 1,
        "source": source,
        "timestamp_utc": environment["captured_at_utc"],
        "solver_version": environment["solver_version"],
        "profile": profile,
        "registry_digest": registry_digest,
        "configuration_digest": hashlib.sha256(
            canonical_json({"profile": profile, "registry_digest": registry_digest}).encode("utf-8")
        ).hexdigest(),
        "environment": environment,
        "result_files": files,
        "artifact_policy": "qualification/0_2_6/artifact_policy.json",
        "threshold_source": "qualification/0_2_6/tolerance_policy.json",
    }
    target = output_dir / "manifest.json"
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target
