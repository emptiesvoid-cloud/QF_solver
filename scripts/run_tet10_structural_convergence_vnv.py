"""Run and publish TET4/TET10 structural convergence evidence."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from solveur.verification.tet10_structural_convergence import Tet10StructuralConvergenceCampaign


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/VNV-TET10-STRUCTURAL-CONVERGENCE-012"),
    )
    args = parser.parse_args()
    summary = Tet10StructuralConvergenceCampaign(args.output).run()
    _publish(args.output.resolve())
    print(f"{summary['study_id']}: {summary['status']} -> {args.output.resolve()}")
    return 0 if str(summary["status"]).startswith("PASS") else 1


def _publish(output: Path) -> None:
    reference = ROOT / "qualification" / "vnv" / "tet10_structural_convergence" / "reference"
    reference.mkdir(parents=True, exist_ok=True)
    names = (
        "summary.json",
        "report.md",
        "tet10_structural_convergence.png",
        "bending_tet10_deformation.png",
        "torsion_tet10_deformation.png",
        "vnv_manifest.json",
    )
    for name in names:
        shutil.copy2(output / name, reference / name)
    for name in names[2:5]:
        target = ROOT / "docs" / "assets" / "reviews" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(output / name, target)


if __name__ == "__main__":
    raise SystemExit(main())
