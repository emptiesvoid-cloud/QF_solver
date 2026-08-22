"""Create a tracked index for local Code_Aster correlation evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from solveur.io.manifest import (
    git_source_state,
    manifest_file_entry,
    runtime_fingerprint,
    sha256,
    utc_timestamp,
    write_json_file,
)
from solveur.paths import project_root


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return f"<external>/{path.name}"


def _read_summary(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _file_entry(path: Path, root: Path) -> dict[str, Any]:
    try:
        return manifest_file_entry("campaign_artifact", path, root)
    except ValueError:
        return {
            "role": "campaign_artifact",
            "path": f"<external>/{path.name}",
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        }


def _study_record(study_dir: Path, root: Path) -> dict[str, Any]:
    summary_path = study_dir / "summary.json"
    summary = _read_summary(summary_path) if summary_path.is_file() else None
    record: dict[str, Any] = {
        "directory": _relative(study_dir, root),
        "summary": None,
        "study_id": None,
        "status": "UNAVAILABLE",
        "maturity": None,
        "artifacts": [],
    }
    if summary is not None:
        record.update(
            {
                "summary": _file_entry(summary_path, root),
                "study_id": summary.get("study_id"),
                "status": summary.get("status", "UNKNOWN"),
                "maturity": summary.get("maturity"),
            }
        )
        external_solver = summary.get("external_solver")
        if isinstance(external_solver, dict):
            record["external_solver"] = external_solver
    patterns = ("report.md", "vnv_manifest.json", "*.png", "*.json")
    artifacts: list[dict[str, Any]] = []
    for pattern in patterns:
        for path in sorted(study_dir.glob(pattern)):
            if path == summary_path or not path.is_file():
                continue
            artifacts.append(_file_entry(path, root))
    record["artifacts"] = artifacts
    if summary is None:
        record["missing"] = ["summary.json"]
    return record


def build_catalog(
    input_dir: str | Path,
    output_path: str | Path,
    *,
    excluded_directories: set[str] | None = None,
) -> dict[str, Any]:
    """Build an index without copying or loading large evidence files."""
    root = project_root().resolve()
    source = (root / input_dir).resolve() if not Path(input_dir).is_absolute() else Path(input_dir).resolve()
    output = (root / output_path).resolve() if not Path(output_path).is_absolute() else Path(output_path).resolve()
    studies = []
    excluded = excluded_directories or set()
    if source.is_dir():
        studies = [
            _study_record(directory, root)
            for directory in sorted(source.iterdir())
            if directory.is_dir() and directory.name not in excluded
        ]
    runtime = runtime_fingerprint()
    runtime["python"].pop("executable", None)
    runtime["platform"].pop("processor", None)
    runtime["parallel_environment"] = {
        name: bool(value) for name, value in runtime.get("parallel_environment", {}).items()
    }
    return {
        "schema_version": 1,
        "catalog_id": "CODE-ASTER-CORRELATION-2026-08-14",
        "generated_utc": utc_timestamp(),
        "input_directory": _relative(source, root),
        "output": _relative(output, root),
        "source": git_source_state(root),
        "runtime": runtime,
        "studies": studies,
        "summary": {
            "study_count": len(studies),
            "excluded_directories": sorted(excluded),
            "pass_external_correlation": sum(
                study["status"] == "PASS_EXTERNAL_CORRELATION" for study in studies
            ),
            "warning": sum(study["status"] == "WARNING" for study in studies),
            "failure": sum(
                study["status"] not in {"PASS_EXTERNAL_CORRELATION", "WARNING", "UNAVAILABLE"}
                for study in studies
            ),
            "unavailable": sum(study["status"] == "UNAVAILABLE" for study in studies),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="tmp/code_aster")
    parser.add_argument(
        "--output",
        default="qualification/external_reference_digests/code_aster_correlation_campaign_2026-08-14.json",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Directory name to omit from the tracked campaign catalog.",
    )
    args = parser.parse_args()
    catalog = build_catalog(args.input, args.output, excluded_directories=set(args.exclude))
    write_json_file(args.output, catalog)
    print(json.dumps(catalog["summary"], indent=2))
    print(f"catalog: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
