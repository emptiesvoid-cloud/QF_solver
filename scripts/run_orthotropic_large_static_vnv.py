"""Run and publish the bounded orthotropic large-static TET4 campaign."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from solveur.io.manifest import write_json_file
from solveur.verification.orthotropic_large_static import OrthotropicLargeStaticCampaign
from solveur.verification.vnv_manifest import write_vnv_manifest


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "results" / "VNV-ORTHOTROPIC-LARGE-STATIC-008"
CONTROLLED = ROOT / "qualification" / "vnv" / "orthotropic_large_static"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--nx", type=int, default=8)
    parser.add_argument("--ny", type=int, default=4)
    parser.add_argument("--nz", type=int, default=3)
    args = parser.parse_args()
    output = args.output.resolve()
    summary = OrthotropicLargeStaticCampaign(output, nx=args.nx, ny=args.ny, nz=args.nz).run()
    reference = CONTROLLED / "reference"
    reference.mkdir(parents=True, exist_ok=True)
    for name in ("summary.json", "report.md"):
        shutil.copy2(output / name, reference / name)
    write_vnv_manifest(reference, str(summary["study_id"]))
    study = {
        "study_id": summary["study_id"],
        "title": "Verification du chemin grand modele TET4 orthotrope en statique lineaire",
        "status": summary["status"],
        "maturity": summary["maturity"],
        "scope": summary["scope"],
        "model": summary["model"],
        "criteria": {
            "large_vs_standard_displacement_relative_error": 1.0e-9,
            "matrix_free_vs_assembled_displacement_relative_error": 1.0e-7,
            "energy_work_relative_error": 1.0e-8,
        },
        "controlled_artifacts": [
            "qualification/vnv/orthotropic_large_static/study.json",
            "qualification/vnv/orthotropic_large_static/reference/summary.json",
            "qualification/vnv/orthotropic_large_static/reference/report.md",
            "qualification/vnv/orthotropic_large_static/reference/vnv_manifest.json",
        ],
        "limitations": summary["limitations"],
    }
    write_json_file(CONTROLLED / "study.json", study)
    print(f"{summary['study_id']}: {summary['status']} -> {output}")
    return 0 if summary["status"] == "PASS_TECHNICAL_VERIFICATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
