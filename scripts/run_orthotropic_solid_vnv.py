"""Run the orthotropic solid kernel verification campaign."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from solveur.verification.orthotropic_solid import OrthotropicSolidKernelCampaign


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "results" / "VNV-ORTHOTROPIC-SOLID-KERNEL-001"
REFERENCE = ROOT / "qualification" / "vnv" / "orthotropic_solid_kernel" / "reference"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    summary = OrthotropicSolidKernelCampaign(output).run()
    REFERENCE.mkdir(parents=True, exist_ok=True)
    for source in output.iterdir():
        if source.is_file():
            shutil.copy2(source, REFERENCE / source.name)
    print(f"{summary['study_id']}: {summary['status']} -> {output}")
    return 0 if summary["status"] == "PASS_TECHNICAL_VERIFICATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
