"""Run the MITC3+ laminate internal static and dynamic V&V campaign."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from solveur.verification.mitc3_laminate_dynamic import STUDY_ID, write_mitc3_laminate_dynamic_evidence  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate MITC3+ laminate internal V&V evidence.")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "results" / STUDY_ID)
    args = parser.parse_args()
    summary = write_mitc3_laminate_dynamic_evidence(args.output)
    print(f"MITC3 laminate V&V: {summary['status']}")
    print(f"output: {args.output.resolve()}")
    return 0 if summary["status"] == "PASS_INTERNAL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
