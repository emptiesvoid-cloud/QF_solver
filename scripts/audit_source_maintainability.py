"""Report source-size debt without treating file length as a behavior gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
SOURCE_LINE_TARGET = 700
SOURCE_ROOTS = ("src/solveur", "scripts", "tests")
# Historical reference counts, not limits or exclusions from the inventory.
HISTORICAL_LINE_REFERENCES = {
    "scripts/run_wp13_01c_final_runtime.py": 1512,
    "scripts/wp13_02b9_harness.py": 1003,
    "scripts/run_wp13_07_contact_bounded.py": 886,
    "scripts/run_wp13_02c_harmonic_mixed.py": 830,
    "scripts/run_wp13_03b_v2_mpc_rbe2.py": 801,
    "scripts/run_wp13_02c2_harmonic_harness.py": 789,
    "scripts/wp13_02b12_contract_compliance.py": 754,
    "src/solveur/large/generic_distributed.py": 1160,
    "src/solveur/core/analyses/dynamic.py": 723,
}


class SourceSizeAdvisoryWarning(UserWarning):
    """A maintenance objective is exceeded; numerical gates are unaffected."""


def audit_source_maintainability(
    root: str | Path = ROOT, *, target: int = SOURCE_LINE_TARGET,
) -> dict[str, Any]:
    """Inventory all Python sources, including every historical oversized file.

    There is no maximum accepted length. Unreadable files and absent source
    roots still fail closed. Syntax, dependency and behavior gates are separate.
    """
    if isinstance(target, bool) or not isinstance(target, int) or target < 1:
        raise ValueError("The advisory line target must be a positive integer.")
    base = Path(root).resolve()
    findings: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    scanned = 0
    for relative_root in SOURCE_ROOTS:
        source_root = base / relative_root
        if not source_root.is_dir():
            errors.append({"path": relative_root, "reason": "MISSING_SOURCE_ROOT"})
            continue
        for path in sorted(source_root.rglob("*.py")):
            relative = path.relative_to(base).as_posix()
            try:
                with path.open(encoding="utf-8") as stream:
                    line_count = sum(1 for _ in stream)
            except (OSError, UnicodeError) as exc:
                errors.append({"path": relative, "reason": type(exc).__name__})
                continue
            scanned += 1
            if line_count > target:
                reference = HISTORICAL_LINE_REFERENCES.get(relative)
                findings.append({
                    "path": relative,
                    "lines": line_count,
                    "target": target,
                    "excess_lines": line_count - target,
                    "classification": "MAINTENANCE_DEBT_NON_BLOCKING",
                    "historical_reference_lines": reference,
                    "growth_from_historical_reference": (
                        line_count - reference if reference is not None else None
                    ),
                })
    findings.sort(key=lambda item: (-item["lines"], item["path"]))
    status = "FAIL_CLOSED" if errors else ("PASS_WITH_MAINTENANCE_DEBT" if findings else "PASS")
    return {
        "schema_version": 1,
        "status": status,
        "policy": "ADVISORY_SIZE_OBJECTIVE_NO_HARD_CAP",
        "line_target": target,
        "scanned_files": scanned,
        "oversized_files": len(findings),
        "findings": findings,
        "errors": errors,
        "numerical_thresholds_changed": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--target", type=int, default=SOURCE_LINE_TARGET)
    args = parser.parse_args(argv)
    report = audit_source_maintainability(args.root, target=args.target)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
