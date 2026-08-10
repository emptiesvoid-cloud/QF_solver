"""Run and publish the curved composite conical-cutout MITC4 campaign."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from solveur.verification.composite_conical_cutout import CompositeConicalCutoutStudy


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/VNV-COMP-CONICAL-CUTOUT-009"))
    args = parser.parse_args()
    output = args.output.resolve()
    summary = CompositeConicalCutoutStudy(output).run()
    reference = ROOT / "qualification" / "vnv" / "composite_conical_cutout" / "reference"
    reference.mkdir(parents=True, exist_ok=True)
    for name in ("summary.json", "report.md", "fine_model.json", "fine_results.json", "fine_deformation.vtu", "composite_conical_cutout_geometry.png", "composite_conical_cutout_convergence.png", "vnv_manifest.json"):
        shutil.copy2(output / name, reference / name)
    for name in ("composite_conical_cutout_geometry.png", "composite_conical_cutout_convergence.png"):
        destination = ROOT / "docs" / "assets" / "reviews" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(output / name, destination)
    print(f"{summary['study_id']}: {summary['status']} -> {output}")
    return 0 if str(summary["status"]).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
