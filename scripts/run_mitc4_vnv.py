"""Run the controlled MITC4 V&V evidence campaign."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from solveur.verification.mitc4_campaign import Mitc4ValidationCampaign  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate MITC4 static, modal and Newmark V&V evidence.")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "results" / "VNV-MITC4-LINEAR-V1")
    parser.add_argument("--quick", action="store_true", help="run a reduced locking matrix")
    args = parser.parse_args()
    summary = Mitc4ValidationCampaign(args.output, quick=args.quick).run()
    print(f"MITC4 V&V: {summary['status']}")
    print(f"output: {args.output.resolve()}")
    return 0 if summary["status"] in {"PASS_INTERNAL", "PASS_INTERNAL_WITH_WARNING"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
