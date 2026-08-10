"""Run and publish the structural MITC4 laminate convergence campaign."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from solveur.verification.composite_structural import CompositeStructuralConvergenceCampaign


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/VNV-COMP-STRUCTURAL-CONVERGENCE-002"))
    args = parser.parse_args()
    summary = CompositeStructuralConvergenceCampaign(args.output).run()
    _publish(args.output.resolve())
    print(f"{summary['study_id']}: {summary['status']} -> {args.output.resolve()}")
    return 0 if str(summary["status"]).startswith("PASS") else 1


def _publish(output: Path) -> None:
    reference = ROOT / "qualification" / "vnv" / "composite_structural" / "reference"
    reference.mkdir(parents=True, exist_ok=True)
    names = (
        "summary.json",
        "report.md",
        "composite_structural_convergence.png",
        "composite_bending_deformation.png",
        "vnv_manifest.json",
    )
    for name in names:
        shutil.copy2(output / name, reference / name)
    for name in ("composite_structural_convergence.png", "composite_bending_deformation.png"):
        destination = ROOT / "docs" / "assets" / "reviews" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(output / name, destination)


if __name__ == "__main__":
    raise SystemExit(main())
