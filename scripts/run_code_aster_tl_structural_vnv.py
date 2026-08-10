"""Run the Code_Aster 3D correlation for the TET4-TL structural scope."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from solveur.verification.code_aster_tl_structural import CodeAsterTlStructuralCampaign


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = CodeAsterTlStructuralCampaign(args.output).run()
    _publish(args.output.resolve())
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if str(summary["status"]).startswith("PASS") else 1


def _publish(output: Path) -> None:
    reference = ROOT / "qualification" / "vnv" / "external" / "code_aster_tl_structural" / "reference"
    reference.mkdir(parents=True, exist_ok=True)
    for name in (
        "summary.json",
        "report.md",
        "code_aster_stress_comparison.png",
        "code_aster_column_path.png",
        "vnv_manifest.json",
    ):
        shutil.copy2(output / name, reference / name)


if __name__ == "__main__":
    raise SystemExit(main())
