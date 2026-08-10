"""Run the imperfect-column TET4 postbuckling benchmark."""

from __future__ import annotations

from pathlib import Path

from solveur.verification.tet4_total_lagrangian_postbuckling import (
    TotalLagrangianPostbucklingCampaign,
)


def main() -> int:
    buckling = Path("results/VNV-TET4-TL-BUCKLING-EULER-006/summary.json")
    output = Path("results/VNV-TET4-TL-POSTBUCKLING-007")
    summary = TotalLagrangianPostbucklingCampaign(output, buckling).run()
    print(f"{summary['study_id']}: {summary['status']} -> {output.resolve()}")
    return 0 if str(summary["status"]).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
