"""Run the cyclic J2 load-increment sensitivity campaign."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
for candidate in (SOURCE_ROOT, PROJECT_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from solveur.verification.j2_step_sensitivity import J2StepSensitivityCampaign  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify cyclic J2 load-increment sensitivity.")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "results" / "VNV-J2-STEP-SENSITIVITY-005")
    args = parser.parse_args()
    summary = J2StepSensitivityCampaign(args.output).run()
    print(f"J2 step sensitivity: {summary['status']}")
    print(f"output: {args.output.resolve()}")
    return 0 if summary["status"] == "PASS_INTERNAL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
