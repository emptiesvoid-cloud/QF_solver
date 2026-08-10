"""Run the same-mesh QF_solver/CalculiX C3D10 correlation."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from solveur.verification.calculix_tet10 import CalculixTet10Correlation


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        type=Path,
        default=Path("results/VNV-TET10-STRUCTURAL-CONVERGENCE-012/torsion_tet10_h4.model.json"),
    )
    parser.add_argument(
        "--qf-result",
        type=Path,
        default=Path("results/VNV-TET10-STRUCTURAL-CONVERGENCE-012/torsion_tet10_h4.result.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/VNV-TET10-CALCULIX-C3D10-014"),
    )
    args = parser.parse_args()
    summary = CalculixTet10Correlation(args.output, args.model, args.qf_result).run()
    _publish(args.output.resolve())
    print(f"{summary['study_id']}: {summary['status']} -> {args.output.resolve()}")
    return 0 if str(summary["status"]).startswith("PASS") else 1


def _publish(output: Path) -> None:
    reference = ROOT / "qualification" / "vnv" / "external" / "calculix_tet10" / "reference"
    reference.mkdir(parents=True, exist_ok=True)
    for source in output.iterdir():
        if source.is_file():
            shutil.copy2(source, reference / source.name)
    target = ROOT / "docs" / "assets" / "reviews" / "calculix_c3d10_deformation.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(output / "calculix_c3d10_deformation.png", target)


if __name__ == "__main__":
    raise SystemExit(main())
