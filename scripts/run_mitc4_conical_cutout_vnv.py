"""Run and publish the complex curved MITC4 static geometry campaign."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from solveur.verification.mitc4_conical_cutout import Mitc4ConicalCutoutStudy


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/VNV-MITC4-CONICAL-CUTOUT-STATIC-012"))
    args = parser.parse_args()
    output = args.output.resolve()
    summary = Mitc4ConicalCutoutStudy(output).run()
    _publish(output)
    print(f"{summary['study_id']}: {summary['status']} -> {output}")
    return 0 if str(summary["status"]).startswith("PASS") else 1


def _publish(output: Path) -> None:
    reference = ROOT / "qualification" / "vnv" / "mitc4_conical_cutout" / "reference"
    reference.mkdir(parents=True, exist_ok=True)
    names = (
        "summary.json", "report.md", "fine_model.json", "fine_results.json", "fine_deformation.vtu",
        "conical_cutout_geometry_deformation.png", "conical_cutout_convergence.png", "vnv_manifest.json",
    )
    for name in names:
        shutil.copy2(output / name, reference / name)
    for name in ("conical_cutout_geometry_deformation.png", "conical_cutout_convergence.png"):
        destination = ROOT / "docs" / "assets" / "reviews" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(output / name, destination)


if __name__ == "__main__":
    raise SystemExit(main())
