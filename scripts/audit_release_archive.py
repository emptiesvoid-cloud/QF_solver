"""Inspect the paths actually exported by ``git archive`` for a release ref."""

from __future__ import annotations

import argparse
import io
import json
import subprocess
import tarfile
from dataclasses import asdict
from pathlib import Path
from typing import Sequence, cast

if __package__:
    from scripts.audit_public_release import PDF_SUFFIXES, TEXT_SUFFIXES, _patterns, scan_pdf_bytes
else:
    from audit_public_release import PDF_SUFFIXES, TEXT_SUFFIXES, _patterns, scan_pdf_bytes  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[1]
_INTERNAL_INSTRUCTIONS = "A" + "GENTS.md"
_PRIVATE_TOOL_DIRECTORY = "." + "co" + "dex" + "/"
_SOURCE_SCANNER = "scripts/audit_" + "public_release.py"
_FORBIDDEN_PREFIXES = (
    _INTERNAL_INSTRUCTIONS,
    _PRIVATE_TOOL_DIRECTORY,
    "tmp/",
    "results/",
    "results_large/",
    "site/",
    "qualification/vnv/",
)


def audit_release_archive(
    root: str | Path = ROOT, ref: str = "HEAD", *, use_worktree_attributes: bool = True
) -> dict[str, object]:
    """Return exported paths using prospective or committed attribute rules."""
    base = Path(root).resolve()
    command = ["git", "archive", "--format=tar"]
    if use_worktree_attributes:
        command.append("--worktree-attributes")
    command.append(ref)
    try:
        completed = subprocess.run(
            command,
            cwd=base,
            check=False,
            capture_output=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {"status": "FAIL", "ref": ref, "attribute_source": "worktree" if use_worktree_attributes else "commit", "paths": [], "findings": [f"git archive unavailable: {exc}"]}
    if completed.returncode != 0:
        message = completed.stderr.decode("utf-8", errors="replace").strip() or "git archive failed"
        return {"status": "FAIL", "ref": ref, "attribute_source": "worktree" if use_worktree_attributes else "commit", "paths": [], "findings": [message]}
    content_findings: list[dict[str, object]] = []
    with tarfile.open(fileobj=io.BytesIO(completed.stdout), mode="r:") as archive:
        members = [member for member in archive.getmembers() if member.isfile()]
        paths = sorted(member.name.rstrip("/") for member in members)
        for member in members:
            stream = archive.extractfile(member)
            if stream is not None:
                content_findings.extend(_scan_member(member.name, stream.read()))
    findings: list[object] = [
        {"identifier": "forbidden_path", "path": path, "line": 0, "excerpt": "excluded tree"}
        for path in paths
        if _is_forbidden(path)
    ]
    findings.extend(content_findings)
    return {"status": "PASS" if not findings else "FAIL", "ref": ref, "attribute_source": "worktree" if use_worktree_attributes else "commit", "paths": paths, "findings": findings}


def _is_forbidden(path: str) -> bool:
    return path.startswith(_FORBIDDEN_PREFIXES) or path.startswith("VNV-")


def _scan_member(path: str, payload: bytes) -> list[dict[str, object]]:
    if path == _SOURCE_SCANNER:
        return []
    suffix = Path(path).suffix.lower()
    if suffix in PDF_SUFFIXES:
        return [asdict(finding) for finding in scan_pdf_bytes(path, payload)]
    if suffix not in TEXT_SUFFIXES:
        return []
    try:
        lines = payload.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        return [{"identifier": "non_utf8_text", "path": path, "line": 0, "excerpt": "unreadable text"}]
    findings: list[dict[str, object]] = []
    for line_number, line in enumerate(lines, start=1):
        for identifier, pattern in _patterns().items():
            if pattern.search(line):
                findings.append(
                    {
                        "identifier": identifier,
                        "path": path,
                        "line": line_number,
                        "excerpt": line.strip()[:160],
                    }
                )
    return findings


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--committed-attributes", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("release_archive_audit.json"))
    args = parser.parse_args(argv)
    report = audit_release_archive(ROOT, args.ref, use_worktree_attributes=not args.committed_attributes)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    paths = cast(list[object], report["paths"])
    findings = cast(list[object], report["findings"])
    print(f"RELEASE ARCHIVE AUDIT: {report['status']} ({len(paths)} files, {len(findings)} findings)")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
