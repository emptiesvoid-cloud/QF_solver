"""Run and publish the curved-composite CalculiX correlation."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from solveur.verification.calculix_curved_composite import CalculixCurvedCompositeCorrelation
from solveur.verification.vnv_manifest import write_vnv_manifest


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/VNV-COMP-CURVED-CALCULIX-S8R-007"),
    )
    parser.add_argument("--image", default="qf-solver/calculix-nafems13h:2.20")
    args = parser.parse_args()
    output = args.output.resolve()
    summary = CalculixCurvedCompositeCorrelation(output, image=args.image).run()
    _publish(output)
    print(f"{summary['study_id']}: {summary['status']} -> {output}")
    return 0 if str(summary["status"]).startswith("PASS") else 1


def _publish(output: Path) -> None:
    reference = ROOT / "qualification" / "vnv" / "external" / "calculix_curved_composite" / "reference"
    reference.mkdir(parents=True, exist_ok=True)
    names = (
        "summary.json",
        "report.md",
        "curved_composite_calculix_correlation.png",
        "curved_composite_calculix_deformation.png",
    )
    for name in names:
        shutil.copy2(output / name, reference / name)
    write_vnv_manifest(reference, CalculixCurvedCompositeCorrelation.study_id)
    for name in (
        "curved_composite_calculix_correlation.png",
        "curved_composite_calculix_deformation.png",
    ):
        destination = ROOT / "docs" / "assets" / "reviews" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(output / name, destination)


if __name__ == "__main__":
    raise SystemExit(main())
