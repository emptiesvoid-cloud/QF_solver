"""Enforce branch-aware coverage on safety-critical P0 modules."""

from __future__ import annotations

import json
import sys
from pathlib import Path


MINIMUM = 90.0
P0_MODULES = (
    "solveur/core/errors.py",
    "solveur/verification/traceability.py",
)


def main(*paths: str) -> int:
    report_paths = paths or ("coverage.json",)
    files: dict[str, list[dict[str, object]]] = {}
    for path in report_paths:
        report = json.loads(Path(path).read_text(encoding="utf-8"))
        for name, data in report.get("files", {}).items():
            files.setdefault(name.replace("\\", "/"), []).append(data)
    failures: list[str] = []
    for module in P0_MODULES:
        records = [data for name, entries in files.items() if name.endswith(module) for data in entries]
        if not records:
            failures.append(f"{module}: absent from coverage report")
            continue
        percent = max(float(record["summary"]["percent_covered"]) for record in records)
        print(f"P0 COVERAGE {module}: {percent:.2f}%")
        if percent < MINIMUM:
            failures.append(f"{module}: {percent:.2f}% < {MINIMUM:.2f}%")
    if failures:
        print("P0 COVERAGE FAIL: " + "; ".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:]))
