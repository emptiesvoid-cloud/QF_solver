"""Run and publish CalculiX correlation for the composite conical cutout."""

from __future__ import annotations
import argparse
import shutil
from pathlib import Path
from solveur.verification.calculix_composite_conical_cutout import CalculixCompositeConicalCutoutCorrelation

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/VNV-COMP-CONICAL-CUTOUT-CALCULIX-S8R-011"))
    args = parser.parse_args()
    output = args.output.resolve()
    summary = CalculixCompositeConicalCutoutCorrelation(output).run()
    ref = (
        ROOT / "qualification" / "vnv" / "external" / "calculix_composite_conical_cutout_regular_pressure" / "reference"
    )
    ref.mkdir(parents=True, exist_ok=True)
    for name in (
        "summary.json",
        "report.md",
        "composite_conical_calculix_correlation.png",
        "composite_conical_calculix_deformation.png",
        "vnv_manifest.json",
    ):
        shutil.copy2(output / name, ref / name)
    for name in ("composite_conical_calculix_correlation.png", "composite_conical_calculix_deformation.png"):
        target = ROOT / "docs" / "assets" / "reviews" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(output / name, target)
    print(f"{summary['study_id']}: {summary['status']} -> {output}")
    return 0 if str(summary["status"]).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
