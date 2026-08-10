"""Run CalculiX stress and buckling correlations for the TET4-TL scope."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from solveur.verification.calculix_tl_structural import CalculixTlStructuralCampaign


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = CalculixTlStructuralCampaign(args.output).run()
    _publish(args.output.resolve())
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if str(summary["status"]).startswith("PASS") else 1


def _publish(output: Path) -> None:
    reference = ROOT / "qualification" / "vnv" / "external" / "calculix_tl_structural" / "reference"
    reference.mkdir(parents=True, exist_ok=True)
    for name in ("summary.json", "report.md", "buckling_external_comparison.png", "vnv_manifest.json"):
        shutil.copy2(output / name, reference / name)


if __name__ == "__main__":
    raise SystemExit(main())
