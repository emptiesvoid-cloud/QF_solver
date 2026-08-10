"""Run NAFEMS R0031/1 with QF_solver and Code_Aster DST."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from solveur.verification.composite_nafems import CompositeNafemsR0031Campaign


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/VNV-COMP-NAFEMS-R0031-CODEASTER-004"))
    parser.add_argument("--skip-code-aster", action="store_true")
    args = parser.parse_args()
    summary = CompositeNafemsR0031Campaign(args.output).run(execute_code_aster=not args.skip_code_aster)
    _publish(args.output.resolve())
    print(f"{summary['study_id']}: {summary['status']} -> {args.output.resolve()}")
    return 0 if str(summary["status"]).startswith("PASS") else 1


def _publish(output: Path) -> None:
    reference = ROOT / "qualification" / "vnv" / "external" / "code_aster_composite_nafems" / "reference"
    reference.mkdir(parents=True, exist_ok=True)
    for path in output.iterdir():
        if path.is_file():
            shutil.copy2(path, reference / path.name)
    for name in ("nafems_r0031_convergence.png", "nafems_r0031_deformation.png"):
        destination = ROOT / "docs" / "assets" / "reviews" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(output / name, destination)


if __name__ == "__main__":
    raise SystemExit(main())
