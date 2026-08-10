"""Run and publish TET10 mass, modal, load and recovery evidence."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from solveur.verification.tet10_mass_modal_loads import Tet10MassModalLoadsCampaign


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/VNV-TET10-MASS-MODAL-LOADS-013"),
    )
    args = parser.parse_args()
    summary = Tet10MassModalLoadsCampaign(args.output).run()
    _publish(args.output.resolve())
    print(f"{summary['study_id']}: {summary['status']} -> {args.output.resolve()}")
    return 0 if str(summary["status"]).startswith("PASS") else 1


def _publish(output: Path) -> None:
    reference = ROOT / "qualification" / "vnv" / "tet10_mass_modal_loads" / "reference"
    reference.mkdir(parents=True, exist_ok=True)
    for name in ("summary.json", "report.md", "tet10_modal_mode1.png", "vnv_manifest.json"):
        shutil.copy2(output / name, reference / name)
    target = ROOT / "docs" / "assets" / "reviews" / "tet10_modal_mode1.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(output / "tet10_modal_mode1.png", target)


if __name__ == "__main__":
    raise SystemExit(main())
