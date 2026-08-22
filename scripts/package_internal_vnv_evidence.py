"""Package the small internal linear-dynamics V&V campaign."""

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


KEEP_NAMES = frozenset({"summary.json", "report.md"})


def package_internal_vnv(
    input_dir: str | Path,
    output_dir: str | Path,
) -> Path:
    """Copy sanitized family results and create a verifiable bundle."""
    root = project_root().resolve()
    source = Path(input_dir).resolve()
    output = Path(output_dir).resolve()
    if not source.is_dir():
        raise FileNotFoundError(f"internal V&V directory not found: {source}")

    families = _discover_families(source)
    if not families:
        raise ValueError("internal V&V directory contains no complete family study")
    if any(str(item["status"]) != "PASS" for item in families):
        raise ValueError("internal V&V bundle requires PASS family studies")

    output.mkdir(parents=True, exist_ok=True)
    for item in families:
        destination = output / str(item["family"]).lower()
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item["summary_path"], destination / "summary.json")
        shutil.copy2(item["report_path"], destination / "report.md")

    metadata = {
        "purpose": "Controlled internal linear-dynamics V&V evidence.",
        "solver": DISPLAY_NAME,
        "solver_version": __version__,
        "campaign": "linear_dynamic_families",
        "source_directory": _display_path(source, root),
        "families": [
            {"family": item["family"], "study_id": item["study_id"], "status": item["status"]}
            for item in families
        ],
        "owner_decision": "pending",
        "external_correlation": "not included; Code_Aster evidence is tracked separately",
        "certification_claim": "none",
    }
    write_json_file(output / "README.json", metadata)
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
        "evidence_kind": "internal_linear_dynamics_vnv",
        "input_sha256": sha256(output / "README.json"),
        "traceability": {
            "scope": "linear-dynamic-families",
            "status": "READY_FOR_OWNER_REVIEW",
            "qualification_claim": "none",
        },
        "metadata": {
            "source_directory": _display_path(source, root),
            "selected_file_policy": sorted(KEEP_NAMES),
            "family_count": len(families),
        },
        "file_count": len(files),
        "files": files,
    }
    write_json_file(output / "evidence_manifest.json", manifest)
    report = EvidenceBundleVerifier().verify(output)
    if report.status != "PASS":
        details = "; ".join(report.errors) or "unknown evidence verification error"
        raise RuntimeError(f"internal V&V evidence is invalid: {details}")
    return output


def _discover_families(source: Path) -> list[dict[str, Any]]:
    families: list[dict[str, Any]] = []
    for directory in sorted(path for path in source.iterdir() if path.is_dir()):
        summary_path = directory / "summary.json"
        report_path = directory / "report.md"
        if not summary_path.is_file() or not report_path.is_file():
            continue
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid summary: {summary_path}") from exc
        if not isinstance(summary, dict):
            raise ValueError(f"summary must be an object: {summary_path}")
        families.append(
            {
                "family": str(summary.get("family", directory.name)),
                "study_id": str(summary.get("study_id", directory.name)),
                "status": str(summary.get("status", "UNKNOWN")),
                "summary_path": summary_path,
                "report_path": report_path,
            }
        )
    return families


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return f"<external>/{path.name}"


def _safe_command_line(root: Path) -> list[str]:
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
    if name == "README.json":
        return "bundle_metadata"
    if name == "summary.json":
        return "summary"
    if name == "report.md":
        return "report"
    return "campaign_artifact"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="qualification/vnv/linear_dynamic_families")
    parser.add_argument(
        "--output",
        default="qualification/evidence/linear_dynamic_families_2026-08-14",
    )
    args = parser.parse_args()
    output = package_internal_vnv(args.input, args.output)
    print("INTERNAL V&V EVIDENCE: PASS")
    print(f"bundle: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
