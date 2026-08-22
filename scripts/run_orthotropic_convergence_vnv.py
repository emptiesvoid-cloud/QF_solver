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
    parser.add_argument(
        "--tet4-extra-sizes",
        type=float,
        nargs="+",
        default=None,
        help="Additional TET4 mesh sizes, in metres, appended to the baseline campaign.",
    )
    parser.add_argument(
        "--full-result-element-limit",
        type=int,
        default=12_000,
        help="Above this element count, write compact summary artifacts instead of full JSON results.",
    )
    parser.add_argument("--study-id", default=None)
    parser.add_argument(
        "--solver-method",
        choices=("direct", "cg", "large_cg"),
        default="direct",
        help="Linear solver used for the campaign; large_cg uses the vectorized TET4 path.",
    )
    arguments = parser.parse_args()
    campaign = OrthotropicStructuralConvergenceCampaign(arguments.output, solver_method=arguments.solver_method)
    campaign.full_result_element_limit = arguments.full_result_element_limit
    if arguments.tet4_extra_sizes is not None:
        campaign.tet4_extended_sizes = tuple(arguments.tet4_extra_sizes)
    if arguments.study_id:
        campaign.study_id = arguments.study_id
    summary = campaign.run()
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS_TECHNICAL_VERIFICATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
