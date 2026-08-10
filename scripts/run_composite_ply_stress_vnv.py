"""Run and publish the MITC4 laminate ply-stress campaign."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from solveur.verification.composite_ply_stress import CompositePlyStressCampaign


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/VNV-COMP-PLY-STRESS-005"))
    args = parser.parse_args()
    output = args.output.resolve()
    summary = CompositePlyStressCampaign(output).run()
    _publish(output)
    print(f"{summary['study_id']}: {summary['status']} -> {output}")
    return 0 if str(summary["status"]).startswith("PASS") else 1


def _publish(output: Path) -> None:
    reference = ROOT / "qualification" / "vnv" / "composite_ply_stress" / "reference"
    reference.mkdir(parents=True, exist_ok=True)
    names = (
        "summary.json",
        "report.md",
        "ply_stress_convergence.png",
        "ply_stress_profile.png",
        "vnv_manifest.json",
    )
    for name in names:
        shutil.copy2(output / name, reference / name)
    for name in ("ply_stress_convergence.png", "ply_stress_profile.png"):
        destination = ROOT / "docs" / "assets" / "reviews" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(output / name, destination)


if __name__ == "__main__":
    raise SystemExit(main())
