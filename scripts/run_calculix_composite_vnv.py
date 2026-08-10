"""Run the CalculiX S8R composite-shell correlation."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from solveur.verification.calculix_composite import CalculixCompositeCorrelation


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/VNV-COMP-CALCULIX-S8R-003"))
    parser.add_argument("--image", default="qf-solver/calculix-nafems13h:2.20")
    args = parser.parse_args()
    summary = CalculixCompositeCorrelation(args.output, image=args.image).run()
    _publish(args.output.resolve())
    print(f"{summary['study_id']}: {summary['status']} -> {args.output.resolve()}")
    return 0 if str(summary["status"]).startswith("PASS") else 1


def _publish(output: Path) -> None:
    reference = ROOT / "qualification" / "vnv" / "external" / "calculix_composite" / "reference"
    reference.mkdir(parents=True, exist_ok=True)
    for path in output.iterdir():
        if path.is_file():
            shutil.copy2(path, reference / path.name)
    figure = output / "calculix_composite_correlation.png"
    destination = ROOT / "docs" / "assets" / "reviews" / figure.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(figure, destination)


if __name__ == "__main__":
    raise SystemExit(main())
