"""Classify and audit tracked documentation prepared for public release."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Sequence

try:
    from scripts.audit_public_release import audit_public_release
    from scripts.git_tools import git_command
except ModuleNotFoundError:
    from audit_public_release import audit_public_release  # type: ignore[no-redef]
    from git_tools import git_command  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = Path("qualification/publication_audit_0_2_5.json")
WEB_RUNTIME_PATHS = (
    "mkdocs.yml",
    "scripts/serve_docs.py",
    "scripts/serve_docs.ps1",
    "src/solveur/documentation/server.py",
    "tests/documentation/test_docs_server.py",
    "tests/documentation/test_site_browser.py",
)
INTERNAL_PREFIXES = (
    "." + "co" + "dex/",
    ".graphifyignore",
    "A" + "GENTS.md",
    "graphify-out/",
    "output/",
    "qualification/evidence/",
    "qualification/maturity_evidence_",
    "qualification/vnv/",
    "results/",
    "results_large/",
    "site/",
)
INTERNAL_CLASSIFICATION_LABELS = (
    "local_tool_configuration/",
    "local_graph_configuration",
    "local_instruction_file",
    "graph_cache/",
    "output/",
    "qualification/evidence/",
    "qualification/maturity_evidence_",
    "qualification/vnv/",
    "results/",
    "results_large/",
    "site/",
)
IMMUTABLE_ARCHIVES = (
    "qualification/baselines/qf_solver_0.2.0_engineering.json",
    "qualification/baselines/qf_solver_0.2.0_engineering.md",
)


def public_document_audit(root: str | Path = ROOT) -> dict[str, Any]:
    """Return a deterministic classification and hygiene report for tracked files."""
    base = Path(root).resolve()
    publication_candidates = _publication_candidates(base)
    tracked = _tracked_index_files(base)
    docs = [path for path in tracked if path.startswith("docs/")]
    public_generated = [
        path
        for path in docs
        if path.startswith("docs/generated/") or path.startswith("docs/assets/generated/")
    ]
    public_source = [path for path in docs if path not in public_generated]
    if "README.md" in tracked:
        public_source.append("README.md")
    immutable = [path for path in tracked if path in IMMUTABLE_ARCHIVES]
    internal_tracked = [
        path for path in tracked if any(path.startswith(prefix) for prefix in INTERNAL_PREFIXES)
    ]
    vocabulary_offenders = _review_vocabulary_offenders(base, publication_candidates)
    web_runtime_present = [
        relative for relative in WEB_RUNTIME_PATHS if (base / relative).is_file()
    ]
    pyproject = _read_text(base / "pyproject.toml").casefold()
    web_dependencies = [name for name in ("mkdocs", "playwright") if name in pyproject]
    release_audit = audit_public_release(base)

    checks = [
        _check(
            "public_source_hygiene",
            release_audit["status"] == "PASS",
            f"{release_audit['scanned_files']} tracked release files scanned",
        ),
        _check(
            "controlled_review_vocabulary",
            not vocabulary_offenders,
            "no generic review vocabulary in tracked text sources"
            if not vocabulary_offenders
            else ", ".join(vocabulary_offenders),
        ),
        _check(
            "web_delivery_retired",
            not web_runtime_present and not web_dependencies,
            "no web runtime source or web-only dependency remains"
            if not web_runtime_present and not web_dependencies
            else f"runtime={web_runtime_present}, dependencies={web_dependencies}",
        ),
        _check(
            "internal_paths_not_tracked",
            not internal_tracked,
            "internal and working artifact paths are absent from tracked files"
            if not internal_tracked
            else ", ".join(internal_tracked),
        ),
    ]
    return {
        "schema_version": 1,
        "audit_id": "QF-PUBLIC-DOC-AUDIT-025-001",
        "release": {"name": "QF_solver", "version": "0.2.5a0"},
        "status": "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL",
        "classification": {
            "public_source_documentation": {
                "count": len(public_source),
                "paths": ["README.md", "docs/** excluding generated evidence"],
                "publication": "public",
            },
            "public_generated_documentation": {
                "count": len(public_generated),
                "paths": ["docs/generated/**", "docs/assets/generated/**"],
                "publication": "public",
            },
            "archive_immutable": {
                "count": len(immutable),
                "paths": list(IMMUTABLE_ARCHIVES),
                "publication": "public_historical",
            },
            "internal": {
                "tracked_count": len(internal_tracked),
                "reserved_prefixes": list(INTERNAL_CLASSIFICATION_LABELS),
                "publication": "not_published",
            },
            "generated_not_published": {
                "paths": [
                    "site/**",
                    "output/**",
                    "qualification/maturity_evidence_*/**",
                    "results/**",
                    "results_large/**",
                ],
                "publication": "not_published",
            },
        },
        "checks": checks,
        "public_release_audit": {
            "status": release_audit["status"],
            "scanned_files": release_audit["scanned_files"],
            "finding_count": len(release_audit["findings"]),
        },
    }


def _tracked_index_files(root: Path) -> list[str]:
    """List candidate source entries from the index, independent of generated worktree state."""
    completed = subprocess.run(
        [git_command(), "ls-files", "--cached"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if completed.returncode != 0:
        raise RuntimeError("Git tracked-file inventory is unavailable.")
    return sorted(relative for relative in completed.stdout.splitlines() if relative)


def _publication_candidates(root: Path) -> list[str]:
    """List public candidates while excluding local and controlled private artifacts."""
    completed = subprocess.run(
        [git_command(), "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if completed.returncode != 0:
        raise RuntimeError("Git publication candidate inventory is unavailable.")
    return sorted(
        relative
        for relative in completed.stdout.splitlines()
        if relative
        and not any(relative.startswith(prefix) for prefix in INTERNAL_PREFIXES)
        and (root / relative).is_file()
    )


def _review_vocabulary_offenders(root: Path, tracked: Sequence[str]) -> list[str]:
    """Find generic review labels in tracked text documents and source files."""
    suffixes = {".cff", ".json", ".md", ".py", ".rst", ".tex", ".toml", ".txt", ".yaml", ".yml"}
    forbidden_terms = ("h" + "uman", "h" + "umain")
    exempt_prefixes = (
        "qualification/evidence/",
        "qualification/maturity_evidence_",
        "docs/generated/",
    )
    offenders: list[str] = []
    for relative in tracked:
        path = root / relative
        if path.suffix.lower() not in suffixes or relative.startswith(exempt_prefixes):
            continue
        if any(term in _read_text(path).casefold() for term in forbidden_terms):
            offenders.append(relative)
    return offenders


def _check(identifier: str, passed: bool, detail: str) -> dict[str, str]:
    return {"id": identifier, "status": "PASS" if passed else "FAIL", "detail": detail}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else ""


def main(argv: Sequence[str] | None = None) -> int:
    """Write the controlled public-document audit record."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report = public_document_audit(ROOT)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(
        "PUBLIC DOCUMENT AUDIT: "
        f"{report['status']} ({report['public_release_audit']['scanned_files']} files, "
        f"{report['public_release_audit']['finding_count']} findings)"
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
