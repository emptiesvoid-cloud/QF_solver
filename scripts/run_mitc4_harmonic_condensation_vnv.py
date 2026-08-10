"""Run the controlled MITC4 harmonic-condensation proof."""

from __future__ import annotations

import argparse

from solveur.verification.mitc4_harmonic_condensation import (
    STUDY_ID,
    write_mitc4_harmonic_condensation_evidence,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=f"results/{STUDY_ID}")
    args = parser.parse_args()
    summary = write_mitc4_harmonic_condensation_evidence(args.output)
    print(f"{STUDY_ID}: {summary['status']}")
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
