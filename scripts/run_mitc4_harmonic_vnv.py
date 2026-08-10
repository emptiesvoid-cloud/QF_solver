"""Run the MITC4 harmonic modal verification study."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.mitc4_harmonic import write_mitc4_harmonic_evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate MITC4 harmonic V&V evidence.")
    parser.add_argument("--output", default="results/VNV-MITC4-HARMONIC-MODAL-001")
    args = parser.parse_args()
    summary = write_mitc4_harmonic_evidence(Path(args.output))
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS" else 4


if __name__ == "__main__":
    raise SystemExit(main())
