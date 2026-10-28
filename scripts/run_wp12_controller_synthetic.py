"""Run the WP12 controller's synthetic contracts one exact pytest node at a time."""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_TEST_FILES = (
    Path("tests/unit/test_development_autonomous_policy.py"),
    Path("tests/unit/test_wp12_observable_archive_synthetic.py"),
    Path("tests/unit/test_wp12b_diagnostic_provenance.py"),
    Path("tests/unit/test_wp12b_hex20_diagnostic_support.py"),
    Path("tests/unit/test_wp12b_owner_decision_contract.py"),
)
SUMMARY_RE = re.compile(r"\b(\d+)\s+(passed|failed|skipped|error|errors)\b")


def _test_nodeids(path: Path) -> list[str]:
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"), filename=str(path))
    nodeids: list[str] = []

    def visit(node: ast.Module | ast.ClassDef, classes: tuple[str, ...] = ()) -> None:
        for child in node.body:
            if isinstance(child, ast.ClassDef):
                visit(child, (*classes, child.name))
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.startswith("test_"):
                nodeids.append("::".join((path.as_posix(), *classes, child.name)))

    visit(tree)
    return nodeids


def main() -> int:
    totals = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0}
    failures: list[tuple[str, str]] = []
    for path in SYNTHETIC_TEST_FILES:
        for nodeid in _test_nodeids(path):
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "--tb=short", nodeid],
                cwd=ROOT,
                capture_output=True,
                check=False,
                text=True,
            )
            output = result.stdout + result.stderr
            for count, status in SUMMARY_RE.findall(output):
                key = "errors" if status in {"error", "errors"} else status
                totals[key] += int(count)
            if result.returncode:
                failures.append((nodeid, output))
    print(
        "WP12 synthetic controller suite: "
        f"{totals['passed']} passed, {totals['failed']} failed, "
        f"{totals['skipped']} skipped, {totals['errors']} errors"
    )
    for nodeid, output in failures:
        print(f"\nFAIL: {nodeid}\n{output}")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
