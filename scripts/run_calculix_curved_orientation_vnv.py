"""Run and publish the intrinsic curved-orientation CalculiX correlation."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from solveur.verification.calculix_curved_orientation import (
    CalculixCurvedOrientationCorrelation,
)
from solveur.verification.vnv_manifest import write_vnv_manifest


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/VNV-COMP-CURVED-ORIENTATION-008"),
    )
    parser.add_argument("--image", default="qf-solver/calculix-nafems13h:2.20")
    args = parser.parse_args()
    output = args.output.resolve()
    campaign = CalculixCurvedOrientationCorrelation(output, image=args.image)
    summary = campaign.run()
    _publish(output)
    print(f"{summary['study_id']}: {summary['status']} -> {output}")
    return 0 if str(summary["status"]).startswith("PASS") else 1


def _publish(output: Path) -> None:
    reference = (
        ROOT
        / "qualification"
        / "vnv"
        / "external"
        / "calculix_curved_orientation"
        / "reference"
    )
    reference.mkdir(parents=True, exist_ok=True)
    names = (
        "summary.json",
        "report.md",
        "curved_orientation_correlation.png",
        "curved_orientation_deformation.png",
    )
    for name in names:
        shutil.copy2(output / name, reference / name)
    write_vnv_manifest(reference, CalculixCurvedOrientationCorrelation.study_id)
    assets = ROOT / "docs" / "assets" / "reviews"
    assets.mkdir(parents=True, exist_ok=True)
    for name in names[2:]:
        shutil.copy2(output / name, assets / name)


if __name__ == "__main__":
    raise SystemExit(main())
