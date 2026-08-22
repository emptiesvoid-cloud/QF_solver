"""Run the independent multi-DOF discrete verification campaign."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from solveur.verification.discrete_multidof_campaign import write_discrete_multidof_campaign


ROOT = Path(__file__).resolve().parents[1]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "qualification/vnv/discrete_multidof_2026-08-21")
    args = parser.parse_args(argv)
    report = write_discrete_multidof_campaign(args.output)
    print(f"DISCRETE MULTIDOF CAMPAIGN: {report['status']} ({args.output})")
    return 0 if report["status"] == "PASS_TECHNICAL_VERIFICATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
