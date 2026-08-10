"""Run and publish projected-axis composite shell verification."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from solveur.verification.composite_curved_assembly import CompositeCurvedAssemblyCampaign


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/VNV-COMP-CURVED-ASSEMBLY-006"),
    )
    args = parser.parse_args()
    output = args.output.resolve()
    summary = CompositeCurvedAssemblyCampaign(output).run()
    _publish(output)
    print(f"{summary['study_id']}: {summary['status']} -> {output}")
    return 0 if str(summary["status"]).startswith("PASS") else 1


def _publish(output: Path) -> None:
    reference = ROOT / "qualification" / "vnv" / "composite_curved_assembly" / "reference"
    reference.mkdir(parents=True, exist_ok=True)
    names = (
        "summary.json",
        "report.md",
        "composite_curved_assembly_convergence.png",
        "composite_curved_assembly_meshes.png",
        "vnv_manifest.json",
    )
    for name in names:
        shutil.copy2(output / name, reference / name)
    for name in (
        "composite_curved_assembly_convergence.png",
        "composite_curved_assembly_meshes.png",
    ):
        destination = ROOT / "docs" / "assets" / "reviews" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(output / name, destination)


if __name__ == "__main__":
    raise SystemExit(main())
