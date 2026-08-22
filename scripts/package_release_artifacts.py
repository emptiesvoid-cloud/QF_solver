"""Archive reproducible release artifacts without exposing workstation paths.

The historical V&V registry contains paths from ignored working directories.
This script creates a small, controlled archive of the artifacts that are
actually present.  It never invents a missing result: absent or unsupported
paths remain explicitly listed in ``artifact_catalog.json``.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from solveur.io.evidence_verifier import EvidenceBundleVerifier
from solveur.io.manifest import (
    discovered_file_entries,
    git_source_state,
    locked_environment_fingerprints,
    sha256,
    utc_timestamp,
    write_json_file,
    runtime_fingerprint,
)
from solveur.paths import project_path, project_root
from solveur.version import DISPLAY_NAME, __version__


DEFAULT_REQUIREMENTS = project_path("qualification/requirements.json")
DEFAULT_OUTPUT = project_path("qualification/evidence/release_vv_artifacts_2026-08-14-r6")
SAFE_SUFFIXES = frozenset({".csv", ".json", ".md", ".pdf", ".png", ".svg", ".txt", ".vtu"})
MAX_FILE_BYTES = 25 * 1024 * 1024
_PRIVATE_PREFIXES = (
    "[A-Za-z]" + ":" + r"[\\/]",
    "/" + "home" + "/",
    "/" + "Users" + "/",
    "/" + "mnt" + "/",
)
PRIVATE_PATH = re.compile(r"(?:" + "|".join(_PRIVATE_PREFIXES) + r")[^\s`\"']+")
SENSITIVE_KEYS = frozenset(
    {
        "command_line",
        "cwd",
        "executable",
        "input_path",
        "processor",
        "source_directory",
        "source_input_path",
        "source_path",
        "workdir",
    }
)


def package_release_artifacts(
    requirements_path: str | Path = DEFAULT_REQUIREMENTS,
    output_dir: str | Path = DEFAULT_OUTPUT,
) -> Path:
    """Archive present requirement artifacts and write a verifiable index."""
    requirements_file = Path(requirements_path).resolve()
    project = project_root().resolve()
    try:
        requirements_file.relative_to(project)
        root = project
    except ValueError:
        # Small isolated registries are useful for unit tests and downstream
        # tooling; their relative artifacts are resolved beside the registry.
        root = requirements_file.parent.resolve()
    output = Path(output_dir).resolve()
    if not requirements_file.is_file():
        raise FileNotFoundError(f"Requirements registry not found: {requirements_file}")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Output directory is not empty: {output}")
    data = json.loads(requirements_file.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("requirements"), list):
        raise ValueError("Requirements registry must contain a requirements list.")

    output.mkdir(parents=True, exist_ok=True)
    contents = output / "contents"
    aliases: dict[str, str] = {}
    records: dict[str, dict[str, Any]] = {}
    artifact_paths = _artifact_paths(data)
    for relative in artifact_paths:
        source = _safe_source_path(root, relative)
        if source is None or not source.exists():
            records[relative] = {"status": "MISSING", "source": relative}
            continue
        destination = contents / Path(relative)
        if source.is_file():
            copied = _copy_safe_file(source, destination, root)
            if copied:
                aliases[relative] = _relative_to_root(destination, root)
                records[relative] = {
                    "status": "ARCHIVED",
                    "source": relative,
                    "path": aliases[relative],
                    "kind": "file",
                }
            else:
                records[relative] = {"status": "UNSUPPORTED", "source": relative}
            continue

        copied_files = 0
        for child in sorted(path for path in source.rglob("*") if path.is_file()):
            child_relative = child.relative_to(root).as_posix()
            child_destination = contents / child_relative
            copied_files += int(_copy_safe_file(child, child_destination, root))
        if copied_files:
            aliases[relative] = _relative_to_root(destination, root)
            records[relative] = {
                "status": "ARCHIVED",
                "source": relative,
                "path": aliases[relative],
                "kind": "directory",
                "file_count": copied_files,
            }
        else:
            records[relative] = {"status": "UNSUPPORTED", "source": relative}

    alias_file = output / "artifact_aliases.json"
    write_json_file(
        alias_file,
        {
            "schema_version": 1,
            "generated_at_utc": utc_timestamp(),
            "purpose": "Resolve historical requirement artifact paths to controlled copies.",
            "aliases": aliases,
        },
    )
    catalog = {
        "schema_version": 1,
        "catalog_id": "release-vv-artifacts-2026-08-14",
        "solver": {"name": DISPLAY_NAME, "version": __version__},
        "requirements_registry": _display_path(requirements_file, root),
        "generated_at_utc": utc_timestamp(),
        "policy": {
            "missing_artifacts_remain_open": True,
            "raw_work_files_excluded": True,
            "maximum_file_size_bytes": MAX_FILE_BYTES,
            "safe_suffixes": sorted(SAFE_SUFFIXES),
        },
        "summary": {
            "requested_count": len(records),
            "archived_count": sum(item["status"] == "ARCHIVED" for item in records.values()),
            "missing_count": sum(item["status"] == "MISSING" for item in records.values()),
            "unsupported_count": sum(item["status"] == "UNSUPPORTED" for item in records.values()),
        },
        "artifacts": records,
        "aliases_file": _relative_to_root(alias_file, root),
    }
    write_json_file(output / "artifact_catalog.json", catalog)
    write_json_file(
        output / "README.json",
        {
            "purpose": "Controlled release V&V artifact archive.",
            "solver": DISPLAY_NAME,
            "owner_decision": "pending",
            "certification_claim": "none",
            "missing_artifacts_are_not_replaced": True,
            "catalog": "artifact_catalog.json",
        },
    )
    (output / "README.md").write_text(_render_readme(catalog), encoding="utf-8")
    manifest = _manifest(root, requirements_file, output, catalog)
    write_json_file(output / "evidence_manifest.json", manifest)
    report = EvidenceBundleVerifier().verify(output)
    if report.status != "PASS":
        details = "; ".join(report.errors) or "unknown evidence verification error"
        raise RuntimeError(f"Release artifact bundle is invalid: {details}")
    return output


def _artifact_paths(data: dict[str, Any]) -> list[str]:
    paths: set[str] = set()
    for requirement in data.get("requirements", []):
        if not isinstance(requirement, dict):
            continue
        for value in requirement.get("artifacts", []):
            if isinstance(value, str) and value:
                paths.add(value)
    return sorted(paths)


def _safe_source_path(root: Path, relative: str) -> Path | None:
    candidate = Path(relative)
    if candidate.is_absolute():
        return None
    try:
        resolved = (root / candidate).resolve()
        resolved.relative_to(root)
    except ValueError:
        return None
    return resolved


def _copy_safe_file(source: Path, destination: Path, root: Path) -> bool:
    if source.name == "evidence_manifest.json" or source.suffix.lower() not in SAFE_SUFFIXES:
        return False
    if source.stat().st_size > MAX_FILE_BYTES:
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    suffix = source.suffix.lower()
    if suffix == ".json":
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return False
        destination.write_text(
            json.dumps(_redact_value(data, root, key=""), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return True
    if suffix in {".md", ".txt", ".csv"}:
        try:
            text = source.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return False
        destination.write_text(_redact_text(text, root), encoding="utf-8")
        return True
    shutil.copy2(source, destination)
    return True


def _redact_value(value: Any, root: Path, *, key: str) -> Any:
    if isinstance(value, dict):
        return {str(name): _redact_value(item, root, key=str(name)) for name, item in value.items()}
    if isinstance(value, list):
        return [_redact_value(item, root, key=key) for item in value]
    if isinstance(value, str):
        return _redact_text(value, root) if key in SENSITIVE_KEYS else _redact_text(value, root)
    return value


def _redact_text(value: str, root: Path) -> str:
    result = value.replace(str(root), "<project>").replace(root.as_posix(), "<project>")
    return PRIVATE_PATH.sub("<redacted-path>", result)


def _relative_to_root(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root).as_posix()


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return f"<external>/{path.name}"


def _manifest(root: Path, requirements_file: Path, output: Path, catalog: dict[str, Any]) -> dict[str, Any]:
    manifest_root = project_root().resolve()
    runtime = runtime_fingerprint()
    runtime.get("python", {}).pop("executable", None)
    runtime.get("platform", {}).pop("processor", None)
    runtime["parallel_environment"] = {
        name: bool(value) for name, value in runtime.get("parallel_environment", {}).items()
    }
    return {
        "manifest_schema_version": 2,
        "created_at_utc": utc_timestamp(),
        "solver": {"name": DISPLAY_NAME, "version": __version__},
        "source": git_source_state(manifest_root),
        "runtime": runtime,
        "locked_environments": locked_environment_fingerprints(manifest_root),
        "command_line": _safe_command_line(manifest_root),
        "evidence_kind": "release_vv_artifact_archive",
        "input_sha256": sha256(requirements_file),
        "traceability": {
            "status": "READY_FOR_OWNER_REVIEW",
            "qualification_claim": "none",
            "missing_artifacts_remain_open": True,
        },
        "metadata": {
            "catalog": "artifact_catalog.json",
            "requirements_registry": _display_path(requirements_file, manifest_root),
            "summary": catalog["summary"],
        },
        "file_count": len(discovered_file_entries(output, _evidence_role)),
        "files": discovered_file_entries(output, _evidence_role),
    }


def _safe_command_line(root: Path) -> list[str]:
    values: list[str] = []
    for raw in sys.argv:
        value = str(raw)
        candidate = Path(value)
        try:
            value = candidate.resolve().relative_to(root).as_posix()
        except (ValueError, OSError):
            value = _redact_text(value, root)
        values.append(value)
    return values


def _evidence_role(relative_path: str) -> str:
    name = Path(relative_path).name
    if name == "artifact_catalog.json":
        return "artifact_catalog"
    if name == "artifact_aliases.json":
        return "artifact_aliases"
    if name == "README.json":
        return "bundle_metadata"
    if name == "README.md":
        return "bundle_readme"
    if name == "summary.json":
        return "summary"
    if name == "report.md":
        return "report"
    if name == "vnv_manifest.json":
        return "study_manifest"
    if name.endswith(".png") or name.endswith(".svg"):
        return "figure"
    return "artifact"


def _render_readme(catalog: dict[str, Any]) -> str:
    summary = catalog["summary"]
    return "\n".join(
        [
            "# Controlled release V&V artifacts",
            "",
            "This archive contains only artifacts present in the current checkout.",
            "Historical paths are mapped through `artifact_aliases.json` when a",
            "controlled copy was possible. Missing and unsupported paths remain",
            "open and are not replaced by placeholders.",
            "",
            f"- Requested paths: {summary['requested_count']}",
            f"- Archived paths: {summary['archived_count']}",
            f"- Missing paths: {summary['missing_count']}",
            f"- Unsupported paths: {summary['unsupported_count']}",
            "- Owner decision: pending",
            "- Certification claim: none",
            "",
            "Use `artifact_catalog.json` for the machine-readable status and",
            "`evidence_manifest.json` for SHA-256 integrity verification.",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requirements", type=Path, default=DEFAULT_REQUIREMENTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = package_release_artifacts(args.requirements, args.output)
    print("RELEASE ARTIFACT ARCHIVE: PASS")
    print(f"bundle: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
