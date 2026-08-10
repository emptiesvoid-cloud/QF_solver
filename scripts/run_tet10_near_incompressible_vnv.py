"""Run and publish the TET10 near-incompressible characterization."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from solveur.verification.tet10_near_incompressible import Tet10NearIncompressibleCampaign
from solveur.verification.vnv_manifest import write_vnv_manifest


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/VNV-TET10-NEAR-INCOMPRESSIBLE-015"),
    )
    args = parser.parse_args()
    summary = Tet10NearIncompressibleCampaign(args.output).run()
    _publish(args.output.resolve())
    print(f"{summary['study_id']}: {summary['status']} -> {args.output.resolve()}")
    return 0 if str(summary["status"]).startswith("PASS") else 1


def _publish(output: Path) -> None:
    reference = ROOT / "qualification" / "vnv" / "tet10_near_incompressible" / "reference"
    reference.mkdir(parents=True, exist_ok=True)
    for name in (
        "summary.json",
        "report.md",
        "tet10_near_incompressible.png",
        "tet10_nu0499_deformation.png",
        "tet10_nu0499_deformation.vtu",
    ):
        shutil.copy2(output / name, reference / name)
    write_vnv_manifest(reference, Tet10NearIncompressibleCampaign.study_id)
    for name in ("tet10_near_incompressible.png", "tet10_nu0499_deformation.png"):
        target = ROOT / "docs" / "assets" / "reviews" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(output / name, target)


if __name__ == "__main__":
    raise SystemExit(main())
