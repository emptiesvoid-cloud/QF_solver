"""Run and publish the controlled TET10 geometry/quadrature campaign."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from solveur.verification.tet10_geometry_quadrature import Tet10GeometryQuadratureCampaign


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/VNV-TET10-GEOMETRY-QUADRATURE-011"),
    )
    args = parser.parse_args()
    summary = Tet10GeometryQuadratureCampaign(args.output).run()
    _publish(args.output.resolve())
    print(f"{summary['study_id']}: {summary['status']} -> {args.output.resolve()}")
    return 0 if str(summary["status"]).startswith("PASS") else 1


def _publish(output: Path) -> None:
    reference = ROOT / "qualification" / "vnv" / "tet10_geometry_quadrature" / "reference"
    reference.mkdir(parents=True, exist_ok=True)
    for name in ("summary.json", "report.md", "tet10_quadrature_convergence.png", "vnv_manifest.json"):
        shutil.copy2(output / name, reference / name)
    docs_asset = ROOT / "docs" / "assets" / "reviews" / "tet10_quadrature_convergence.png"
    docs_asset.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(output / "tet10_quadrature_convergence.png", docs_asset)


if __name__ == "__main__":
    raise SystemExit(main())
