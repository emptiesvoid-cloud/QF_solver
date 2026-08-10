"""Run the MITC4 simply-supported square-plate modal V&V study."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.mitc4_modal_plate import write_mitc4_modal_plate_evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate MITC4 plate modal V&V evidence.")
    parser.add_argument("--output", default="results/VNV-MITC4-MODAL-PLATE-003")
    args = parser.parse_args()
    summary = write_mitc4_modal_plate_evidence(Path(args.output))
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS" else 4


if __name__ == "__main__":
    raise SystemExit(main())
