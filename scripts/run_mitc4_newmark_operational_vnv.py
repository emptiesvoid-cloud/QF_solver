"""Run the MITC4 Newmark operational load, damping and restart V&V study."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from solveur.verification.mitc4_newmark_operational import (
    STUDY_ID,
    write_mitc4_newmark_operational_evidence,
)


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results" / STUDY_ID,
    )
    args = parser.parse_args()
    output = args.output.resolve()
    summary = write_mitc4_newmark_operational_evidence(output)
    assets = ROOT / "docs" / "assets" / "reviews"
    assets.mkdir(parents=True, exist_ok=True)
    shutil.copy2(output / f"{STUDY_ID}.png", assets / "mitc4_newmark_operational.png")
    print(f"{STUDY_ID}: {summary['status']}")
    return 0 if summary["status"] == "PASS" else 4


if __name__ == "__main__":
    raise SystemExit(main())
