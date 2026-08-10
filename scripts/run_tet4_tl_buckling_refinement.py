"""Run the near-100k TET4 Euler buckling acceptance probe."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from solveur.verification.tet4_tl_buckling_refinement import Tet4TlBucklingRefinementProbe


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/VNV-TET4-TL-BUCKLING-H5-010"),
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path("results/VNV-TET4-TL-BUCKLING-EULER-006/summary.json"),
    )
    args = parser.parse_args()
    summary = Tet4TlBucklingRefinementProbe(args.output, args.baseline).run()
    _publish(args.output.resolve())
    print(f"{summary['study_id']}: {summary['status']} -> {args.output.resolve()}")
    return 0 if str(summary["status"]).startswith("PASS") else 1


def _publish(output: Path) -> None:
    reference = ROOT / "qualification" / "vnv" / "tet4_tl_buckling_h5" / "reference"
    reference.mkdir(parents=True, exist_ok=True)
    for name in (
        "summary.json",
        "report.md",
        "buckling_h5_convergence.png",
        "buckling_h5_mode.png",
        "vnv_manifest.json",
    ):
        shutil.copy2(output / name, reference / name)


if __name__ == "__main__":
    raise SystemExit(main())
