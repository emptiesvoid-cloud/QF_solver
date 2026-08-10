"""Run TET4 total-Lagrangian load-increment sensitivity."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.verification.tet4_total_lagrangian_steps import TotalLagrangianStepSensitivity


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/VNV-TET4-TL-STEPS-004"))
    args = parser.parse_args()
    summary = TotalLagrangianStepSensitivity(args.output).run()
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if summary["status"] == "PASS_STEP_SENSITIVITY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
