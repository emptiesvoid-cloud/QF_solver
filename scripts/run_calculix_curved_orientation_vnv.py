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
    parser.add_argument(
        "--mesh-sizes",
        nargs="+",
        default=None,
        help="Optional levels written as NXxNY, for example 8x4 16x8 24x12 48x24 96x48 192x96.",
    )
    parser.add_argument(
        "--faceted-geometry",
        action="store_true",
        help="Place S8R midside nodes on the same faceted bilinear surface as MITC4.",
    )
    args = parser.parse_args()
    output = args.output.resolve()
    meshes = None
    if args.mesh_sizes:
        meshes = tuple(tuple(int(value) for value in item.lower().split("x")) for item in args.mesh_sizes)
    campaign = CalculixCurvedOrientationCorrelation(
        output,
        image=args.image,
        meshes=meshes,
        faceted_geometry=args.faceted_geometry,
    )
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
