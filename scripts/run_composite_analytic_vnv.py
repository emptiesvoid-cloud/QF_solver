"""Run and publish the analytical composite V&V campaign."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from solveur.verification.composite_analytic import CompositeAnalyticalCampaign


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/VNV-COMP-ANALYTIC-001"),
    )
    args = parser.parse_args()
    summary = CompositeAnalyticalCampaign(args.output).run()
    _publish(args.output.resolve())
    print(f"{summary['study_id']}: {summary['status']} -> {args.output.resolve()}")
    return 0 if str(summary["status"]).startswith("PASS") else 1


def _publish(output: Path) -> None:
    reference = ROOT / "qualification" / "vnv" / "composite_analytic" / "reference"
    reference.mkdir(parents=True, exist_ok=True)
    names = ("summary.json", "report.md", "composite_failure_envelopes.png", "vnv_manifest.json")
    for name in names:
        shutil.copy2(output / name, reference / name)
    docs_asset = ROOT / "docs" / "assets" / "reviews" / "composite_failure_envelopes.png"
    docs_asset.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(output / "composite_failure_envelopes.png", docs_asset)


if __name__ == "__main__":
    raise SystemExit(main())
