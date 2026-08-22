"""Evaluate the explicit gates required before a public QF_solver release."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Sequence

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 uses the optional test dependency.
    import tomli as tomllib

if __package__:
    from scripts.audit_public_release import audit_public_release
    from scripts.audit_git_history import audit_git_history_paths
    from scripts.audit_release_archive import audit_release_archive
    from scripts.git_tools import git_command
else:
    # Support direct execution with ``python scripts/release_readiness.py``.
    from audit_public_release import audit_public_release  # type: ignore[no-redef]
    from audit_git_history import audit_git_history_paths  # type: ignore[no-redef]
    from audit_release_archive import audit_release_archive  # type: ignore[no-redef]
    from git_tools import git_command  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[1]
_GOVERNANCE_FILES = (
    "LICENSE",
    "LICENSE-DOCS",
    "NOTICE",
    "THIRD_PARTY_LICENSES.md",
    "OPEN_SOURCE_READINESS.md",
    "PUBLIC_RELEASE_POLICY.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "SUPPORT.md",
    "CHANGELOG.md",
)


def release_readiness(root: str | Path = ROOT) -> dict[str, object]:
    """Return a deterministic release-gate report including the archive contents."""
    base = Path(root).resolve()
    project = _project_metadata(base)
    version = str(project.get("version", ""))
    audit = audit_public_release(base)
    archive = audit_release_archive(base)
    history = audit_git_history_paths(base)
    checks = [
        _check("public_source_audit", audit["status"] == "PASS", "No prohibited public-source marker found."),
        _check("release_archive_audit", archive["status"] == "PASS", "Git archive contains no excluded runtime or private evidence tree."),
        _check(
            "git_history_audit",
            history["status"] == "PASS",
            "The public branch must have no reachable private or internal history marker.",
        ),
        _check(
            "governance_documents",
            all((base / name).is_file() for name in _GOVERNANCE_FILES),
            "Required release and contributor documents are present.",
        ),
        _check("license_selected", _license_selected(base, project), "A root LICENSE and non-proprietary package metadata are required for public release."),
        _check(
            "changelog_version",
            bool(version) and f"## {version}" in _read_text(base / "CHANGELOG.md"),
            "CHANGELOG.md must contain a dated release section for the package version.",
        ),
        _git_clean_check(base),
        _git_tag_check(base, version),
    ]
    failures = [item["id"] for item in checks if item["status"] != "PASS"]
    return {
        "status": "READY" if not failures else "NOT_READY",
        "version": version,
        "source_audit": audit,
        "archive_audit": archive,
        "history_audit": history,
        "checks": checks,
        "blocking_gates": failures,
        "manual_actions": [
            "Review the Apache-2.0 and CC BY 4.0 application against all third-party artifacts before publishing.",
            "Review the public repository history and the generated source archive before publishing.",
            "Create the release tag only after the final quality campaign and changelog review.",
        ],
    }


def _project_metadata(root: Path) -> dict[str, Any]:
    path = root / "pyproject.toml"
    if not path.is_file():
        return {}
    return dict(tomllib.loads(path.read_text(encoding="utf-8")).get("project", {}))


def _license_selected(root: Path, project: dict[str, Any]) -> bool:
    """Check the SPDX declaration and the corresponding license files."""
    license_metadata = project.get("license", {})
    if not (root / "LICENSE").is_file():
        return False
    if isinstance(license_metadata, str):
        license_files = project.get("license-files", [])
        return license_metadata == "Apache-2.0" and isinstance(license_files, list) and "LICENSE" in license_files
    if not isinstance(license_metadata, dict):
        return False
    declared_file = str(license_metadata.get("file", ""))
    declared_text = str(license_metadata.get("text", "")).strip()
    return declared_file == "LICENSE" or bool(declared_text and declared_text != "Proprietary")


def _check(identifier: str, passed: bool, detail: str) -> dict[str, str]:
    return {"id": identifier, "status": "PASS" if passed else "FAIL", "detail": detail}


def _git_clean_check(root: Path) -> dict[str, str]:
    completed = _git(root, "status", "--porcelain")
    if completed is None:
        return _check("git_clean_worktree", False, "Git metadata is unavailable; release provenance cannot be established.")
    return _check("git_clean_worktree", not completed.stdout.strip(), "The release source tree must have no uncommitted changes.")


def _git_tag_check(root: Path, version: str) -> dict[str, str]:
    if not version:
        return _check("version_tag", False, "Package version is missing.")
    completed = _git(root, "tag", "--points-at", "HEAD")
    if completed is None:
        return _check("version_tag", False, "Git metadata is unavailable; no immutable release tag can be verified.")
    expected = {version, f"v{version}"}
    if version.endswith("a0"):
        base_version = version[:-2]
        expected.update({f"{base_version}-alpha", f"v{base_version}-alpha"})
    return _check("version_tag", bool(expected & set(completed.stdout.split())), "HEAD must carry the package version tag.")


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    try:
        completed = subprocess.run(
            [git_command(), *args], cwd=root, text=True, capture_output=True, check=False, timeout=10
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return completed if completed.returncode == 0 else None


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("release_readiness.json"))
    args = parser.parse_args(argv)
    report = release_readiness(ROOT)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"RELEASE READINESS: {report['status']}")
    raw_checks = report["checks"]
    if isinstance(raw_checks, list):
        for check in raw_checks:
            if isinstance(check, dict):
                print(f"{str(check.get('status', 'FAIL')):>4}  {check.get('id', '')}: {check.get('detail', '')}")
    return 0 if report["status"] == "READY" else 4


if __name__ == "__main__":
    raise SystemExit(main())
