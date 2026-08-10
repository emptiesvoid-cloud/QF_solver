"""Generate the controlled wideband MITC4/Newmark V&V evidence."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.mitc4_newmark_broadband import (
    write_mitc4_newmark_broadband_evidence,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/VNV-MITC4-NEWMARK-BROADBAND-004"),
    )
    args = parser.parse_args()
    summary = write_mitc4_newmark_broadband_evidence(args.output)
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
