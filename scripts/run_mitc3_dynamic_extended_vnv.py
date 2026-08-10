"""Run the extended MITC3+ modal, Newmark and harmonic V&V campaign."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from solveur.verification.mitc3_dynamic_extended import (  # noqa: E402
    CAMPAIGN_ID,
    write_mitc3_dynamic_extended_evidence,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate extended MITC3+ linear-dynamics V&V evidence.")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "results" / CAMPAIGN_ID)
    args = parser.parse_args()
    summary = write_mitc3_dynamic_extended_evidence(args.output)
    print(f"MITC3 extended dynamics V&V: {summary['status']}")
    print(f"output: {args.output.resolve()}")
    return 0 if summary["status"] == "PASS_INTERNAL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
