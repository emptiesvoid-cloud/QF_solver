"""Run damped and forced MITC4 Newmark verification."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.mitc4_newmark_extended import write_mitc4_newmark_extended_evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate extended MITC4 Newmark V&V evidence.")
    parser.add_argument("--output", default="results/VNV-MITC4-NEWMARK-DAMPED-FORCED-003")
    args = parser.parse_args()
    summary = write_mitc4_newmark_extended_evidence(Path(args.output))
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS" else 4


if __name__ == "__main__":
    raise SystemExit(main())
