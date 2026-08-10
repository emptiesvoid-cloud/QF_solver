"""Run the MITC4 Newmark free-vibration V&V study."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.mitc4_newmark import write_mitc4_newmark_evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate MITC4 Newmark V&V evidence.")
    parser.add_argument("--output", default="results/VNV-MITC4-NEWMARK-FREE-002")
    args = parser.parse_args()
    summary = write_mitc4_newmark_evidence(Path(args.output))
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS" else 4


if __name__ == "__main__":
    raise SystemExit(main())
