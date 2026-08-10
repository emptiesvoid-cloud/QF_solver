"""Run the MITC3+ engineering V&V campaign."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.mitc3_campaign import Mitc3ValidationCampaign


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results") / "VNV-MITC3-PLUS-V1",
    )
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    summary = Mitc3ValidationCampaign(args.output, quick=args.quick).run()
    print(f"MITC3+ V&V: {summary['status']}")
    print(f"evidence: {args.output.resolve()}")
    return 1 if summary["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
