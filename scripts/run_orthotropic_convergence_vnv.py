"""Run the off-axis TET4/TET10 structural convergence campaign."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.orthotropic_convergence import OrthotropicStructuralConvergenceCampaign


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("qualification/vnv/orthotropic_solid_convergence/reference"),
    )
    arguments = parser.parse_args()
    summary = OrthotropicStructuralConvergenceCampaign(arguments.output).run()
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS_TECHNICAL_VERIFICATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
