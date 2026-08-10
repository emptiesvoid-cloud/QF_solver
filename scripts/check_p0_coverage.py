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


def main(path: str = "coverage.json") -> int:
    report = json.loads(Path(path).read_text(encoding="utf-8"))
    files = {name.replace("\\", "/"): data for name, data in report.get("files", {}).items()}
    failures: list[str] = []
    for module in P0_MODULES:
        record = next((data for name, data in files.items() if name.endswith(module)), None)
        if record is None:
            failures.append(f"{module}: absent from coverage report")
            continue
        percent = float(record["summary"]["percent_covered"])
        print(f"P0 COVERAGE {module}: {percent:.2f}%")
        if percent < MINIMUM:
            failures.append(f"{module}: {percent:.2f}% < {MINIMUM:.2f}%")
    if failures:
        print("P0 COVERAGE FAIL: " + "; ".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "coverage.json"))
