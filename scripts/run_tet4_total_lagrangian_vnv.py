"""Generate total-Lagrangian TET4 kernel review evidence."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
for candidate in (SOURCE_ROOT, PROJECT_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from solveur.verification.tet4_total_lagrangian import TotalLagrangianTet4Campaign  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate finite-kinematics TET4 kernel evidence.")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "results" / "VNV-TET4-TL-KERNEL-001")
    args = parser.parse_args()
    summary = TotalLagrangianTet4Campaign(args.output).run()
    print(f"TET4 total-Lagrangian kernel: {summary['status']}")
    print(f"output: {args.output.resolve()}")
    return 0 if summary["status"] == "PASS_KERNEL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
