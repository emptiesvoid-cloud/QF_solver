"""Run the controlled CalculiX S8R ply-stress correlation."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from solveur.verification.calculix_composite_conical_ply_stress import (
    CompositeConicalPlyStressCalculixCorrelation,
)


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/VNV-COMP-CONICAL-CUTOUT-PLY-STRESS-CALCULIX-S8R-012"))
    args = parser.parse_args()
    output = args.output.resolve()
    summary = CompositeConicalPlyStressCalculixCorrelation(output).run()
    reference = (
        ROOT
        / "qualification"
        / "vnv"
        / "external"
        / "calculix_composite_conical_cutout_ply_stress"
        / "reference"
    )
    reference.mkdir(parents=True, exist_ok=True)
    for name in ("summary.json", "report.md", "conical_ply_stress_calculix_convergence.png", "vnv_manifest.json"):
        shutil.copy2(output / name, reference / name)
    target = ROOT / "docs" / "assets" / "reviews" / "composite_conical_ply_stress_calculix_convergence.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(output / "conical_ply_stress_calculix_convergence.png", target)
    print(f"{summary['study_id']}: {summary['status']} -> {output}")
    return 0 if str(summary["status"]).startswith("PASS") else 4


if __name__ == "__main__":
    raise SystemExit(main())
