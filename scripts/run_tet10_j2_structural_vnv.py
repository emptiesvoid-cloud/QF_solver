"""Run the committed-state TET10 J2 structural verification campaign."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
for candidate in (SOURCE_ROOT, PROJECT_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from solveur.verification.j2_structural import J2StructuralCyclicCampaign  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate committed-state TET10 J2 V&V evidence.")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "results" / "VNV-J2-TET10-CYCLIC-001",
    )
    args = parser.parse_args()
    summary = J2StructuralCyclicCampaign(args.output, element_type="TET10").run()
    print(f"TET10 J2 structural V&V: {summary['status']}")
    print(f"output: {args.output.resolve()}")
    return 0 if summary["status"] == "PASS_INTERNAL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
