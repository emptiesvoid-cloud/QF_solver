"""Package controlled Code_Aster correlation evidence without raw work files."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from solveur.io.evidence_verifier import EvidenceBundleVerifier
from solveur.io.manifest import (
    discovered_file_entries,
    git_source_state,
    locked_environment_fingerprints,
    runtime_fingerprint,
    sha256,
    utc_timestamp,
    write_json_file,
)
from solveur.paths import project_root
from solveur.version import DISPLAY_NAME, __version__


KEEP_NAMES = frozenset(
    {
        "summary.json",
        "report.md",
        "vnv_manifest.json",
        "code_aster_raw.json",
        "code_aster_modal_raw.json",
    }
)


def package_campaign(
    input_dir: str | Path,
    catalog_path: str | Path,
    output_dir: str | Path,
) -> Path:
    """Copy controlled campaign artifacts and create a verifiable manifest."""
    root = project_root().resolve()
    source = Path(input_dir).resolve()
    catalog_file = Path(catalog_path).resolve()
    output = Path(output_dir).resolve()
    if not source.is_dir():
        raise FileNotFoundError(f"Code_Aster campaign directory not found: {source}")
    if not catalog_file.is_file():
        raise FileNotFoundError(f"Code_Aster catalog not found: {catalog_file}")
    catalog = json.loads(catalog_file.read_text(encoding="utf-8"))
    studies = catalog.get("studies")
    if not isinstance(studies, list):
        raise ValueError("Code_Aster catalog field 'studies' must be a list.")
    output.mkdir(parents=True, exist_ok=True)
    write_json_file(output / "campaign_catalog.json", catalog)
    for study in studies:
        _copy_study(source, output / "studies", study)
    write_json_file(output / "README.json", _bundle_metadata(catalog, catalog_file, source))
    files = discovered_file_entries(output, _evidence_role)
    runtime = runtime_fingerprint()
    runtime["python"].pop("executable", None)
    runtime["platform"].pop("processor", None)
    runtime["parallel_environment"] = {
        name: bool(value) for name, value in runtime.get("parallel_environment", {}).items()
    }
    manifest = {
        "manifest_schema_version": 2,
        "created_at_utc": utc_timestamp(),
        "solver": {"name": DISPLAY_NAME, "version": __version__},
        "source": git_source_state(root),
        "runtime": runtime,
        "locked_environments": locked_environment_fingerprints(root),
        "command_line": _safe_command_line(root),
        "evidence_kind": "code_aster_external_correlation",
        "input_sha256": sha256(catalog_file),
        "traceability": {
            "scope": "code-aster-correlation-campaign-2026-08-14",
            "status": "READY_FOR_OWNER_REVIEW",
            "qualification_claim": "none",
        },
        "metadata": {
            "source_catalog": _display_path(catalog_file, root),
            "source_directory": _display_path(source, root),
            "selected_file_policy": sorted(KEEP_NAMES) + ["*.png"],
            "study_count": len(studies),
            "catalog_summary": catalog.get("summary", {}),
        },
        "file_count": len(files),
        "files": files,
    }
    write_json_file(output / "evidence_manifest.json", manifest)
    report = EvidenceBundleVerifier().verify(output)
    if report.status != "PASS":
        details = "; ".join(report.errors) or "unknown evidence verification error"
        raise RuntimeError(f"Packaged Code_Aster evidence is invalid: {details}")
    return output


def _copy_study(source: Path, destination_root: Path, study: Any) -> None:
    if not isinstance(study, dict):
        raise ValueError("Every Code_Aster catalog study must be an object.")
    directory_value = study.get("directory")
    if not directory_value:
        raise ValueError("Every Code_Aster catalog study must declare a directory.")
    study_source = Path(str(directory_value))
    if not study_source.is_absolute():
        study_source = (project_root() / study_source).resolve()
    else:
        study_source = study_source.resolve()
    if not study_source.is_dir():
        _write_study_record(destination_root, study)
        return
    name = study_source.name
    destination = destination_root / name
    destination.mkdir(parents=True, exist_ok=True)
    copied = False
    for path in sorted(study_source.iterdir()):
        if path.is_file() and (
            path.name in KEEP_NAMES
            or path.suffix.lower() in {".md", ".png"}
        ):
            shutil.copy2(path, destination / path.name)
            copied = True
    if not copied:
        _write_study_record(destination_root, study)


def _write_study_record(destination_root: Path, study: dict[str, Any]) -> None:
    directory = Path(str(study.get("directory", "unavailable")))
    destination = destination_root / directory.name
    destination.mkdir(parents=True, exist_ok=True)
    write_json_file(destination / "record.json", study)


def _bundle_metadata(catalog: dict[str, Any], catalog_file: Path, source: Path) -> dict[str, Any]:
    root = project_root().resolve()
    return {
        "purpose": "Controlled Code_Aster correlation evidence for Owner review.",
        "solver": DISPLAY_NAME,
        "catalog": catalog.get("catalog_id"),
        "catalog_path": _display_path(catalog_file, root),
        "source_directory": _display_path(source, root),
        "raw_work_files_excluded": True,
        "owner_decision": "pending",
        "certification_claim": "none",
    }


def _display_path(path: Path, root: Path) -> str:
    """Expose a repository-relative path without leaking workstation paths."""
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return f"<external>/{path.name}"


def _safe_command_line(root: Path) -> list[str]:
    """Keep command semantics while removing absolute workstation locations."""
    values: list[str] = []
    for raw in sys.argv:
        value = str(raw)
        candidate = Path(value)
        if candidate.is_absolute():
            value = _display_path(candidate, root)
        values.append(value)
    return values


def _evidence_role(relative_path: str) -> str:
    name = Path(relative_path).name
    if name == "campaign_catalog.json":
        return "campaign_catalog"
    if name == "README.json":
        return "bundle_metadata"
    if name == "record.json":
        return "study_record"
    if name == "summary.json":
        return "summary"
    if name.endswith(".md"):
        return "report"
    if name == "vnv_manifest.json":
        return "study_manifest"
    if name.endswith("_raw.json"):
        return "external_raw_result"
    if name.endswith(".png"):
        return "figure"
    return "campaign_artifact"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="tmp/code_aster")
    parser.add_argument(
        "--catalog",
        default="qualification/external_reference_digests/code_aster_correlation_campaign_2026-08-14.json",
    )
    parser.add_argument(
        "--output",
        default="qualification/evidence/code_aster_correlation_campaign_2026-08-14",
    )
    args = parser.parse_args()
    output = package_campaign(args.input, args.catalog, args.output)
    print("CODE_ASTER EVIDENCE: PASS")
    print(f"bundle: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
