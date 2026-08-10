"""Run isotropic-path numerical and performance non-regression."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.orthotropic_performance import OrthotropicIsotropicPerformanceCampaign


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("qualification/vnv/orthotropic_isotropic_performance/reference"),
    )
    arguments = parser.parse_args()
    summary = OrthotropicIsotropicPerformanceCampaign(arguments.output).run()
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS_NON_REGRESSION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
