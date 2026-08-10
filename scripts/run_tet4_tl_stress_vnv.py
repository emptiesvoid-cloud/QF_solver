"""Run the finite-strain TET4 stress and energy benchmark."""

from __future__ import annotations

from pathlib import Path

from solveur.verification.tet4_total_lagrangian_stress import TotalLagrangianStressCampaign


def main() -> int:
    output = Path("results/VNV-TET4-TL-STRESS-005")
    summary = TotalLagrangianStressCampaign(output).run()
    print(f"{summary['study_id']}: {summary['status']} -> {output.resolve()}")
    return 0 if str(summary["status"]).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
