"""Run complex same-mesh orthotropic correlations with two external solvers."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.orthotropic_external import OrthotropicExternalCampaign


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("qualification/vnv/external/orthotropic_solids/reference"),
    )
    parser.add_argument("--mesh-size", type=float, default=0.30)
    arguments = parser.parse_args()
    summary = OrthotropicExternalCampaign(arguments.output, mesh_size=arguments.mesh_size).run()
    print(f"{summary['study_id']}: {summary['status']}")
    for row in summary["cases"]:
        print(
            f"  {row['case']}: {row['elements']} TET4, "
            f"CalculiX={100 * row['calculix_l2']:.6f} %, "
            f"Code_Aster={100 * row['code_aster_l2']:.6f} %"
        )
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
