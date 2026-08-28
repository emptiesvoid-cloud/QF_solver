"""Capture a static architecture inventory for the 0.2.6 refactor guard."""

from __future__ import annotations

import argparse
import ast
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "qualification" / "0_2_6" / "architecture_audit.json")
    arguments = parser.parse_args()
    report = audit(ROOT)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown_report(report)
    print(f"architecture audit: {arguments.output}")
    return 0


def _write_markdown_report(report: dict[str, Any]) -> None:
    """Provide a reader-facing companion without making the JSON non-authoritative."""

    target = ROOT / "docs" / "verification" / "0_2_6" / "0_2_6_architecture_audit.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    oversized = report["oversized_modules"]
    large = report["large_tracked_files"][:10]
    lines = [
        "# Architecture Audit",
        "",
        "The machine-readable authority is `qualification/0_2_6/architecture_audit.json`.",
        "This audit is descriptive; no numerical module is moved by the foundation run.",
        "",
        f"- Source SHA captured: `{report['source_sha']}`",
        f"- Source dirty at capture: `{report['source_dirty']}`",
        f"- Python modules inspected: {report['python_module_count']}",
        f"- Flat verification modules: {report['verification_flat_module_count']}",
        "",
        "## Large Modules",
        "",
        "| Module | Lines | Audit threshold |",
        "| --- | ---: | --- |",
        *[f"| `{row['path']}` | {row['lines']} | {row['threshold']} |" for row in oversized],
        "",
        "## Large Historical Artifacts",
        "",
        "These are retained for provenance. The 0.2.6 policy prevents new equivalents from entering normal source history.",
        "",
        "| Artifact | Bytes |",
        "| --- | ---: |",
        *[f"| `{row['path']}` | {row['bytes']} |" for row in large],
        "",
        "## Findings",
        "",
        *[f"- {finding}" for finding in report["findings"]],
        "",
    ]
    target.write_text("\n".join(lines), encoding="utf-8")


def audit(root: Path) -> dict[str, Any]:
    python_files = sorted((root / "src").rglob("*.py"))
    by_directory = Counter(path.parent.relative_to(root).as_posix() for path in python_files)
    oversized = []
    dependencies: dict[str, set[str]] = defaultdict(set)
    for path in python_files:
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        if line_count > 500:
            oversized.append({"path": path.relative_to(root).as_posix(), "lines": line_count, "threshold": "over_500" if line_count < 700 else "at_or_over_700"})
        module = _domain(path, root)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
            elif isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            for name in names:
                if name.startswith("solveur."):
                    target = name.split(".")[1]
                    if target != module:
                        dependencies[module].add(target)
    tracked_large = _large_tracked_files(root)
    verification_files = sorted((root / "src" / "solveur" / "verification").glob("*.py"))
    return {
        "schema_version": 1,
        "captured_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_sha": _git(root, "rev-parse", "HEAD"),
        "source_dirty": bool(_git(root, "status", "--porcelain")),
        "python_module_count": len(python_files),
        "modules_by_directory": dict(sorted(by_directory.items())),
        "oversized_modules": sorted(oversized, key=lambda row: row["lines"], reverse=True),
        "verification_flat_module_count": len(verification_files),
        "dependency_domains": {domain: sorted(targets) for domain, targets in sorted(dependencies.items())},
        "detected_two_way_domain_dependencies": _two_way(dependencies),
        "large_tracked_files": tracked_large,
        "findings": [
            "Verification contains many flat, solver-specific modules and duplicated campaign entrypoints.",
            "No mechanical migration is performed by this audit; the framework package is an additive boundary.",
            "Historical large benchmark displacement blobs exceed the proposed normal artifact size policy and must be preserved, not rewritten.",
        ],
    }


def _domain(path: Path, root: Path) -> str:
    relative = path.relative_to(root / "src")
    if relative.parts[0] != "solveur":
        return relative.parts[0]
    parts = relative.parts[1:]
    return parts[0] if parts else "root"


def _two_way(edges: dict[str, set[str]]) -> list[list[str]]:
    pairs = []
    for source, targets in edges.items():
        for target in targets:
            if source in edges.get(target, set()) and [target, source] not in pairs:
                pairs.append([source, target])
    return sorted(pairs)


def _large_tracked_files(root: Path) -> list[dict[str, Any]]:
    files = subprocess.run(["git", "-C", str(root), "ls-files"], check=True, capture_output=True, text=True).stdout.splitlines()
    rows = []
    for name in files:
        path = root / name
        if path.is_file() and path.stat().st_size > 1_000_000:
            rows.append({"path": name.replace("\\", "/"), "bytes": path.stat().st_size})
    return sorted(rows, key=lambda row: row["bytes"], reverse=True)[:40]


def _git(root: Path, *arguments: str) -> str | None:
    try:
        return subprocess.run(["git", "-C", str(root), *arguments], check=True, capture_output=True, text=True).stdout.strip()
    except subprocess.CalledProcessError:
        return None


if __name__ == "__main__":
    raise SystemExit(main())
