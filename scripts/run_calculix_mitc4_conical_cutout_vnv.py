"""Run and publish the MITC4 conical-cutout CalculiX S4 correlation."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from solveur.verification.calculix_mitc4_conical_cutout import CalculixMitc4ConicalCutoutCorrelation


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/VNV-MITC4-CONICAL-CUTOUT-CALCULIX-S4-013"))
    args = parser.parse_args()
    output = args.output.resolve()
    summary = CalculixMitc4ConicalCutoutCorrelation(output).run()
    reference = ROOT / "qualification" / "vnv" / "external" / "calculix_mitc4_conical_cutout" / "reference"
    reference.mkdir(parents=True, exist_ok=True)
    for name in ("summary.json", "report.md", "conical_cutout_calculix_correlation.png", "conical_cutout_calculix_deformation.png", "vnv_manifest.json"):
        shutil.copy2(output / name, reference / name)
    for name in ("conical_cutout_calculix_correlation.png", "conical_cutout_calculix_deformation.png"):
        destination = ROOT / "docs" / "assets" / "reviews" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(output / name, destination)
    print(f"{summary['study_id']}: {summary['status']} -> {output}")
    return 0 if str(summary["status"]).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
