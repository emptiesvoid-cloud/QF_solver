"""Run the multi-element cyclic TET4 J2 campaign."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from solveur.verification.j2_structural import J2StructuralCyclicCampaign  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate cyclic TET4 J2 V&V evidence.")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "results" / "VNV-J2-TET4-CYCLIC-003")
    args = parser.parse_args()
    summary = J2StructuralCyclicCampaign(args.output).run()
    print(f"J2 structural V&V: {summary['status']}")
    print(f"output: {args.output.resolve()}")
    return 0 if summary["status"] == "PASS_INTERNAL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
