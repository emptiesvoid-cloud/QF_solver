"""Controlled manifest writer shared by compact V&V studies."""

from __future__ import annotations

from solveur.paths import project_root

from pathlib import Path

from solveur.io.manifest import (
    command_line,
    discovered_file_entries,
    git_source_state,
    runtime_fingerprint,
    utc_timestamp,
    write_json_file,
)


def write_vnv_manifest(output_dir: str | Path, study_id: str) -> Path:
    """Fingerprint every generated study artifact after a successful run."""
    output = Path(output_dir).resolve()
    root = project_root()
    manifest = output / "vnv_manifest.json"
    source = git_source_state(root)
    source["repository"] = "."
    write_json_file(
        manifest,
        {
            "schema_version": 1,
            "study_id": study_id,
            "generated_utc": utc_timestamp(),
            "source": source,
            "command": command_line(),
            "runtime": runtime_fingerprint(),
            "files": discovered_file_entries(
                output,
                _artifact_role,
                exclude_names=(manifest.name,),
            ),
        },
    )
    return manifest


def _artifact_role(relative_path: str) -> str:
    name = Path(relative_path).name
    if name == "summary.json":
        return "normalized_results"
    if name == "report.md":
        return "owner_review_report"
    if name.endswith(".png"):
        return "figure"
    if name.endswith(".vtu"):
        return "visualization_data"
    return "supporting_artifact"
