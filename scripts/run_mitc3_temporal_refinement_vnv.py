"""Run the controlled MITC3+ Newmark temporal refinement campaign."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.mitc3_temporal_refinement import (
    DEFAULT_STEPS_PER_PERIOD,
    write_mitc3_temporal_refinement_evidence,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="qualification/vnv/mitc3_laminate_temporal_refinement_2026-08-21",
        help="output directory for the evidence bundle",
    )
    parser.add_argument("--steps", nargs="+", type=int, default=list(DEFAULT_STEPS_PER_PERIOD))
    args = parser.parse_args()
    if tuple(sorted(args.steps)) != tuple(args.steps) or len(args.steps) < 3:
        parser.error("--steps must contain at least three increasing values")
    summary = write_mitc3_temporal_refinement_evidence(Path(args.output))
    print(f"{summary['study_id']}: {summary['status']}")
    for point in summary["time_levels"]:
        print(f"  {point['steps_per_period']} steps/period: RMS={point['normalized_rms_error']:.6e}")
    return 0 if summary["status"] == "PASS_INTERNAL" else 1


if __name__ == "__main__":
    raise SystemExit(main())

