"""Audit source candidates for data that must not enter a public release."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence, cast


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ROOTS = (
    "LICENSE",
    "LICENSE-DOCS",
    "NOTICE",
    "THIRD_PARTY_LICENSES.md",
    ".gitattributes",
    ".gitignore",
    "README.md",
    "CHANGELOG.md",
    "CITATION.cff",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "DEVELOPER_GUIDE.md",
    "OPEN_SOURCE_READINESS.md",
    "PUBLIC_RELEASE_POLICY.md",
    "SECURITY.md",
    "SUPPORT.md",
    "pyproject.toml",
    "mkdocs.yml",
    "qf_solver.py",
    "main_solveur.py",
    "mitc4_solver.py",
    "src",
    "scripts",
    "requirements",
    "tools",
    "docs",
    "examples",
    "qualification",
    "tests",
    ".github",
)
EXCLUDED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "results",
    "results_large",
    "site",
    "tmp",
    "generated",
}
PRIVATE_RELATIVE_PREFIXES = ("qualification/vnv/",)
TEXT_SUFFIXES = {
    ".cff", ".cfg", ".csv", ".htm", ".html", ".ini", ".json", ".md",
    ".ps1", ".py", ".rst", ".sh", ".tex", ".toml", ".txt", ".xml",
    ".yaml", ".yml",
}
PDF_SUFFIXES = {".pdf"}


@dataclass(frozen=True)
class PublicReleaseFinding:
    """One forbidden public-release marker with only a repository-relative path."""

    identifier: str
    path: str
    line: int
    excerpt: str


def _patterns() -> dict[str, re.Pattern[str]]:
    assistant_product = "co" + "dex"
    conversational_product = "chat" + "gpt"
    ai_provider = "open" + "ai"
    internal_worker = "a" + "gent"
    private_environment = "." + assistant_product
    legacy_brand = "saf" + "ran"
    return {
        "workstation_path": re.compile(r"(?i)(?:[a-z]:[\\/]+users[\\/]+|\\\\users\\\\|/(?:home|users)/)"),
        "private_environment": re.compile(rf"(?i)(?:appdata|{re.escape(private_environment)})"),
        "internal_workflow": re.compile(
            rf"(?i)\b(?:{assistant_product}|{conversational_product}|{ai_provider}|"
            rf"{internal_worker}ique|mode {internal_worker}|coding {internal_worker})\b"
        ),
        "legacy_brand": re.compile(rf"(?i)\b{legacy_brand}\b"),
        "private_email": re.compile(
            r"(?i)\b(?![^@\s]*@users\.noreply\.github\.com\b)"
            r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b"
        ),
        "credential": re.compile(
            r"(?i)(?:github_pat_[a-z0-9_]+|ghp_[a-z0-9]{20,}|"
            r"sk-[a-z0-9_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)"
        ),
    }


def public_source_files(root: str | Path = ROOT) -> Iterable[Path]:
    """Yield release candidates while excluding generated and local artifact trees."""
    base = Path(root).resolve()
    for relative in PUBLIC_ROOTS:
        candidate = base / relative
        if candidate.is_file():
            yield candidate
        elif candidate.is_dir():
            for path in candidate.rglob("*"):
                relative_parts = path.relative_to(base).parts
                relative_name = path.relative_to(base).as_posix()
                if (
                    path.is_file()
                    and path.suffix.lower() in TEXT_SUFFIXES | PDF_SUFFIXES
                    and not (set(relative_parts) & EXCLUDED_PARTS)
                    and not relative_name.startswith(PRIVATE_RELATIVE_PREFIXES)
                ):
                    if path.name != Path(__file__).name:
                        yield path


def audit_public_release(root: str | Path = ROOT) -> dict[str, object]:
    """Return a deterministic, path-safe audit report for public release candidates."""
    base = Path(root).resolve()
    findings: list[PublicReleaseFinding] = []
    files = sorted(set(public_source_files(base)))
    patterns = _patterns()
    for path in files:
        relative = path.relative_to(base).as_posix()
        if path.suffix.lower() in PDF_SUFFIXES:
            findings.extend(scan_pdf_bytes(relative, path.read_bytes()))
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            findings.append(PublicReleaseFinding("non_utf8_text", relative, 0, "unreadable text"))
            continue
        for line_number, line in enumerate(lines, start=1):
            for identifier, pattern in patterns.items():
                if pattern.search(line):
                    findings.append(
                        PublicReleaseFinding(
                            identifier, relative, line_number, line.strip()[:160]
                        )
                    )
    return {
        "status": "PASS" if not findings else "FAIL",
        "scanned_files": len(files),
        "findings": [asdict(finding) for finding in findings],
    }


def scan_pdf_bytes(relative: str, payload: bytes) -> list[PublicReleaseFinding]:
    """Detect private paths and internal links stored in PDF objects."""
    lowered = payload.lower()
    findings: list[PublicReleaseFinding] = []
    markers = {
        "workstation_path": (
            b"c:/users/",
            b"c:\\users\\",
            b"/home/",
            b"file\\072\\057\\057\\057c\\072\\057users\\057",
        ),
        "legacy_brand": (b"saf" + b"ran",),
    }
    for identifier, values in markers.items():
        if any(value in lowered for value in values):
            findings.append(
                PublicReleaseFinding(identifier, relative, 0, "forbidden marker in PDF object")
            )
    if b"/uri (file:" in lowered or b"/uri(file:" in lowered:
        findings.append(
            PublicReleaseFinding("local_file_uri", relative, 0, "local file URI in PDF annotation")
        )
    return findings


def main(argv: Sequence[str] | None = None) -> int:
    """Run the audit and emit portable JSON without exposing the workstation root."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("public_release_audit.json"))
    args = parser.parse_args(argv)
    report = audit_public_release(ROOT)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    findings = cast(list[object], report["findings"])
    print(
        f"PUBLIC RELEASE AUDIT: {report['status']} ({report['scanned_files']} files, {len(findings)} findings)"
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
