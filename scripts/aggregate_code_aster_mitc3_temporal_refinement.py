"""Aggregate completed Code_Aster MITC3+ temporal probes."""

from __future__ import annotations

import argparse

from solveur.verification.code_aster_mitc3_temporal_refinement import (
    CodeAsterMitc3TemporalRefinementStudy,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("sources", nargs=3, help="three completed probe directories")
    args = parser.parse_args()
    summary = CodeAsterMitc3TemporalRefinementStudy(tuple(args.sources), args.output).run()
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS_DIAGNOSTIC" else 1


if __name__ == "__main__":
    raise SystemExit(main())
