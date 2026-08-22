"""Publish the extra TET10 bending refinement used by the 1% stable gate."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from solveur.verification.tet10_structural_convergence import Tet10StructuralConvergenceCampaign
from solveur.verification.vnv_manifest import write_vnv_manifest


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "results" / "VNV-TET10-STABLE-REFINEMENT-002"
REFERENCE = ROOT / "qualification" / "vnv" / "tet10_stable_refinement" / "reference"
MESH_LEVELS = (1.10, 0.85, 0.65, 0.50, 0.40, 0.30)
PUBLISHED_FILES = (
    "summary.json",
    "report.md",
    "tet10_structural_convergence.png",
    "bending_tet10_deformation.png",
    "torsion_tet10_deformation.png",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    campaign = Tet10StructuralConvergenceCampaign(output)
    campaign.box_sizes = MESH_LEVELS
    summary = campaign.run()
    _publish(output)
    bending = summary["bending"]["families"]["TET10"]
    print(
        f"{summary['study_id']}: {summary['status']} | "
        f"levels={len(bending['levels'])} | "
        f"final_bending_error={float(bending['finest_response_error']):.12g}"
    )
    return 0 if str(summary["status"]).startswith("PASS") else 1


def _publish(output: Path) -> None:
    REFERENCE.mkdir(parents=True, exist_ok=True)
    for name in PUBLISHED_FILES:
        shutil.copy2(output / name, REFERENCE / name)
    write_vnv_manifest(REFERENCE, "VNV-TET10-STABLE-REFINEMENT-002")


if __name__ == "__main__":
    raise SystemExit(main())
