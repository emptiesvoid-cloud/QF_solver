"""Publish the refined MITC4 static correlation against Code_Aster DKQ."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from solveur.verification.code_aster_mitc4_conical_cutout import CodeAsterMitc4ConicalCutoutCorrelation
from solveur.verification.vnv_manifest import write_vnv_manifest


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "results" / "VNV-MITC4-CONICAL-CUTOUT-REFINEMENT-002"
REFERENCE = ROOT / "qualification" / "vnv" / "external" / "code_aster_mitc4_conical_cutout_refinement" / "reference"
MESH_LEVELS = ((8, 24), (12, 36), (16, 48), (20, 60), (24, 72))
PUBLISHED_FILES = ("summary.json", "report.md", "conical_cutout_code_aster_correlation.png")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    study = CodeAsterMitc4ConicalCutoutCorrelation(output)
    study.meshes = MESH_LEVELS
    summary = study.run()
    _publish(output)
    fine = summary["rows"][-1]
    print(
        f"{summary['study_id']}: {summary['status']} | levels={len(summary['rows'])} | "
        f"fine_vector_difference={float(fine['vector_difference']):.12g}"
    )
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 1


def _publish(output: Path) -> None:
    REFERENCE.mkdir(parents=True, exist_ok=True)
    for name in PUBLISHED_FILES:
        shutil.copy2(output / name, REFERENCE / name)
    write_vnv_manifest(REFERENCE, "VNV-MITC4-CONICAL-CUTOUT-REFINEMENT-002")


if __name__ == "__main__":
    raise SystemExit(main())
